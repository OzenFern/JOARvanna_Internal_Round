"""blackbox/agents/tools/search.py — Keyword-based document search tool."""
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class Document:
    doc_id:  str
    title:   str
    content: str
    score:   float = 0.0

# ── Demo knowledge base ────────────────────────────────────────────────────────
KNOWLEDGE_BASE: list[Document] = [
    Document("d01", "Eiffel Tower",
             "The Eiffel Tower is a wrought-iron lattice tower in Paris, France. "
             "It stands 330 metres tall and was completed in 1889."),
    Document("d02", "Python language",
             "Python is a high-level, general-purpose programming language. "
             "It was created by Guido van Rossum and first released in 1991."),
    Document("d03", "Water boiling point",
             "Water boils at 100 degrees Celsius (212 Fahrenheit) at sea level. "
             "The boiling point decreases at higher altitudes."),
    Document("d04", "Speed of light",
             "The speed of light in a vacuum is approximately 299,792 km/s. "
             "It is denoted by the letter c in physics."),
    Document("d05", "Great Wall of China",
             "The Great Wall of China stretches over 21,196 km. "
             "It was built over many centuries by various Chinese dynasties."),
    Document("d06", "Amazon River",
             "The Amazon River is the largest river by discharge volume. "
             "It flows through Brazil and is approximately 6,400 km long."),
    Document("d07", "Human body temperature",
             "Normal human body temperature is approximately 37 degrees Celsius (98.6 F). "
             "Fever is generally defined as temperature above 38 degrees Celsius."),
    Document("d08", "Shakespeare birth year",
             "William Shakespeare was born in April 1564 in Stratford-upon-Avon, England. "
             "He wrote 37 plays and 154 sonnets."),
]

def search(query: str, top_k: int = 3) -> list[Document]:
    """Return top_k documents most relevant to the query (keyword overlap scoring)."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored = []
    for doc in KNOWLEDGE_BASE:
        doc_terms = set(re.findall(r"\w+", (doc.title + " " + doc.content).lower()))
        overlap   = len(query_terms & doc_terms)
        if overlap > 0:
            scored.append(Document(
                doc_id=doc.doc_id, title=doc.title,
                content=doc.content, score=overlap / len(query_terms),
            ))
    scored.sort(key=lambda d: d.score, reverse=True)
    return scored[:top_k]

def retrieve(doc_id: str) -> Document | None:
    """Retrieve a specific document by ID."""
    for doc in KNOWLEDGE_BASE:
        if doc.doc_id == doc_id:
            return doc
    return None
