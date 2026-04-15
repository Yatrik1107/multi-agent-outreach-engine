import csv
import io
import re
from typing import Any

from fastapi import UploadFile

from smartlead.api.v1.schemas.leads import LeadInput


def _norm_header(h: str) -> str:
    key = h.strip().lower()
    key = re.sub(r"[\s\-]+", "_", key)
    return key


def _get(row: dict[str, Any], *names: str) -> str:
    for n in names:
        v = row.get(n)
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip()
        else:
            s = str(v).strip()
        if s:
            return s
    return ""


def _parse_csv_text(raw: str) -> tuple[list[LeadInput], list[str]]:
    errors: list[str] = []
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames:
        return [], ["CSV has no header row."]

    fieldmap = {_norm_header(h): h for h in reader.fieldnames if h}

    def pick(*candidates: str) -> str | None:
        for c in candidates:
            k = _norm_header(c)
            if k in fieldmap:
                return fieldmap[k]
        return None

    col_company = pick("company_name", "company", "name", "organization")
    col_website = pick("website", "url", "domain", "company_website")
    col_email = pick("contact_email", "email", "e_mail", "contact")

    if not col_company:
        return [], [
            "Missing required column. Provide at least one of: "
            "company_name, company, name, organization.",
        ]

    leads: list[LeadInput] = []
    for idx, row in enumerate(reader, start=2):
        company = _get(row, col_company)
        if not company:
            errors.append(f"Row {idx}: empty company; skipped.")
            continue
        website = _get(row, col_website) if col_website else ""
        email = _get(row, col_email) if col_email else ""
        try:
            leads.append(
                LeadInput(
                    company_name=company,
                    website=website,
                    contact_email=email,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Row {idx}: invalid data ({exc}).")

    if not leads and not errors:
        errors.append("No data rows found after the header.")

    return leads, errors


def parse_leads_csv_bytes(raw_bytes: bytes) -> tuple[list[LeadInput], list[str]]:
    try:
        raw = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], ["CSV must be UTF-8 encoded."]
    return _parse_csv_text(raw)


async def parse_leads_csv(file: UploadFile) -> tuple[list[LeadInput], list[str]]:
    raw_bytes = await file.read()
    return parse_leads_csv_bytes(raw_bytes)