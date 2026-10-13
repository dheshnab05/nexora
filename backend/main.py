
import io
import os
import re
import sqlite3
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from rag_service import retrieve_guidance
import pandas as pd
import pytesseract
from PIL import Image, ImageOps
from pypdf import PdfReader
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from llm_service import generate_complaint_with_llm
from rag_service import retrieve_guidance
from security_service import calculate_sha256, verify_file_integrity
# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "Nexora.db"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_TYPES = {
    ".txt", ".csv", ".pdf", ".png", ".jpg", ".jpeg"
}

INCIDENT_TYPES = {
    "Financial fraud / UPI fraud",
    "Phishing or scam message",
    "Account hacked",
    "Online harassment",
    "Other cybercrime",
}

app = FastAPI(
    title="Nexora — Cybercrime Response and Evidence Guidance",
    description="Evidence ingestion, ETL and data-quality analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --------------------------------------------------
# DATABASE: STORE METADATA, NOT EVIDENCE CONTENT
# --------------------------------------------------

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS processing_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL,
                records_extracted INTEGER NOT NULL,
                quality_score REAL NOT NULL,
                processed_at TEXT NOT NULL
            )
        """)


init_db()


def log_event(
    case_id,
    filename,
    file_type,
    file_size,
    status,
    records_extracted,
    quality_score,
):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO processing_events (
                case_id, filename, file_type, file_size,
                status, records_extracted, quality_score,
                processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                filename,
                file_type,
                file_size,
                status,
                records_extracted,
                quality_score,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


# --------------------------------------------------
# EXTRACT: READ SUPPORTED FILE TYPES
# --------------------------------------------------

def extract_text(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()

    if extension == ".txt":
        return content.decode("utf-8-sig", errors="replace")

    if extension == ".csv":
        # Read CSV through Pandas and convert its rows
        # to text for subsequent processing.
        df = pd.read_csv(io.BytesIO(content), dtype=str)
        df = df.fillna("")
        return df.to_csv(index=False)

    if extension == ".pdf":
        reader = PdfReader(io.BytesIO(content))

        if reader.is_encrypted:
            raise ValueError(
                "Password-protected PDFs are not supported."
            )

        if len(reader.pages) > 50:
            raise ValueError(
                "PDF exceeds the 50-page processing limit."
            )

        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            pages.append(
                f"[Page {page_number}]\n{page_text}"
            )

        text = "\n".join(pages)

        if not text.strip():
            raise ValueError(
                "No selectable text was found in this PDF. "
                "Scanned PDF OCR is not implemented in this version."
            )

        return text

    if extension in {".png", ".jpg", ".jpeg"}:
        image = Image.open(io.BytesIO(content))

        if image.width * image.height > 20_000_000:
            raise ValueError(
                "Image dimensions exceed the processing limit."
            )

        image = ImageOps.exif_transpose(image).convert("RGB")

        try:
            return pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as exc:
            raise ValueError(
                "Tesseract OCR is not installed or not on PATH. "
                "Install Tesseract, restart VS Code, and try again."
            ) from exc

    raise ValueError("Unsupported file type.")


# --------------------------------------------------
# TRANSFORM: NORMALIZE AND IDENTIFY CANDIDATE FIELDS
# --------------------------------------------------

def normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def unique_matches(pattern, text, flags=0):
    found = re.findall(pattern, text, flags)

    # Preserve order while removing duplicates.
    return list(dict.fromkeys(
        item.strip() if isinstance(item, str)
        else "".join(item).strip()
        for item in found
        if (item.strip() if isinstance(item, str)
            else "".join(item).strip())
    ))


def extract_fields(text: str) -> dict:
    # These are candidates extracted from text, not
    # verified transaction facts.
    dates = unique_matches(
        r"\b(?:\d{4}-\d{2}-\d{2}|"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        text,
    )

    amounts = unique_matches(
        r"(?i)(?:₹|INR|Rs\.?)\s*[\d,]+(?:\.\d{1,2})?",
        text,
    )

    # Common transaction-reference labels followed by
    # an alphanumeric identifier.
    references = unique_matches(
        r"(?i)\b(?:UTR|transaction\s*(?:ID|ref(?:erence)?|no\.?)|"
        r"reference\s*(?:ID|no\.?))\s*[:#-]?\s*"
        r"([A-Z0-9][A-Z0-9/-]{5,34})\b",
        text,
    )

    phones = unique_matches(
        r"(?<!\d)(?:\+91[- ]?)?[6-9]\d{9}(?!\d)",
        text,
    )

    emails = unique_matches(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text,
    )

    return {
        "dates": dates,
        "amounts": amounts,
        "transaction_references": references,
        "phone_numbers": phones,
        "email_addresses": emails,
    }


# --------------------------------------------------
# VALIDATE: IDENTIFY MISSING INFORMATION
# --------------------------------------------------


def quality_report(fields: dict, incident_type: str) -> dict:
    """
    Check whether required candidate fields were extracted.
    This measures data completeness, not factual accuracy.
    """

    required_by_type = {
        "Financial fraud / UPI fraud": [
            "dates",
            "amounts",
            "transaction_references",
        ],
        "Phishing or scam message": [
            "dates",
            "email_addresses",
        ],
        "Account hacked": [
            "dates",
            "email_addresses",
        ],
        "Online harassment": [
            "dates",
        ],
        "Other cybercrime": [
            "dates",
        ],
    }

    required = required_by_type.get(
        incident_type,
        ["dates"],
    )

    # Identify fields for which no candidate value was extracted.
    missing = [
        field
        for field in required
        if not fields.get(field)
    ]

    total = len(required)
    present = total - len(missing)

    score = (
        round((present / total) * 100, 2)
        if total
        else 100.0
    )

    # Flag candidate values for review; extraction is not verification.
    verification_fields = [
        field
        for field in fields
        if fields.get(field)
    ]

    return {
        "required_fields_checked": required,
        "missing_fields": missing,
        "candidate_completeness_percent": score,
        "requires_user_verification": True,
        "verification_status": "pending",
        "fields_requiring_verification": verification_fields,
        "notice": (
            "Completeness indicates whether required candidate "
            "fields were extracted. It does not confirm that the "
            "information is accurate or that the complaint is ready "
            "to submit. Verify all details against the original evidence."
        ),
    }



# --------------------------------------------------
# API: HEALTH CHECK
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "service": "Nexora Data Engineering API",
        "module": "Module 1 - Data Engineering",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# API: PROCESS AN EVIDENCE FILE
# --------------------------------------------------

def create_timeline(cleaned_text, fields):
    """Create candidate timeline events from extracted evidence text."""
    import re

    events = []
    lines = cleaned_text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        dates = re.findall(
            r"\b\d{4}-\d{2}-\d{2}\b",
            line
        )

        for date in dates:
            events.append({
                "date_candidate": date,
                "source_line": line_number,
                "description": line.strip(),
                "verified": False
            })

    # Sort chronologically; extracted events remain unverified.
    events.sort(key=lambda event: event["date_candidate"])

    return events

@app.post("/api/evidence/process")
async def process_evidence(
    file: UploadFile = File(...),
    incident_type: str = Form(...),
):
    if incident_type not in INCIDENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Select a supported incident type.",
        )

    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if not filename or extension not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Allowed formats: TXT, CSV, PDF, PNG, JPG and JPEG.",
        )

    # Read at most 10 MB + 1 byte to enforce the limit.
    content = await file.read(MAX_FILE_SIZE + 1)
    await file.close()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    case_id = "CASE-" + hashlib.sha256(
        os.urandom(32)
    ).hexdigest()[:12].upper()

    try:
        raw_text = extract_text(filename, content)
        cleaned_text = normalize_text(raw_text)

        if not cleaned_text:
            raise ValueError(
                "No text could be extracted from this file."
            )

        fields = extract_fields(cleaned_text)
        quality = quality_report(fields, incident_type)
        timeline = create_timeline(cleaned_text, fields)

        # Count lines with content as a basic processing metric.
        line_count = sum(
            1 for line in cleaned_text.splitlines()
            if line.strip()
        )

        log_event(
            case_id=case_id,
            filename=filename,
            file_type=extension,
            file_size=len(content),
            status="success",
            records_extracted=line_count,
            quality_score=quality["candidate_completeness_percent"],
        )

        return {
            "case_id": case_id,
            "filename": filename,
            "incident_type": incident_type,
            "processing_status": "success",
            "extracted_text": cleaned_text,
            "candidate_fields": fields,
            "data_quality": quality,
            "timeline": timeline,
            "processing_metrics": {
                "file_size_bytes": len(content),
                "nonempty_lines": line_count,
                "timeline_events": len(timeline),
            },
            "privacy_notice": (
                "The uploaded file and extracted text are not "
                "saved by this endpoint. Processing metadata is "
                "stored in SQLite."
            ),
        }

    except ValueError as exc:
        log_event(
            case_id=case_id,
            filename=filename,
            file_type=extension,
            file_size=len(content),
            status="failed",
            records_extracted=0,
            quality_score=0,
        )
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        import traceback
        traceback.print_exc()
        log_event(
            case_id=case_id,
            filename=filename,
            file_type=extension,
            file_size=len(content),
            status="failed",
            records_extracted=0,
            quality_score=0,
        )
        raise HTTPException(
            status_code=500,
            detail="Evidence processing failed. Check server logs.",
        ) from exc


# --------------------------------------------------
# API: PROCESSING METADATA
# --------------------------------------------------

@app.get("/api/processing-events")
def processing_events():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, case_id, filename, file_type, file_size,
                   status, records_extracted, quality_score,
                   processed_at
            FROM processing_events
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()

    return {
        "count": len(rows),
        "events": [dict(row) for row in rows],
    }

# MODULE 3: GUIDANCE RETRIEVAL API

class GuidanceRequest(BaseModel):
    query: str
    incident_type: str | None = None


@app.post("/api/guidance/retrieve")
def get_guidance(request: GuidanceRequest):
    return retrieve_guidance(
        query=request.query,
        incident_type=request.incident_type
    )

# MODULE 3: COMPLAINT DRAFT GENERATION

class ComplaintDraftRequest(BaseModel):
    incident_type: str
    incident_date: str = ""
    description: str
    amount: str = ""
    transaction_id: str = ""
    contact: str = ""
    email: str = ""


@app.post("/api/guidance/complaint-draft")
def generate_complaint_draft(request: ComplaintDraftRequest):

    incident_mapping = {
        "Financial fraud / UPI fraud": "financial_fraud",
        "Phishing or scam message": "general_cybercrime",
        "Account hacked": "general_cybercrime",
        "Online harassment": "general_cybercrime",
        "Other cybercrime": "general_cybercrime"
    }

    guidance_type = incident_mapping.get(
        request.incident_type,
        "general_cybercrime"
    )

    # Retrieve relevant guidance from the local knowledge base.
    query = (
        request.incident_type + " " +
        request.description + " " +
        request.amount + " " +
        request.transaction_id
    )

    retrieved = retrieve_guidance(
        query=query,
        incident_type=guidance_type
    )

    def display(value):
        return value.strip() if value and value.strip() else (
            "[NOT PROVIDED — PLEASE ADD]"
        )

    missing_fields = []

    required_fields = {
        "Incident date": request.incident_date,
        "Incident description": request.description,
    }

    if guidance_type == "financial_fraud":
        required_fields.update({
            "Amount lost": request.amount,
            "Transaction ID": request.transaction_id,
        })

    for field, value in required_fields.items():
        if not value or not value.strip():
            missing_fields.append(field)

    draft = f"""
