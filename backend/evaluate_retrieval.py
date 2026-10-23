"""
Evaluate the retriever on a small labelled set of questions.

For each question we know which SOP section *should* be found. We report:
  - recall@1: how often the right section is the top result
  - recall@3: how often it is in the top 3 (what the LLM actually sees)

Usage:
    python evaluate_retrieval.py
"""
from config import Config
from retriever import Retriever

# (question, title of the section that answers it)
EVAL_SET = [
    ("vaccine frozen below zero degrees", "Pharma freezing risk"),
    ("insulin shipment is at 11 degrees, what now?", "Pharma temperature excursion response"),
    ("what temperature should medicines be kept at?", "Pharma temperature range"),
    ("pharma truck stuck in traffic for 5 hours", "Pharma delay handling"),
    ("who must be notified for a high risk shipment", "HIGH risk"),
    ("which shipments are high risk right now and what do we do?", "HIGH risk"),
    ("medium risk shipment, how quickly do we review it", "MEDIUM risk"),
    ("model says low risk, any action needed?", "LOW risk"),
    ("the sensor reading jumped suddenly, is it broken?", "Sensor fault check"),
    ("electronics got wet in the truck", "Electronics humidity response"),
    ("laptops shipment delayed by a day", "Electronics delay handling"),
    ("how hot can a furniture shipment get?", "General cargo limits"),
    ("can spoiled chicken still be delivered?", "Food temperature excursion response"),
    ("mould on fruit cartons because of moisture", "Food humidity and condensation"),
    ("vegetables arriving 6 hours late", "Food delay handling"),
    ("what is the safe range for dairy?", "Food temperature range"),
]


def evaluate(retriever):
    hits_at_1 = hits_at_3 = 0
    misses = []
    for question, expected in EVAL_SET:
        titles = [r["title"] for r in retriever.search(question, k=3)]
        hits_at_1 += titles[0] == expected
        hits_at_3 += expected in titles
        if expected not in titles:
            misses.append((question, expected, titles))
    n = len(EVAL_SET)
    return hits_at_1 / n, hits_at_3 / n, misses


if __name__ == "__main__":
    for name, backend in [("TF-IDF (keywords)", "tfidf"), ("Embeddings (bge-small)", "embeddings")]:
        r1, r3, misses = evaluate(Retriever(Config.KNOWLEDGE_DIR, backend=backend))
        print(f"{name:26s} recall@1 = {r1:.0%}   recall@3 = {r3:.0%}")
        for question, expected, got in misses:
            print(f"    miss: {question!r} expected {expected!r}, got {got}")
    print(f"\n{len(EVAL_SET)} labelled questions")
