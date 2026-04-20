from __future__ import annotations

from fastapi import UploadFile

from smartlead.services.csv_ingest import parse_leads_csv_bytes
from smartlead.services.excel_ingest import parse_leads_xlsx_bytes, parse_leads_xls_bytes

ALLOWED_EXTS = (".csv", ".xlsx", ".xls")

def _ext(name: str) -> str:
    n = (name or "").lower().strip()
    for e in ALLOWED_EXTS:
        if n.endswith(e):
            return e
    return ""

def parse_leads_upload_bytes(filename: str, raw: bytes):
    e = _ext(filename)
    if e == ".csv":
        return parse_leads_csv_bytes(raw)
    if e == ".xlsx":
        return parse_leads_xlsx_bytes(raw)
    if e == ".xls":
        return parse_leads_xls_bytes(raw)
    return [], [f"Unsupported file type. Upload one of: {', '.join(ALLOWED_EXTS)}."]

async def parse_leads_upload(file: UploadFile):
    raw = await file.read()
    return parse_leads_upload_bytes(file.filename or "", raw)