CYBERCRIME COMPLAINT — DRAFT ONLY

Incident type: {request.incident_type}
Incident date: {display(request.incident_date)}

Incident description:
{display(request.description)}

Amount involved: {display(request.amount)}
Transaction ID: {display(request.transaction_id)}
Contact number: {display(request.contact)}
Email address: {display(request.email)}

Please review the information above and correct it against
your original evidence before using this draft.

Missing information:
{chr(10).join('- ' + field for field in missing_fields)
 if missing_fields else '- No required fields missing from this form.'}

STATUS: UNVERIFIED DRAFT — NOT SUBMITTED
"""

    return {
        "status": "draft_generated",
        "incident_type": request.incident_type,
        "complaint_draft": draft,
        "missing_fields": missing_fields,
        "requires_user_review": True,
        "retrieved_guidance": retrieved["results"],
        "sources": [
            {
                "source_name": item["source_name"],
                "source_url": item["source_url"]
            }
            for item in retrieved["results"]
        ],
        "notice": (
            "This is a template-generated draft, not legal advice. "
            "Verify all details and sources before submission."
        )
    }

# MODULE 3: ADAPTIVE INCIDENT CHECKLIST

@app.get("/api/guidance/checklist")
def get_incident_checklist(incident_type: str):

    checklists = {
        "Financial fraud / UPI fraud": [
            "Contact your bank or payment provider using its official channel.",
            "For financial cyber fraud in India, call 1930 immediately.",
            "Report the incident at https://www.cybercrime.gov.in/.",
            "Keep the transaction ID, amount, date, and payment receipt ready.",
            "Verify all details against the original evidence."
        ],
        "Phishing or scam message": [
            "Keep the original suspicious message or email.",
            "Record the sender address, phone number, and suspicious URL.",
            "Avoid clicking suspicious links or sharing passwords and OTPs.",
            "Report the incident through https://www.cybercrime.gov.in/.",
            "Review the evidence before preparing a complaint."
        ],
        "Account hacked": [
            "Use the service's official account recovery process.",
            "Change compromised passwords from a trusted device.",
            "Enable multi-factor authentication if available.",
            "Preserve security alerts and suspicious login notifications.",
            "Report the incident through https://www.cybercrime.gov.in/."
        ],
        "Online harassment": [
            "Preserve relevant messages, URLs, and screenshots.",
            "Record dates and times when known.",
            "Use the platform's official reporting and blocking features where appropriate.",
            "Report the incident through https://www.cybercrime.gov.in/.",
            "Review the evidence before preparing a complaint."
        ],
        "Other cybercrime": [
            "Record what happened and when it happened.",
            "Preserve relevant messages, files, URLs, and screenshots.",
            "Identify any missing information without guessing.",
            "Use https://www.cybercrime.gov.in/ to find the appropriate reporting category.",
            "Review all details before submitting a complaint."
        ]
    }

    if incident_type not in checklists:
        return {
            "status": "error",
            "message": "Unsupported incident type.",
            "supported_incident_types": list(checklists.keys())
        }

    return {
        "incident_type": incident_type,
        "checklist": checklists[incident_type],
        "official_portal": "https://www.cybercrime.gov.in/",
        "requires_user_review": True
    }

class LLMComplaintRequest(BaseModel):
    incident_type: str
    incident_date: Optional[str] = None
    description: str
    amount: Optional[str] = None
    transaction_id: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None



@app.post("/api/guidance/complaint-draft-llm")
def generate_llm_complaint(request: LLMComplaintRequest):
    from fastapi import HTTPException

    try:
        query = (
            f"{request.incident_type} "
            f"{request.description} "
            f"{request.amount or ''} "
            f"{request.transaction_id or ''}"
        )

        # First retrieve relevant guidance without strict filtering.
        retrieval = retrieve_guidance(query, top_k=3)
        guidance_items = retrieval.get("results", [])

        # If keyword matching finds nothing, retry with a broader query.
        if not guidance_items:
            fallback_query = (
                f"{request.incident_type} cybercrime reporting evidence"
            )
            retrieval = retrieve_guidance(fallback_query, top_k=3)
            guidance_items = retrieval.get("results", [])

        # Do not generate a supposedly grounded draft with no sources.
        if not guidance_items:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No relevant guidance was retrieved. "
                    "Check the knowledge base and retrieval query."
                ),
            )

        draft = generate_complaint_with_llm(
            incident_type=request.incident_type,
            incident_date=request.incident_date,
            description=request.description,
            amount=request.amount,
            transaction_id=request.transaction_id,
            contact=request.contact,
            email=request.email,
            retrieved_guidance=guidance_items,
        )

        return {
            "status": "llm_draft_generated",
            "model": "qwen2.5:3b",
            "complaint_draft": draft,
            "retrieval_method": retrieval.get(
                "retrieval_method", "keyword_matching"
            ),
            "retrieved_guidance": guidance_items,
            "source_count": len(guidance_items),
            "requires_user_review": True,
            "submitted": False,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM generation failed. Check Ollama, the model, "
                "and the backend terminal for details."
            ),
        ) from exc

from pydantic import BaseModel

class IntegrityCheckRequest(BaseModel):
    filename: str
    original_hash: str | None = None


def get_integrity_db():
    """Create the persistent evidence integrity table."""
    db_path = Path(__file__).resolve().parent / "Nexora.db"

    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evidence_integrity (
            filename TEXT PRIMARY KEY,
            original_sha256 TEXT NOT NULL,
            stored_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

@app.post("/api/security/verify-integrity")

@app.post("/api/security/verify-integrity")
def verify_integrity_api(request: IntegrityCheckRequest):
    evidence_dir = Path(__file__).resolve().parent
    file_path = (evidence_dir / request.filename).resolve()

    # Only allow files directly inside the backend directory.
    if file_path.parent != evidence_dir or not file_path.is_file():
        return {
            "filename": request.filename,
            "integrity_status": "file_not_found",
            "verified": False,
            "message": "Evidence file not found in the backend directory."
        }

    current_hash = calculate_sha256(str(file_path))
    conn = get_integrity_db()

    try:
        row = conn.execute(
            """
            SELECT original_sha256, stored_at
            FROM evidence_integrity
            WHERE filename = ?
            """,
            (file_path.name,)
        ).fetchone()

        # First verification: save the original hash once.
        if row is None:
            stored_at = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """
                INSERT INTO evidence_integrity
                    (filename, original_sha256, stored_at)
                VALUES (?, ?, ?)
                """,
                (file_path.name, current_hash, stored_at)
            )
            conn.commit()

            return {
                "filename": file_path.name,
                "original_sha256": current_hash,
                "current_sha256": current_hash,
                "stored_at": stored_at,
                "integrity_status": "baseline_stored",
                "verified": True,
                "message": (
                    "Original hash stored in the Nexora SQLite database. "
                    "This establishes a reference for future comparisons."
                )
            }

        # Later verification: compare against the saved original.
        original_hash, stored_at = row

        result = verify_file_integrity(
            str(file_path), original_hash
        )

        result["stored_at"] = stored_at
        result["storage"] = "SQLite: Nexora.db"
        result["message"] = (
            "File matches the stored reference hash."
            if result.get("verified")
            else "File differs from its stored reference hash."
        )

        return result

    finally:
        conn.close()
