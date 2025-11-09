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

1. **Multi-State Logic**
   Support differing data requirements between states such as NSW and VIC.

2. **AI Document Processing**
   Use lightweight OCR or stubbed AI extraction to interpret payslips, bank statements, and reference letters.

3. **Profile Reusability**
   Store renter details persistently in a structured format, accessible across multiple submissions.

4. **Security and Compliance**
   Include privacy guardrails, field validation, and audit logging.

5. **Maintainability and Scalability**
   Build modular services with clear boundaries, enabling future cloud or enterprise extension.

---

## System Overview

The application is built around a modular **FastAPI backend** that orchestrates a series of **intelligent agents** for validation, compliance, and document reasoning.

It follows a **clean separation of concerns**:

* **API layer** (FastAPI endpoints for `/applications`, `/profiles`, `/rag/query`)
* **Core services** (database, vector store, caching, audit)
* **AI agents** (Intent, Compliance, Guardrails, RAG, Response)
* **Data persistence** (SQLite, Chroma vector store, JSON memory)
* **Testing layer** (Pytest-based integration and unit tests)

This separation ensures maintainability while still showcasing full-stack understanding of system interactions.

---

## Core Capabilities

1. **State-Aware Application Validation**
   Dynamically checks for required fields based on selected state rules (e.g., NSW vs VIC).

2. **AI-Powered Document Extraction**
   Extracts structured data from PDFs (payslips, rental forms, bank statements) through a document service.

3. **Contextual Reasoning via RAG**
   Retrieves relevant policy snippets from a seeded vector store to support agent responses.

4. **Guardrails and Privacy Detection**
   Scans for PII such as phone numbers or emails and masks them in logs and responses.

5. **Reusable Renter Profiles**
   Saves normalized profile data, allowing pre-filling of future applications.

6. **Audit and Observability**
   Every API call, document upload, and validation event is logged in both file and database layers.

7. **Resilience and Error Handling**
   Gracefully handles missing data, malformed PDFs, or empty uploads without breaking execution.

---

## Multi-Agent Architecture (Described)

The backend uses a **LangGraph-inspired multi-agent pipeline** to divide responsibility across specialized agents:

### Intent Agent

Identifies the user’s request type (e.g., “submit application”, “check compliance”, “upload document”).

### Canonical Agent

Normalizes incoming fields, ensuring consistent formatting (e.g., phone numbers, addresses).

### Compliance Agent

Applies state-specific validation logic using rules loaded from `config/state_rules.json`.

### Guardrails Agent

Detects privacy violations or missing fields, returning structured warnings.

### RAG Agent

Retrieves context from Chroma VectorDB to provide legal and procedural explanations.

### Response Agent

Synthesizes all outputs into a clear, user-facing response or JSON payload.

Each agent runs independently but shares a consistent context dictionary. This design mimics an **agentic reasoning loop** within an enterprise AI assistant while remaining transparent and testable.

---

## Data and Knowledge Management

### SQLite Database

Holds:

* `profiles` – renter profiles with contact, employment, and identity details
* `applications` – application submissions including metadata and validation results
* `audit` – logs of all events and API interactions

### Chroma Vector Store

Contains embedded knowledge snippets for each state and general guidance. Example seeded data:

* “NSW rental applications require proof of income, identity, and rental history.”
* “VIC applicants must provide passport or driver’s license, income verification, and references.”

### Memory Store

A lightweight JSON file (`memory_store.json`) stores the in-memory context, allowing restart persistence and debugging.

---

## Retrieval-Augmented Generation (RAG) Flow

1. The RAG Agent receives a text query (e.g., “What documents are required for NSW?”).
2. The vector store performs a semantic search using embeddings from SentenceTransformer.
3. Top matching knowledge snippets are returned to provide context for the response agent.
4. The API responds with a list of retrieved documents and scores, ensuring transparency.

This enables explainable AI behavior: all conclusions trace back to concrete textual knowledge sources.

---

## Application Lifecycle

The startup lifecycle initializes several critical components:

1. **Database Initialization** – SQLite tables and seed data creation
2. **Chroma Vector Store Load** – Embedding four core knowledge statements
3. **SentenceTransformer Load** – Inference model for semantic similarity
4. **Memory Store Load** – Reloads cached profiles and session context
5. **Agent Registration** – Initializes all agents with dependencies injected

This ensures the system is fully operational when `/health` or `/graph/status` endpoints are queried.

---

## API Overview

