# Rental AI Assistant – Multi-State Application Validator

## Introduction

The **Rental AI Assistant** is a home-built **proof-of-concept** designed to demonstrate how **AI-powered document intelligence** and **multi-agent reasoning** can automate and streamline the rental application process across multiple Australian states.

It was developed as a personal showcase project to illustrate **real-world application of Generative AI, RAG (Retrieval-Augmented Generation), multi-agent orchestration, and data compliance validation** within a maintainable backend architecture.

This README is written for **interview reviewers, engineering leads, and solution architects** who want to understand the reasoning, design, and technical competency behind the system.

---

## Executive Summary

Rental applications vary by state in Australia — each with distinct legal and compliance requirements. Applicants often resubmit similar data repeatedly, while property managers manually verify documents, identity, and income. This results in duplication, errors, and delays.

The Rental AI Assistant addresses this inefficiency through an **AI-driven backend system** that performs:

* **Multi-state validation** (NSW, VIC, etc.)
* **Document extraction and semantic reasoning** using AI
* **Reusable renter profiles** stored securely in SQLite and JSON
* **Compliance and guardrails** to prevent privacy breaches or data inconsistencies
* **Explainable RAG retrieval** for answering context-based queries

The proof-of-concept demonstrates how a lightweight backend, powered by **FastAPI**, **LangGraph-style multi-agent orchestration**, and **Chroma VectorDB**, can deliver a scalable and compliant digital rental assistant.

---

## Problem Context

In a typical Australian rental market:

* Each **state’s legislation** (e.g., NSW Fair Trading vs VIC Consumer Affairs) requires different supporting documents.
* **Property managers** spend hours cross-checking payslips, references, and identification.
* **Renters** repeat manual entry for each new property application.
* **Privacy laws** (such as the Privacy Act 1988) restrict how personal data can be stored or shared.

The challenge was to design a system that:

1. Handles **multi-state variations** without hard-coding each form.
2. Allows **profile reuse** for renters across states.
3. Integrates **AI extraction** for PDF documents.
4. Maintains **data security, auditability, and compliance**.
5. Demonstrates a **modern, extensible architecture** suitable for real deployment.

---

## Objectives

The project was guided by five core objectives:

1. **Multi-State Logic** – Support differing data requirements between NSW and VIC.
2. **AI Document Processing** – Use lightweight OCR or stubbed AI extraction to interpret payslips, bank statements, and references.
3. **Profile Reusability** – Store renter details persistently in a structured format.
4. **Security and Compliance** – Include privacy guardrails, field validation, and audit logging.
5. **Maintainability and Scalability** – Enable modular and cloud-ready extension.

---

## Setup Instructions

### Prerequisites

Install:

* **Python 3.11**
* **Poetry** for dependency management
* **curl** and **jq** for API testing
* macOS / Linux / Windows (via WSL)

Optional for OCR:

```bash
brew install tesseract poppler
```

---

### Clone the Repository

```bash
git clone git@github.com:qjkconsultants/rental-ai-assistant.git
cd rental-ai-assistant
```

---

### Install Dependencies

```bash
poetry install
```

If Poetry is not installed:

```bash
pip install poetry && poetry install
```

---

### Activate the Virtual Environment

```bash
poetry shell
```

---

### Initialize Database and Vector Store

```bash
PYTHONPATH=src poetry run python src/snug/core/seed_chroma.py
```

This seeds:

* **Chroma VectorDB** (state & compliance knowledge)
* **SQLite DB (`data/snug.db`)**
* **JSON memory store** for runtime cache

---

### Start the API Server

```bash
PYTHONPATH=src poetry run uvicorn snug.api.app:app --reload
```

Expected log:

```
Use pytorch device_name: cpu
Load pretrained SentenceTransformer: all-MiniLM-L6-v2
Chroma vector store seeded with 4 items.
Application startup complete on http://127.0.0.1:8000
```

---

### Verify Health

```bash
curl -s http://127.0.0.1:8000/health | jq
```

Expected:

```json
{"status":"ok","agents":["intent","canonical","compliance","guardrails","rag","response"]}
```

---

## System Overview

A modular **FastAPI** backend orchestrates multiple **intelligent agents** for validation, compliance, and document reasoning.

Layers:

* **API layer:** `/applications`, `/profiles`, `/rag/query`
* **Core services:** database, vector store, caching, audit
* **AI agents:** Intent, Compliance, Guardrails, RAG, Response
* **Persistence:** SQLite, Chroma, JSON memory
* **Tests:** Pytest integration and unit tests

---

## Core Capabilities

1. **State-Aware Validation** based on `state_rules.json`
2. **AI Document Extraction** for structured PDF parsing
3. **RAG Contextual Reasoning** from Chroma vector store
4. **Guardrails Privacy Detection** for PII masking
5. **Profile Persistence** across sessions
6. **Audit Logging** and observability
7. **Robust Error Handling** for corrupt or missing inputs

---

## Multi-Agent Architecture

Each agent performs a specific reasoning task:

* **Intent Agent** – Identifies user intent (e.g., submit, validate).
* **Canonical Agent** – Normalizes and standardizes fields.
* **Compliance Agent** – Validates based on state-specific rules.
* **Guardrails Agent** – Flags privacy or safety violations.
* **RAG Agent** – Retrieves policy context using embeddings.
* **Response Agent** – Synthesizes structured outputs.

