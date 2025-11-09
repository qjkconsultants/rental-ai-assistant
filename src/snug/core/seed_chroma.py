# src/snug/core/seed_chroma.py
from snug.core.vector_db import VectorDB
from snug.logging import log

def ensure_seeded():
    """Seed Chroma with example documents if empty."""
    vdb = VectorDB(collection_name="rental_kb")

    # Check if already seeded
    results = vdb.search("rental application", limit=1)
    if results:
        log.info("chroma_seed", status="already_seeded")
        return vdb

    docs = [
        "NSW rental applications require proof of income, identity, and rental history.",
        "VIC applicants must provide passport or driver’s license, income verification, and references.",
        "QLD tenants should include ID, proof of employment, and previous rental references.",
        "General rental guidance: ensure all documents are clear and recent."
    ]
    metas = [{"state": "NSW"}, {"state": "VIC"}, {"state": "QLD"}, {"state": "GENERAL"}]
    vdb.add_documents(docs, metas)
    log.info("chroma_seed", status="seeded", count=len(docs))
    return vdb
