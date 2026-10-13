
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_FILE = PROJECT_ROOT / "knowledge_base" / "cyber_guidance.json"


def load_knowledge_base():
    """Load trusted cybercrime guidance from the local JSON file."""
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)




def retrieve_guidance(query, incident_type=None, top_k=3):
    """Retrieve relevant guidance using incident-aware keyword matching."""
    documents = load_knowledge_base()

    query_words = set(query.lower().replace("/", " ").split())
    results = []

    # Map user-facing incident names to knowledge-base categories.
    incident_aliases = {
        "phishing": {"general_cybercrime"},
        "phishing or scam message": {"general_cybercrime"},
        "general_cybercrime": {"general_cybercrime"},
        "financial_fraud": {"financial_fraud"},
        "financial fraud": {"financial_fraud"},
        "evidence_preservation": {"evidence_preservation"},
    }

    normalized_type = (incident_type or "").strip().lower()
    allowed_types = incident_aliases.get(normalized_type)

    # Treat these terms as indicators of a financial incident.
    financial_terms = {
        "upi", "payment", "money", "bank", "transaction",
        "financial", "fraud", "amount", "transfer"
    }

    is_financial_query = bool(query_words & financial_terms)

    for document in documents:
        doc_type = document.get("incident_type", "")

        # Prefer documents matching the selected incident category.
        if allowed_types and doc_type not in allowed_types:
            continue

        # Avoid unrelated financial advice for a phishing-only query.
        if not is_financial_query and doc_type == "financial_fraud":
            continue

        searchable_text = " ".join([
            document.get("title", ""),
            doc_type,
            " ".join(document.get("keywords", [])),
            " ".join(document.get("guidance", [])),
        ]).lower()

        score = sum(
            1 for word in query_words
            if len(word) > 2 and word in searchable_text
        )

        if score > 0:
            results.append({
                "id": document["id"],
                "title": document["title"],
                "incident_type": doc_type,
                "guidance": document.get("guidance", []),
                "source_name": document.get("source_name", "Unknown source"),
                "source_url": document.get("source_url", ""),
                "retrieval_score": score,
            })

    results.sort(
        key=lambda item: item["retrieval_score"],
        reverse=True,
    )

    selected = results[:top_k]

    return {
        "query": query,
        "retrieval_method": "incident_aware_keyword_matching",
        "results": selected,
        "result_count": len(selected),
    }