All agents share a common context object, forming a transparent reasoning chain.

---

## Data and Knowledge Management

### SQLite Database

Stores:

* Renter profiles
* Applications
* Audit logs

### Chroma Vector Store

Contains knowledge entries such as:

* “NSW rental applications require proof of income, identity, and rental history.”
* “VIC applicants must provide passport or driver’s license, income verification, and references.”

### JSON Memory Store

`memory_store.json` preserves state context for debugging and reloading.

---

## Retrieval-Augmented Generation (RAG) Flow

1. RAG agent receives a query (e.g., “What documents are required for NSW?”)
2. Chroma vector search retrieves semantically similar text.
3. Top results are fed into response synthesis.
4. Output includes retrieved snippets for transparency.

This makes the reasoning explainable and auditable.

---

## Application Lifecycle

Startup initializes:

1. **Database and seed data**
2. **Chroma Vector Store**
3. **SentenceTransformer model**
4. **Memory context store**
5. **Agent registration**

After initialization, `/health` or `/graph/status` endpoints confirm readiness.

---

## API Overview

| Endpoint            | Method | Purpose                                   |
| ------------------- | ------ | ----------------------------------------- |
| `/health`           | GET    | Verifies agents and stores                |
| `/applications`     | POST   | Submits and validates rental applications |
| `/profiles/{email}` | GET    | Retrieves renter profiles                 |
| `/rag/query`        | POST   | Executes semantic queries                 |
| `/applications`     | GET    | Lists all submissions                     |

---

## Example Workflow

### Submit NSW Application

```bash
curl -X POST http://127.0.0.1:8000/applications \
  -F state=NSW \
  -F email="nsw.tester@example.com" \
  -F first_name="John" \
  -F last_name="Doe" \
  -F dob="1990-05-12" \
  -F phone_number="0400000001" \
  -F current_address="1 Sydney St" \
  -F employment_status="Full-Time" \
  -F employer_name="ABC Pty Ltd" \
  -F employer_contact="0400111222" \
  -F income=95000 \
  -F drivers_license="NSW999999" \
  -F documents=@tests/fixtures/forms/NSW_rental_form.pdf
```

Response:

```json
{"status":"ok","state":"NSW","message":"Please ensure all required ID, income, and rental history documents are provided for NSW’s rental application."}
```

---

## Testing and Validation

Run tests:

```bash
PYTHONPATH=src poetry run pytest -v
```

Includes:

* Application lifecycle tests
* Corrupt document handling
* Guardrails privacy scans
* RAG retrieval checks
* Compliance enforcement

---

## Error Handling

Examples:

* Missing field → structured error
* Corrupt PDF → `{"detail":"No /Root object! - Is this really a PDF?"}`
* Invalid state → guidance response listing supported states

All failures are gracefully handled and logged.

---

## Security and Privacy

* PII masked in logs and responses
* Guardrails enforce privacy rules
* Temp files deleted post-processing
* SQLite uses WAL mode for durability
* No external API keys stored

---

## Observability and Audit

All actions are logged with:

* Timestamp (UTC)
* Entity type
* Action summary
* Metadata

Dual logging to `logs/app.log` and `audit` DB table ensures full traceability.

---

## Extensibility

Future enhancements:

* Integrate **AWS Textract / Bedrock** for true AI extraction
* Cloud DB migration (PostgreSQL / DynamoDB)
* Frontend (Next.js, Streamlit)
* Add new state rules (QLD, SA, WA)
* Authentication via JWT

---

## Design Decisions

1. **FastAPI** for async, typed APIs
2. **SQLite** for simplicity and ACID compliance
3. **Chroma** for offline RAG reasoning
4. **LangGraph-style agents** for modular design
5. **JSON configs** for scalable state rules
6. **Guardrails** for responsible AI
7. **Poetry** for isolated reproducible builds

---

## Design Alternatives Considered

| Option          | Replaced By | Reason                 |
| --------------- | ----------- | ---------------------- |
| Flask           | FastAPI     | Async, type validation |
| Pinecone        | Chroma      | Local, dependency-free |
| PostgreSQL      | SQLite      | Lightweight for demo   |
| LLM Integration | RAG         | Reproducibility        |
| Docker          | Poetry      | Easier local testing   |

---

## Lessons Learned

1. Multi-agent reasoning clarifies AI workflows.
2. RAG pipelines provide explainable retrieval.
3. JSON-driven rules simplify compliance logic.
4. Clear audit and PII handling is vital for trust.
5. Lightweight stack accelerates experimentation.

---

## Future Enhancements

* Document summarization using embeddings
* Rental affordability scoring
* Real-time chat validation
* Deployment to AWS Lambda + S3
* RAG-powered conversational interface

---

## Conclusion

The **Rental AI Assistant – Multi-State Application Validator** demonstrates how a compact, modular AI backend can automate document-heavy workflows while maintaining explainability, compliance, and audit integrity.

It showcases advanced skills in **Python 3.11**, **FastAPI**, **AI integration**, **state-based validation**, and **enterprise software design**, making it an ideal **portfolio project** for technical interviews.

---

## Author

**Qaisar Khan**
Senior Python & Data/AI Engineer
Sydney, Australia

Email: [qjkconsultants@gmail.com](mailto:qjkconsultants@gmail.com)
LinkedIn: [linkedin.com/in/qjkconsultants](https://linkedin.com/in/qjkconsultants)
