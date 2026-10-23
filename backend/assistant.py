"""
Ops Copilot: answers operations questions using two sources of context.

  1. Live data: the latest reading of any shipment mentioned in the question
     (e.g. "SHP2"), plus every shipment currently at MEDIUM or HIGH risk.
  2. Company knowledge: the SOP sections retrieved for the question (RAG).

Both go into the prompt, and the LLM is told to answer only from them and to
cite the SOP sections it used. Without an LLM key, the same context is
returned in a structured form instead of a generated answer.
"""
import re

from sqlalchemy import func

import llm
from database import ShipmentReading, db
from retriever import get_retriever
from risk_model import sop_search_query

SHIPMENT_ID_PATTERN = re.compile(r"\bSHP-?\d+\b", re.IGNORECASE)

ANSWER_PROMPT = """You are IntelliChain Ops Copilot, an assistant for a logistics operations team.
Answer the question using ONLY the live shipment data and SOP sections below.
- Mention shipment IDs and the actual readings when they are relevant.
- When you recommend an action, cite the SOP section in square brackets, e.g. [Risk Escalation Policy - HIGH risk].
- Check every shipment's readings against the limits in the SOP for ITS product type.
- For each shipment that needs action, give the product-specific SOP steps AND the escalation rule for its risk level.
- If asked about "high risk" or "risky" shipments and none are HIGH, say so in one line, then still
  cover the MEDIUM ones, because they need attention too.
- Each shipment has only its latest reading, so you do not know how long a condition has lasted:
  state time-based rules as conditions (e.g. "if the excursion lasts more than 1 hour ...").
- If the answer is not in the context, say you don't have that information. Do not make things up.
- Keep it short and practical. You may use **bold** and numbered or bulleted lists.

LIVE SHIPMENT DATA (latest reading per shipment):
{shipments}

SOP SECTIONS:
{sections}

QUESTION: {question}"""


def latest_readings():
    """Latest reading for every shipment."""
    latest_ids = (
        db.session.query(func.max(ShipmentReading.id)).group_by(ShipmentReading.shipment_id)
    )
    return ShipmentReading.query.filter(ShipmentReading.id.in_(latest_ids)).all()


def find_relevant_shipments(question):
    """Return (shipments named in the question, other shipments currently at risk)."""
    readings = latest_readings()
    named_ids = {m.upper().replace("-", "") for m in SHIPMENT_ID_PATTERN.findall(question)}
    named = [r for r in readings if r.shipment_id.upper().replace("-", "") in named_ids]
    at_risk = [r for r in readings if r.risk != "LOW" and r not in named]
    at_risk.sort(key=lambda r: (r.risk != "HIGH", -r.risk_probability))
    return named, at_risk[:10]


def retrieve_sections(question, named, at_risk):
    """Collect SOP sections for the question and for each shipment it is about.

    - Questions naming shipments ("SHP2") focus on those shipments and only search
      their product types' SOPs. General questions focus on the riskiest shipments.
    - Each focus shipment gets its own search, so one shipment's SOP can't crowd out
      another's (e.g. electronics and food SOPs hiding the pharma one).
    - The escalation rule for each focus shipment's risk level always applies, so it
      is added by direct lookup.
    """
    retriever = get_retriever()
    focus = named or at_risk[:5]
    products = {r.product_type for r in named} or None

    sections = retriever.search(question, k=2, products=products)
    for r in focus:
        query = sop_search_query(r.product_type, r.risk, r.temperature, r.humidity, r.delay_hours)
        sections += retriever.search(query, k=2, products=[r.product_type])
    for risk in sorted({r.risk for r in focus}):
        sections.append(retriever.get_section("Risk Escalation Policy", f"{risk} risk"))

    unique = {}
    for s in sections:
        if s is not None:
            unique.setdefault((s["document"], s["title"]), s)
    return list(unique.values())


def _format_shipment(r):
    return (
        f"- {r.shipment_id} | {r.product_type} | {r.location} | temp {r.temperature} °C | "
        f"humidity {r.humidity} % | delay {r.delay_hours} h | risk {r.risk} ({r.risk_probability:.0%})"
    )


def _format_section(s):
    return f"[{s['document']} - {s['title']}]\n{s['text']}"


def answer(question):
    named, at_risk = find_relevant_shipments(question)
    shipments = named + at_risk
    sections = retrieve_sections(question, named, at_risk)

    shipment_text = "\n".join(_format_shipment(s) for s in shipments) or "No shipments at risk."
    section_text = "\n\n".join(_format_section(s) for s in sections)

    generated = llm.generate(ANSWER_PROMPT.format(
        shipments=shipment_text, sections=section_text, question=question
    ))
    if generated:
        text, mode = generated, "llm"
    else:
        mode = "retrieval-only"
        text = (
            "LLM is not configured, so here is the relevant context I found.\n\n"
            f"Shipments:\n{shipment_text}\n\n"
            "Relevant SOP guidance:\n"
            + "\n\n".join(_format_section(s) for s in sections)
        )

    return {
        "answer": text,
        "mode": mode,
        "retrieval": get_retriever().mode,
        "sources": [
            {"document": s["document"], "title": s["title"], "file": s["source"], "score": s["score"]}
            for s in sections
        ],
        "shipments": [s.to_dict() for s in shipments],
    }