### Health Check

`GET /health`
Verifies that all agents and data layers are active.

### Create Application

`POST /applications`
Accepts form data and attached PDFs.
Performs multi-state validation, document processing, and compliance checks.

### Get Profile

`GET /profiles/{email}`
Returns stored renter profile with masked sensitive fields.

### Query RAG

`POST /rag/query`
Executes a semantic search over seeded documents and returns relevant knowledge.

### List All Applications

`GET /applications`
Displays every stored submission with validation results and timestamps.

---

## Example Workflow (cURL)

### Submit a NSW Application

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

Expected Response:

```json
{
  "status": "ok",
  "state": "NSW",
  "message": "Please ensure all required ID, income, and rental history documents are provided for NSW’s rental application."
}
```

---

## Testing and Validation

A comprehensive set of integration and unit tests verify all core functionalities:

* **Application Submission Tests** – Valid and invalid data handling
* **Document Service Tests** – Successful and failed OCR parsing
* **RAG Tests** – Query results and relevance
* **Compliance Tests** – State-specific required fields
* **Guardrails Tests** – PII detection and masking
* **Profile Tests** – Persistence and retrieval from SQLite

Each test file (e.g., `test_api_applications.py`, `test_document_service.py`) ensures end-to-end integrity of the workflow.

---

## Error Handling

The API handles both system and validation errors gracefully.
Examples include:

* Missing or malformed fields → structured “Field required” JSON responses
* Corrupt or unreadable PDFs → `{"detail": "No /Root object! - Is this really a PDF?"}`
* Unknown states → validation message with supported state list

Every failure path returns an informative, user-friendly message without exposing stack traces.

---

## Security and Privacy

* PII (emails, phone numbers) are masked in all logs and responses.
* Guardrails agent automatically flags unsafe or private fields.
* Temporary uploaded documents are deleted after processing.
* SQLite uses WAL mode to prevent data corruption.
* No unencrypted credentials or tokens are stored.
* All agents operate deterministically with traceable inputs and outputs.

---

## Observability and Audit

Every application event is logged via the `Audit` module, recording:

* Timestamp (UTC)
* Entity type (profile, application, document)
* Action description
* Additional metadata

Logs are stored in both `logs/app.log` and the `audit` table for cross-validation.
This ensures compliance with data governance and reproducibility standards.

---

## Extensibility

The project is structured for easy enhancement:

* **Cloud Migration** – Replace SQLite with PostgreSQL or DynamoDB.
* **Real OCR / AI Integration** – Connect AWS Textract or Bedrock for live extraction.
* **Frontend Integration** – Add React, Next.js, or Streamlit UI.
* **Authentication Layer** – Secure endpoints via OAuth or JWT.
* **Multi-State Expansion** – Add QLD, SA, and WA rules in `state_rules.json`.

The modular directory layout (`agents`, `core`, `services`, `api`) allows vertical feature addition with minimal refactoring.

---

## Lessons Learned

1. **Agentic Design** simplifies reasoning complexity by dividing validation into specialized roles.
2. **RAG Pipelines** provide explainable results — every message links to factual text.
3. **State Configurability** using JSON is more maintainable than branching logic.
4. **File IO and Async Handling** are crucial for scalability in document uploads.
5. **Testing via cURL and Pytest** offers confidence before deployment.
6. **Clear Logging and Masking** enable safe debugging while maintaining privacy compliance.

---

## Future Enhancements

Planned improvements include:

* Incorporating **vector-based summarization** for document insights.
* Adding **affordability scoring** to estimate rental suitability.
* Implementing **streaming AI responses** for interactive chat-style validation.
* Integrating **LLM model APIs** such as OpenAI or Anthropic Bedrock.
* Deploying on **AWS Lambda + API Gateway** with persistent S3 storage.

---

## Conclusion

The **Rental AI Assistant – Multi-State Application Validator** showcases how a well-architected, lightweight AI system can automate document-intensive workflows through multi-agent reasoning and semantic retrieval.

It highlights professional-level skills in **AI integration, backend design, state management, compliance handling, and data governance** — making it an ideal portfolio and interview demonstration project.

---

## Author

**Qaisar Khan**
Senior Python & Data/AI Engineer
Sydney, Australia

Email: [qjkconsultants@gmail.com](mailto:qjkconsultants@gmail.com)
LinkedIn: [linkedin.com/in/qaisar-khan](https://linkedin.com/in/qaisar-khan)
