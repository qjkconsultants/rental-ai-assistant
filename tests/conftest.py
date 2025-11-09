import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from snug.api.app import app
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pathlib import Path

@pytest.fixture(scope="session")
def tmp_payslip(tmp_path_factory):
    p = tmp_path_factory.mktemp("fx") / "payslip.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    c.drawString(72, 800, "Employer: Acme Corp")
    c.drawString(72, 780, "Gross: 8000")
    c.drawString(72, 760, "Net: 6200")
    c.save()
    return p

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac