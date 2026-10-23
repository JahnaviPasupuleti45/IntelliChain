"""
Retrieval for RAG: finds the SOP sections most relevant to a question.

1. Chunking: every Markdown file in knowledge/ is split at its "## " headings,
   so each chunk is one self-contained SOP section. The "Applies to:" line of
   each file says which product types it covers (metadata).
2. Embedding: chunks are embedded locally with BAAI/bge-small-en-v1.5 through
   fastembed (ONNX, no GPU or API key needed). If fastembed is not installed,
   TF-IDF keyword vectors are used instead.
3. Search: optionally filter chunks by product type (metadata filtering), then
   rank them by cosine similarity to the question.
"""
import glob
import logging
import os
import re

import numpy as np
from flask import current_app

log = logging.getLogger(__name__)
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


def load_chunks(knowledge_dir):
    chunks = []
    for path in sorted(glob.glob(os.path.join(knowledge_dir, "*.md"))):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        doc_title = text.splitlines()[0].lstrip("# ").strip()
        applies_to = re.search(r"^Applies to:\s*(.+)$", text, re.MULTILINE)
        products = {p.strip().lower() for p in applies_to.group(1).split(",")} if applies_to else {"all"}
        for section in text.split("\n## ")[1:]:
            heading, _, body = section.partition("\n")
            chunks.append({
                "source": os.path.basename(path),
                "document": doc_title,
                "products": products,
                "title": heading.strip(),
                "text": body.strip(),
            })
    return chunks


_embedding_model = None


def get_embedding_model():
    """Load the model once per process (first run downloads it, ~67 MB)."""
    global _embedding_model
    if _embedding_model is None:
        from fastembed import TextEmbedding

        _embedding_model = TextEmbedding(EMBEDDING_MODEL)
    return _embedding_model


class EmbeddingIndex:
    def __init__(self, texts):
        self.model = get_embedding_model()
        self.matrix = np.array(list(self.model.embed(texts)))  # vectors are already normalised

    def scores(self, query):
        # bge also supports a "Represent this sentence..." query prefix, but
        # evaluate_retrieval.py showed better recall@1 without it on our SOPs.
        query_vector = next(iter(self.model.embed([query])))
        return self.matrix @ query_vector


class TfidfIndex:
    def __init__(self, texts):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(texts)

    def scores(self, query):
        return (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()


class Retriever:
    def __init__(self, knowledge_dir, backend="embeddings"):
        self.chunks = load_chunks(knowledge_dir)
        # The document title gives each section context, e.g. "HIGH risk" belongs to the escalation policy
        texts = [f"{c['document']} - {c['title']}\n{c['text']}" for c in self.chunks]

        self.mode = backend
        if backend == "embeddings":
            try:
                self.index = EmbeddingIndex(texts)
            except ImportError:
                log.warning("fastembed not installed, falling back to TF-IDF retrieval")
                self.mode = "tfidf"
        if self.mode == "tfidf":
            self.index = TfidfIndex(texts)

    def search(self, query, k=3, products=None):
        """Top-k chunks for the query. If products is given, only SOPs for those products
        (plus general ones such as the escalation policy) are considered."""
        scores = self.index.scores(query)
        candidates = [
            i for i, c in enumerate(self.chunks)
            if not products or "all" in c["products"] or c["products"] & set(products)
        ]
        ranked = sorted(candidates, key=lambda i: scores[i], reverse=True)[:k]
        return [
            {**{key: v for key, v in self.chunks[i].items() if key != "products"}, "score": round(float(scores[i]), 3)}
            for i in ranked
        ]


    def get_section(self, document, title):
        """Look up one section directly by its document and title (no similarity search)."""
        for chunk in self.chunks:
            if chunk["document"] == document and chunk["title"] == title:
                return {**{key: v for key, v in chunk.items() if key != "products"}, "score": None}
        return None


def get_retriever():
    """One retriever per app, built on first use."""
    if "retriever" not in current_app.extensions:
        current_app.extensions["retriever"] = Retriever(
            current_app.config["KNOWLEDGE_DIR"], current_app.config["RETRIEVER_BACKEND"]
        )
    return current_app.extensions["retriever"]
