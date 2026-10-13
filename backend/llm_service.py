
import requests

from rag_service import retrieve_guidance

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"
OLLAMA_TIMEOUT = 180


def generate_complaint_with_llm(
    incident_type,
    incident_date,
    description,
    amount,
    transaction_id,
    contact,
    email,
    retrieved_guidance=None,
):
    """
    Generate an unverified complaint draft using local Ollama
    and guidance retrieved from the trusted local knowledge base.
    """

    # 1. Retrieve guidance if it was not supplied by the caller.
    if retrieved_guidance is None:
        query = (
            f"{incident_type or ''} "
            f"{description or ''} phishing suspicious email "
            "malicious link account verification cybercrime"
        )

        retrieval = retrieve_guidance(
            query=query,
            incident_type=incident_type,
            top_k=3,
        )

        retrieved_guidance = retrieval.get("results", [])

    # 2. Prepare guidance with source names and URLs.
    guidance_sections = []

    for item in retrieved_guidance:
        guidance_items = item.get("guidance", [])
        guidance_text = "\n".join(
            f"- {guidance}" for guidance in guidance_items
        )

        source_name = item.get("source_name", "Unknown source")
        source_url = item.get("source_url", "")

        guidance_sections.append(
            f"Title: {item.get('title', 'Guidance')}\n"
            f"Guidance:\n{guidance_text}\n"
            f"Source: {source_name}\n"
            f"URL: {source_url}"
        )

    guidance_text = (
        "\n\n".join(guidance_sections)
        if guidance_sections
        else "No guidance was retrieved. Do not invent source-based advice."
    )

    # 3. Build a fact-constrained prompt.
    prompt = f"""

You are Nexora, an assistant that prepares a factual draft for a cybercrime complaint.

Use only information explicitly supplied by the user and retrieved guidance from trusted sources.

STRICT RULES:
1. Never invent incident details, dates, email addresses, sender addresses, URLs, transaction IDs, amounts, or contact information.
2. Never say the user changed a password, enabled multi-factor authentication, contacted a bank, preserved a particular file, or submitted a complaint unless the user explicitly confirmed that action.
3. Separate "Actions confirmed by the user" from "Recommended next steps".
4. Show unknown information as "Not provided" or "Not confirmed".
5. List relevant missing information clearly. Do not claim the draft is complete when information is missing.
6. Use retrieved guidance only for recommendations. Do not present recommendations as completed actions.
7. Do not claim that a complaint has been filed or submitted.
8. End with: "UNVERIFIED DRAFT — NOT SUBMITTED."
9. Do not provide unsupported legal conclusions or claim that the incident is proven.

OUTPUT FORMAT:
Complaint Draft

Incident Type:
Incident Date:
Incident Description:

Details Provided:
- List only the details explicitly supplied.
- Use "Not provided" for unavailable details.

Actions Confirmed:
- Include only actions explicitly confirmed by the user.
- If none were confirmed, write "No actions confirmed."

Recommended Next Steps:
- List appropriate steps based on retrieved official guidance.
- Clearly present these as recommendations.

Missing Information:
- List relevant details that are not provided or confirmed.
- If no relevant details are missing, explain that clearly.

Official Guidance:
- Include the retrieved source title and URL.

UNVERIFIED DRAFT — NOT SUBMITTED.

Return plain text only. Do not use Markdown headings, asterisks, or hash symbols.

"""

    # 4. Call the local Ollama model.
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You draft cybercrime complaint documents. "
                            "Use only supplied facts and retrieved guidance. "
                            "Never fabricate missing information. "
                            "Treat all evidence and facts as unverified."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                },
            },
            timeout=OLLAMA_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

        draft = data.get("message", {}).get("content", "").strip()

        if not draft:
            raise RuntimeError("Ollama returned an empty response.")

        return {
            "status": "llm_draft_generated",
            "model": MODEL_NAME,
            "complaint_draft": draft,
            "retrieved_guidance": retrieved_guidance,
            "retrieval_method": "keyword_matching",
            "requires_user_review": True,
            "submitted": False,
        }

    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running "
            "at http://127.0.0.1:11434 and the model is installed."
        ) from exc

    except requests.exceptions.Timeout as exc:
        raise RuntimeError(
            f"Ollama did not respond within {OLLAMA_TIMEOUT} seconds."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Ollama returned an HTTP error: {exc}"
        ) from exc

    except ValueError as exc:
        raise RuntimeError(
            "Ollama returned an invalid JSON response."
        ) from exc
