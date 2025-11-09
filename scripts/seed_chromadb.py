# scripts/seed_chromadb.py
from snug.core.vector_db import VectorDB

docs = [
    "In NSW, tenants must provide 100 points of ID including a driver license or passport.",
    "NSW applications require proof of income such as payslips or employment letters.",
    "VIC rental applications typically include a passport or driver license and rental history.",
    "VIC requires income verification, proof of employment, and rental references.",
]

metas = [
    {"state": "NSW", "topic": "ID"},
    {"state": "NSW", "topic": "Income"},
    {"state": "VIC", "topic": "ID"},
    {"state": "VIC", "topic": "Income"},
]

ids = [f"doc{i}" for i in range(1, len(docs) + 1)]

if __name__ == "__main__":
    vdb = VectorDB()
    vdb.add_documents(docs, metas, ids)
