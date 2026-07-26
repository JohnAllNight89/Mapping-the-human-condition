"""
Blueprint Calculator — FastAPI web server.

Routes:
  GET  /              → serve the frontend (templates/index.html)
  GET  /api/health    → engine health check
  POST /api/calculate → run pipeline, return frontend JSON
  GET  /api/audit     → re-run pipeline, return full ledger as downloadable JSON

All routes except GET / require HTTP Basic Auth (env: ADMIN_USER / ADMIN_PASS,
defaults: admin / blueprint). The browser caches credentials on the first
challenge so the frontend's subsequent XHR calls work seamlessly.
"""
from __future__ import annotations

import os
import secrets
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from blueprint_calculator.pipeline import run_pipeline
from api_adapter import adapt

_ADMIN_USER = os.environ.get("ADMIN_USER", "admin").encode()
_ADMIN_PASS = os.environ.get("ADMIN_PASS", "blueprint").encode()

app = FastAPI(title="Blueprint Calculator — Mapping the Human Condition")
_security = HTTPBasic()


def _require_auth(creds: HTTPBasicCredentials = Depends(_security)) -> str:
    ok = secrets.compare_digest(creds.username.encode(), _ADMIN_USER) and \
         secrets.compare_digest(creds.password.encode(), _ADMIN_PASS)
    if not ok:
        raise HTTPException(
            status_code=401, detail="Unauthorized",
            headers={"WWW-Authenticate": 'Basic realm="Blueprint Calculator"'},
        )
    return creds.username


class CalculateRequest(BaseModel):
    name: str
    birth_date: str
    birth_time: str = ""
    birth_place: str = ""


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("templates/index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "engine": "Mapping the Human Condition — Blueprint Pipeline v1",
    }


@app.post("/api/calculate")
async def calculate(req: CalculateRequest, _: str = Depends(_require_auth)):
    try:
        report = run_pipeline(
            name=req.name,
            birth_date=req.birth_date,
            birth_time=req.birth_time,
            birth_place=req.birth_place,
            today=date.today(),
        )
        return adapt(report)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/audit")
async def audit(
    name: str = Query(...),
    birth_date: str = Query(...),
    birth_time: str = Query(""),
    birth_place: str = Query(""),
    _: str = Depends(_require_auth),
):
    """Re-run the pipeline and return the full provenance ledger as a JSON download."""
    try:
        report = run_pipeline(
            name=name, birth_date=birth_date,
            birth_time=birth_time, birth_place=birth_place,
            today=date.today(),
        )
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in name)
        filename = f"audit-{safe_name}-{birth_date}.json"
        return JSONResponse(
            content=report.ledger.to_dict(),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
