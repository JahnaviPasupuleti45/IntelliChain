import pytest

from config import Config
from evaluate_retrieval import evaluate
from retriever import Retriever, load_chunks


@pytest.fixture(scope="module")
def retriever():
    return Retriever(Config.KNOWLEDGE_DIR, backend="embeddings")


def test_chunks_are_split_by_section_with_metadata():
    chunks = load_chunks(Config.KNOWLEDGE_DIR)
    assert len(chunks) == 16
    assert all(c["title"] and c["text"] for c in chunks)
    pharma = [c for c in chunks if c["source"] == "pharma_cold_chain_sop.md"]
    assert all(c["products"] == {"pharma"} for c in pharma)


def test_embeddings_find_every_answer_in_top_3(retriever):
    """recall@3 on the labelled evaluation set: the top 3 sections are what the LLM sees."""
    assert retriever.mode == "embeddings"
    recall_at_1, recall_at_3, misses = evaluate(retriever)
    assert recall_at_3 == 1.0, misses
    assert recall_at_1 >= 0.75


def test_embeddings_beat_keyword_search(retriever):
    _, embeddings_recall, _ = evaluate(retriever)
    _, tfidf_recall, _ = evaluate(Retriever(Config.KNOWLEDGE_DIR, backend="tfidf"))
    assert embeddings_recall > tfidf_recall


def test_product_filter_only_returns_matching_sops(retriever):
    results = retriever.search("temperature too high, what do we do", k=6, products=["pharma"])
    assert {r["document"] for r in results} <= {"Pharmaceutical Cold Chain SOP", "Risk Escalation Policy"}
