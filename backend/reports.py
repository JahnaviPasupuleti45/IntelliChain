"""Shipment reports: written by the LLM from the reading + relevant SOP sections, or from a template."""
import llm
from retriever import get_retriever
from risk_model import sop_search_query

REPORT_PROMPT = """You are a logistics operations assistant. Write a short incident report for this shipment reading.

Shipment: {shipment_id} ({product_type})
Location: {location}
Temperature: {temperature} °C | Humidity: {humidity} % | Delay: {delay_hours} h
Model risk assessment: {risk} (confidence {probability:.0%})

Relevant company SOP sections:
{context}

Write 3 to 5 sentences: say what is wrong (if anything), why it matters for this product type,
and the specific next actions from the SOP. Only recommend actions that appear in the SOP sections.
This is a single reading, so you do not know how long a condition has lasted: state time-based
SOP rules as conditions (e.g. "if the excursion lasts more than 1 hour ...").
Do not use Markdown formatting."""


def _template_report(r, sections):
    lines = [
        f"Shipment {r['shipment_id']} ({r['product_type']}) at {r['location']}.",
        f"Temperature {r['temperature']} °C, humidity {r['humidity']} %, delay {r['delay_hours']} h.",
        f"Risk: {r['risk']} (model confidence {r['risk_probability']:.0%}).",
    ]
    if r["risk"] != "LOW" and sections:
        lines.append(f"See SOP: {sections[0]['document']} - {sections[0]['title']}.")
    return " ".join(lines)


def build_report(reading):
    """reading is a dict with the sensor values plus 'risk' and 'risk_probability'."""
    query = sop_search_query(
        reading["product_type"], reading["risk"], reading["temperature"], reading["humidity"], reading["delay_hours"]
    )
    sections = get_retriever().search(query, k=3, products=[reading["product_type"]])

    if reading["risk"] != "LOW":
        context = "\n\n".join(f"[{s['document']} - {s['title']}]\n{s['text']}" for s in sections)
        text = llm.generate(REPORT_PROMPT.format(
            probability=reading["risk_probability"], context=context, **reading
        ))
        if text:
            return text, "llm"
    return _template_report(reading, sections), "template"
