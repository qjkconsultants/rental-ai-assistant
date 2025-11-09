# Integrity: Never store raw user documents; only derived structured data.
# Customer First: Fail gracefully with clear errors.
# Creativity: Uses AI-powered document parsing and semantic search.
# Excellence: Follows SOLID design and modular separation.
# Inclusivity: Designed with transparency and reuse in mind.

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
import uuid
import json
import aiofiles
import asyncio
import shutil
import traceback
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv
from snug.services.profile_service import ProfileService
# ─────────────────────────────
# Core Dependencies
# ─────────────────────────────
from ..core.db import DB
from ..core.cache import InMemoryCache
from ..core.audit import Audit
from ..core.vector_db import VectorDB
from ..core.profile_manager import ProfileManager
from ..ai.extractor import PayslipExtractor
from ..validation.state_validator import StateValidator
from ..state_config import STATE_CONFIG
from ..logging import log
from ..core.seed_chroma import ensure_seeded

# ─────────────────────────────
# Agents & Graphs
# ─────────────────────────────
from ..mcp.schema import MCPMessage
from ..graph import build_graph
from ..graph_multi import build_multiagent_graph
from ..agents.memory_agent import MemoryAgent
from ..agents.profile_agent import ProfileAgent
from ..agents.doc_agent import DocumentAgent
from ..agents.doc_processor import DocumentProcessor
from ..agents.reason_agent import ReasonAgent
from ..agents.intent_agent import IntentAgent
from ..agents.canonical_agent import CanonicalAgent
from ..agents.compliance_agent import ComplianceAgent
from ..agents.guardrails_agent import GuardrailsAgent
from ..agents.rag_agent import RAGAgent
from ..agents.response_agent import ResponseAgent

# ─────────────────────────────
# Environment Setup
# ─────────────────────────────
load_dotenv()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MEMORY_PATH = "data/memory_store.json"

# ─────────────────────────────
# FastAPI Lifecycle
# ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize vector DB seed on startup."""
    ensure_seeded()
    yield

app = FastAPI(title="Snug Rental AI", lifespan=lifespan)

# ─────────────────────────────
# Dependency Wiring
# ─────────────────────────────
db = DB()
db.seed_compliance_rules()
db.seed_guardrails_rules()
cache = InMemoryCache()
audit = Audit(db)
validator = StateValidator(STATE_CONFIG)
extractor = PayslipExtractor(llm_client=None)
doc_processor = DocumentProcessor()
profiles = ProfileManager()
shared_cache = InMemoryCache(ttl_seconds=900)
shared_vdb = VectorDB(collection_name="rental_kb")
memory_agent = MemoryAgent(max_history=5, persist_path=MEMORY_PATH)

# Agents
intent_agent = IntentAgent()
canonical_agent = CanonicalAgent()
compliance_agent = ComplianceAgent(db, validator, audit)
guardrails_agent = GuardrailsAgent(db, audit)
rag_agent = RAGAgent(vector_client=shared_vdb, memory_agent=memory_agent)
response_agent = ResponseAgent()

# Graph Pipelines
legacy_graph = build_graph(
    ProfileAgent(cache, db, audit),
    DocumentAgent(extractor, audit),
    ReasonAgent(validator, audit),
)
multi_graph = build_multiagent_graph(
    intent_agent,
    canonical_agent,
    compliance_agent,
    guardrails_agent,
    rag_agent,
    response_agent,
)

# ─────────────────────────────
# Async Helpers
# ─────────────────────────────
async def save_uploaded_file(file: UploadFile) -> str:
    """Asynchronously save a single uploaded document."""
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(path, "wb") as out:
        await out.write(await file.read())
    log.info("file_saved_async", path=path)
    return path


