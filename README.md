# Nexora — Intelligent Cybercrime Response and Evidence Guidance System

**When cybercrime happens, know your next move.**

Nexora is a cybercrime response assistance prototype that helps users organize digital evidence, identify potentially relevant incident details, build an incident timeline, find missing information, retrieve cybercrime guidance with source references, and prepare complaint drafts for review.

## Features

- **Evidence Processing:** Extract candidate dates, amounts, transaction references, phone numbers, and email addresses from supported files.
- **Incident Timeline:** Organize extracted details into a structured timeline.
- **Missing Information Detection:** Highlight fields that may require additional information or user verification.
- **Cybercrime Guidance:** Retrieve relevant guidance from a local knowledge base with available source references.
- **Complaint Draft Generation:** Prepare a draft using supplied incident details for the user to review.
- **Evidence Integrity Verification:** Use SHA-256 hashes to detect changes relative to a stored reference hash.
- **Cloud Processing Demo:** Demonstrate Amazon S3 event notifications, AWS Lambda processing, and Amazon CloudWatch logging.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| Database | SQLite |
| Guidance Knowledge Base | JSON |
| Cloud Storage | Amazon S3 |
| Serverless Processing | AWS Lambda |
| Logging | Amazon CloudWatch |
| File Integrity | SHA-256 |

## Project Structure

```text
nexora/
├── backend/
│   ├── main.py
│   ├── llm_service.py
│   ├── rag_service.py
│   ├── security_service.py
│   └── requirements.txt
├── knowledge_base/
│   └── cyber_guidance.json
├── src/
│   ├── App.jsx
│   ├── main.jsx
│   └── styles.css
├── index.html
├── package.json
├── package-lock.json
├── .gitignore
└── README.md
```

## Prerequisites

- Python with a version supported by the backend dependencies
- Node.js and npm
- Git

## Run Locally

### 1. Start the backend

Open a terminal in the project root:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn main:app --reload
```

The API documentation is available at:

http://127.0.0.1:8000/docs

### 2. Start the frontend

Open a second terminal in the project root:

```bash
npm install
npm run dev
```

Open the local URL displayed by Vite, usually:

http://localhost:5173

If the frontend uses an API base URL, make sure it points to the running backend.

## Cloud Engineering Demonstration

The cloud demonstration uses Amazon S3, AWS Lambda, and Amazon CloudWatch.

1. Upload a test file to the configured S3 bucket.
2. An S3 object-created event triggers the Lambda function.
3. The function processes the uploaded file and records information in CloudWatch logs.

The cloud demonstration is separate from the local application unless explicit integration has been configured.

## Security and Limitations

- Extracted information is unverified until reviewed by the user.
- A completeness score measures field coverage, not factual accuracy.
- Complaint drafts require user review and are not automatically submitted.
- SHA-256 comparison detects changes relative to a reference hash; it does not prove file authenticity.
- A reference hash stored in a local SQLite database is not tamper-proof.
- Never upload real victim information, private evidence, database files, credentials, or AWS access keys to a public repository.

For suspected financial cyber fraud in India, call **1930** promptly and consult the official National Cyber Crime Reporting Portal:

https://cybercrime.gov.in/

## Future Enhancements

- Stronger access controls and secure audit logging.
- Improved evidence parsing and validation.
- Enhanced guidance retrieval and source management.
- Secure integration between the local application and cloud services.
- Automated testing and deployment.

## License

No license has been specified. A license can be added after deciding how the project may be reused or distributed.