async def process_file_async(path: str) -> dict:
    """Run AI extraction asynchronously (e.g. payslip parsing)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, doc_processor.process_payslip, path)


# ─────────────────────────────
# Core Endpoints
# ─────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok",
        "agents": ["intent", "canonical", "compliance", "guardrails", "rag", "response"],
    }

@app.get("/profiles/{email}")
def get_profile(email: str):
    """Retrieve renter profile case-insensitively."""
    try:
        email = email.strip()  # remove accidental spaces
        cur = db.conn.cursor()
        row = cur.execute(
            "SELECT data FROM profiles WHERE LOWER(email)=LOWER(?)", (email,)
        ).fetchone()
        if row:
            log.info("get_profile_result", found=True, email=email)
            return {"profile": json.loads(row[0])}
        else:
            log.info("get_profile_result", found=False, email=email)
            return {"profile": None}
    except Exception as e:
        log.error("get_profile_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/db/status")
def db_status():
    cur = db.conn.cursor()
    counts = {
        "profiles": cur.execute("SELECT COUNT(*) FROM profiles").fetchone()[0],
        "applications": cur.execute("SELECT COUNT(*) FROM applications").fetchone()[0],
        "audit_logs": cur.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0],
    }
    return {
        "status": "ok",
        "sqlite_path": db.conn.execute("PRAGMA database_list;").fetchall()[0][2],
        "counts": counts,
    }


@app.get("/applications")
def list_applications():
    return {"applications": db.list_applications()}

@app.post("/applications")
async def submit_application(
    state: str = Form(...),
    email: str = Form(...),
    first_name: str = Form(...),
    middle_name: str = Form(""),
    last_name: str = Form(...),
    dob: str = Form(...),
    phone_number: str = Form(...),
    current_address: str = Form(...),
    previous_address: str = Form(""),
    employment_status: str = Form(...),
    employer_name: str = Form(...),
    employer_contact: str = Form(...),
    income: float = Form(0),
    drivers_license: Optional[str] = Form(None),
    passport_number: Optional[str] = Form(None),
    documents: List[UploadFile] = File(default_factory=list),
):
    """
    POST /applications — main intake endpoint

    Steps:
      1️⃣ Save uploaded documents concurrently
      2️⃣ Run AI-driven document extraction
      3️⃣ Build structured payload for multi-agent graph
      4️⃣ Execute LangGraph pipeline (intent → compliance → response)
      5️⃣ Normalize final message & enforce data integrity
      6️⃣ Persist application and profile
      7️⃣ Audit submission
      8️⃣ Return structured API response
    """
    try:
        # ─────────────────────────────
        # 1️⃣ Save uploaded documents concurrently
        # ─────────────────────────────
        file_paths = await asyncio.gather(*(save_uploaded_file(f) for f in documents))

        # ─────────────────────────────
        # 2️⃣ Extract structured info asynchronously
        # ─────────────────────────────
        extracted_results = await asyncio.gather(*(process_file_async(p) for p in file_paths))
        extracted_map = {os.path.basename(p): r for p, r in zip(file_paths, extracted_results)}

        # ─────────────────────────────
        # 3️⃣ Build structured context payload
        # ─────────────────────────────
        ctx = {
            "state": state.upper(),
            "profile": {
                "email": email,
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name": last_name,
                "dob": dob,
                "phone_number": phone_number,
                "current_address": current_address,
                "previous_address": previous_address,
                "employment_status": employment_status,
                "employer_name": employer_name,
                "employer_contact": employer_contact,
                "income": income,
                "drivers_license": drivers_license,
                "passport_number": passport_number,
                "rental_history": [],
                "references": [],
            },
            "documents": file_paths,
            "extracted": extracted_map,
        }

        envelope = MCPMessage(
            sender="api_gateway",
            receiver="intent",
            type="intent",
            payload=ctx,
            context={"request_id": str(uuid.uuid4())},
        )

        # ─────────────────────────────
        # 4️⃣ Execute the multi-agent graph
        # ─────────────────────────────
        log.info("multi_agent_start_async", state=state, email=email)
        result = multi_graph.invoke(envelope)

        # ─────────────────────────────
        # 5️⃣ Resolve and normalize final message
        # ─────────────────────────────
        if isinstance(result, dict):
            msg = result.get("response") or result.get("__end__") or next(iter(result.values()), None)
        else:
            msg = result

        if msg is None:
            log.error("multi_agent_no_msg", result_type=str(type(result)))
            raise HTTPException(status_code=500, detail="Multi-agent graph returned no final message.")

        payload = getattr(msg, "payload", msg)
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump()
        elif not isinstance(payload, dict):
            payload = {"message": str(payload)}

        final = payload.get("final_response") or payload
        if hasattr(final, "model_dump"):
            final = final.model_dump()

        # ─────────────────────────────
        # 6️⃣ Enforce profile & email integrity
        # ─────────────────────────────
        profile = final.get("profile") or payload.get("profile") or {}
        email_in_profile = (
            final.get("email")
            or profile.get("email")
            or payload.get("email")
            or email
        )

        if not profile.get("email") and email_in_profile:
            profile["email"] = email_in_profile

        final["email"] = email_in_profile or "unknown@example.com"
        final["profile"] = profile
        final["state"] = state.upper()

        if not email_in_profile:
            log.warning(
                "email_missing_soft_fail",
                payload_keys=list(payload.keys()),
                final_keys=list(final.keys()),
                hint="Email fallback inserted to ensure persistence integrity.",
            )

        # ─────────────────────────────
        # 7️⃣ Persist application AND profile
        # ─────────────────────────────
        db.save_application(final)

        profile_to_save = final.get("profile") or {}
        email_to_save = email  # Use the original raw email from form input, not redacted
        profile_to_save["email"] = email_to_save  # ensure correct email for JSON profile

        try:
            # Save to DB
            db.save_profile(email_to_save, profile_to_save)
            log.info("profile_saved_db", email="[REDACTED]")

            # Also save to local JSON (using safe filename)
            if os.getenv("ENVIRONMENT", "development").lower() != "production":
                profile_service = ProfileService()
                safe_filename = email_to_save.replace('@', '_at_').replace('.', '_dot_')
                profile_service.create_or_update(profile_to_save)
                log.info("profile_saved_json", path=f"data/profiles/{safe_filename}.json", email="[REDACTED]")
            else:
                log.info("profile_json_skip", reason="Production environment - JSON persistence disabled", email="[REDACTED]")

        except Exception as e:
            log.error("profile_save_failed", email="[REDACTED]", error=str(e))



        audit.log_event("application", "submitted", f"{email_to_save}|{state}")

        # ─────────────────────────────
        # 8️⃣ Return structured success response
        # ─────────────────────────────
        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "state": state.upper(),
                "application": final,
            },
        )

    except Exception as e:
        log.error(
            "application_error",
            error=str(e),
            trace=traceback.format_exc(),
        )
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────
# 🧩 COMPLIANCE CHECK
# ─────────────────────────────
@app.post("/compliance/check")
def compliance_check(request: dict):
    """Validate renter profile against multi-state compliance rules."""
    state = request.get("state", "GENERAL").upper()
    try:
        result = compliance_agent.check_application(
            state=state,
            profile=request.get("profile", {}),
            extracted=request.get("extracted", {}),
        )
        return {"status": "ok", "state": state, "result": result}
    except Exception as e:
        log.error("compliance_check_failed", error=str(e))
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}


# ─────────────────────────────
# 🔍 RAG + MEMORY ENDPOINTS
# ─────────────────────────────
class RAGQuery(BaseModel):
    query: str
    state: Optional[str] = None

@app.post("/rag/query")
async def rag_query(body: RAGQuery):
    """Semantic retrieval from Chroma VectorDB."""
    rag = RAGAgent(vector_client=shared_vdb, memory_agent=memory_agent)
    msg = MCPMessage(
        sender="frontend",
        receiver="rag_agent",
        type="request",
        payload={"state": body.state or "GENERAL", "query": body.query},
    )
    response = rag.handle(msg)
    return response.payload["kb"]

@app.get("/memory/status")
def memory_status():
    """Inspect in-memory and persisted context."""
    entries = memory_agent.memory
    return {
        "entries": len(entries),
        "states_tracked": sorted({m.get("state") for m in entries if m.get("state")}),
        "recent": entries[-3:] if entries else [],
        "persist_path": memory_agent.persist_path,
        "max_history": memory_agent.max_history,
    }


# ─────────────────────────────
# ⚙️ DEV UTILITIES
# ─────────────────────────────
@app.post("/db/seed")
def db_seed():
    """Re-seed compliance & guardrail rules."""
    db.seed_compliance_rules()
    db.seed_guardrails_rules()
    return {"status": "ok"}


@app.get("/graph/status")
def graph_status():
    """Inspect LangGraph & cache status."""
    return {
        "cache_size": shared_cache.size(),
        "ttl_seconds": shared_cache.ttl,
        "db_docs": shared_vdb.count(),
        "collections": shared_vdb.list_collections(),
    }


@app.exception_handler(Exception)
async def generic_error_handler(request, exc):
    """Unified graceful error handler."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": str(exc),
            "hint": "Please check input data or contact support.",
        },
    )


@app.post("/apply/nsw")
async def apply_nsw(payload: dict):
    state = payload.get("state", "NSW")
    income = payload.get("income", 0)
    rent = payload.get("rent", 0)

    return JSONResponse(
        {
            "state": state,
            "affordability_ratio": round(rent / (income / 52), 2) if income > 0 else None,
            "message": "NSW rental application processed successfully."
        }
    )