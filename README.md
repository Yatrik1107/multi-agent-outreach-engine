# Smart Lead Qualifier & Outreach Agent

A lightweight multi-agent sales intelligence POC built with **FastAPI** that helps teams go from a raw lead list to a prioritized, personalized outreach workflow.

> Demo video: [Watch the walkthrough](Demo%20Video/Lead%20Generation%20And%20Outreach%20Engine.mp4)


This system ingests CSV/XLSX/XLS lead lists, researches each lead, scores fit against a configurable Ideal Customer Profile (ICP), drafts personalized outreach, and provides a human-in-the-loop UI for review, export, and send.

---

## What This Demo Shows

This POC demonstrates how AI can support an early-stage lead qualification workflow without requiring a complex CRM integration.

### Core flow

1. **Upload leads** from a CSV,XLSX, or XLS file.
2. **Research Agent** gathers public company context.
3. **Scoring Agent** evaluates fit against a configurable ICP.
4. **Outreach Agent** drafts personalized outreach emails.
5. A user can **review, edit, regenerate, export, and send** outreach from the UI.
6. The built-in **chat assistant** can answer questions using the latest processed lead set as context.

---

## Why This Matters

In a real sales workflow, teams often spend significant time on:

- manually researching companies
- deciding which leads to prioritize
- writing first-touch emails from scratch
- aligning messaging to ICP fit
- preparing polished exports for internal or client-facing review

This POC compresses that workflow into a single application.

It is intentionally lightweight, but the flow is real and functional.

---

## Key Capabilities

### 1. CSV,XLSX, or XLS lead ingestion
Upload a lead list from the UI using a simple CSV,XLSX, or XLS file.

Supported column aliases include:

- `company`, `url`, `email`

### 2. Research Agent
The Research Agent gathers lead-level context such as:

- industry
- estimated company size
- recent activity
- company description

Depending on configuration, this can run with:

- mock/demo mode
- live LLM mode

### 3. Scoring Agent
Each lead is scored against the active ICP using:

- target industries
- keyword overlap
- ICP notes
- research context

Output includes:

- numerical score
- rationale for why the lead was scored that way

### 4. Outreach Agent
The Outreach Agent drafts a personalized outreach email with:

- subject line
- email body
- configurable sign-off
- optional greeting informed by discovered or provided contact email

### 5. Human-in-the-loop editing
This is not a black-box system.

Users can:

- edit recipient email
- edit subject
- edit email body
- save a final version per lead

Saved final drafts are used for:

- export
- copy
- send

### 6. Recipient visibility and discovery
The UI shows which recipient will be used for each lead.

Recipient resolution order:

1. manually overridden recipient
2. CSV,XLSX, or XLS `contact_email`
3. discovered email from website
4. prompt user during send if no email is available

### 7. Single-lead regeneration
Users can regenerate one lead at a time without re-uploading the full CSV,XLSX, or XLS.

This allows fast iteration when:

- research looks weak
- ICP has changed
- outreach needs a fresh version

### 8. Export for PM / finance / stakeholders
Users can export the last run as:

- CSV
- JSON
- XLSX

Export includes:

- company
- website
- contact email info
- score
- subject
- body
- whether the final draft was edited

### 9. Chat assistant with run context
The built-in assistant can answer questions about the most recent processed leads, for example:

- "Which company scored the highest?"
- "Why was this lead scored low?"
- "Summarize the outreach generated for this batch."

### 10. Email sending
SMTP is configured so users can send the current effective outreach directly from the UI.

## Architecture Overview

### Backend
- **FastAPI**
- API versioning under `api/v1`
- modular services and agent separation

### Frontend
- simple HTML/JS UI served by FastAPI
- no heavy frontend framework required for the POC

### Agent roles
- `ResearchAgent`
- `ScoringAgent`
- `OutreachAgent`
- `ChatAgent`

### Supporting services
- CSV,XLSX, or XLS ingestion
- pipeline orchestration
- ICP store
- in-memory pipeline context
- email discovery
- LLM provider factory
- SMTP send

---

## Project Structure

```text
SmartLeadEngine/
├── frontend/
│   ├── app.js
│   ├── assets
│   │   └── style.css
│   └── index.html
├── README.md
├── Real_Data.xlsx
├── requirements.txt
├── smartlead
│   ├── agents
│   │   ├── base.py
│   │   ├── chat_agent.py
│   │   ├── __init__.py
│   │   ├── outreach_agent.py
│   │   ├── research_agent.py
│   │   └── scoring_agent.py
│   ├── api
│   │   └── v1
│   │       ├── endpoints
│   │       │   ├── chat.py
│   │       │   ├── health.py
│   │       │   ├── icp.py
│   │       │   ├── __init__.py
│   │       │   └── leads.py
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── schemas
│   │           ├── chat.py
│   │           ├── __init__.py
│   │           ├── leads.py
│   │           ├── pipeline.py
│   │           └── upload.py
│   ├── core
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── __init__.py
│   ├── main.py
│   ├── services
│   │   ├── chat_session.py
│   │   ├── csv_ingest.py
│   │   ├── email_discovery.py
│   │   ├── excel_ingest.py
│   │   ├── gemini_llm.py
│   │   ├── gmail_outreach.py
│   │   ├── grok_llm.py
│   │   ├── icp.py
│   │   ├── icp_store.py
│   │   ├── __init__.py
│   │   ├── leads_ingest.py
│   │   ├── llm_factory.py
│   │   ├── openai_llm.py
│   │   ├── pipeline_context.py
│   │   ├── pipeline.py
│   │   └── tavily_search.py
│   └── utils
│       ├── helpers.py
│       └── __init__.py
├── test_leads_alt.csv
└── test_leads.csv

---

## Quickstart (local, development)

1. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app (development):

```bash
uvicorn smartlead.main:app --reload
```

4. Open the UI at http://127.0.0.1:8000/

Notes:
- The demo defaults to `USE_MOCK_LLM=true` (no external LLM calls). See [smartlead/core/settings.py](smartlead/core/settings.py) for full options.
- To use a live LLM, set `USE_MOCK_LLM=false` and provide credentials for `LLM_PROVIDER` (`gemini`, `openai`, or `grok`).

---

## Configuration

Configuration is driven by environment variables and the `Settings` class in [smartlead/core/settings.py](smartlead/core/settings.py).

- `USE_MOCK_LLM` — `true|false` (default `true`) to use demo/mock LLM outputs.
- `LLM_PROVIDER` — `gemini|openai|grok` (set corresponding API keys in env).
- `LEADGEN_PROVIDER` — `google|openai|exa|tavily` (controls lead-generation backend).
- SMTP: set `SENDER_EMAIL` and `GMAIL_SMTP_KEY` (if using Gmail app password) to enable send.

Refer to the `Settings` class for additional tunables (leadgen caps, grounding model, discovery options).

---

## Dependencies

Core dependencies are listed in [`requirements.txt`](requirements.txt). Highlights:

- `fastapi`, `uvicorn`
- `google-genai`, `openai`, `grok` wrappers (optional)
- `openpyxl`, `xlrd` for Excel handling
- `tavily-python`, `exa-py` for additional lead generation backends

---

## API & Usage

The FastAPI app exposes a versioned router at `/api/v1` (see [smartlead/api/v1/router.py](smartlead/api/v1/router.py)).

Examples:

- Health: `GET /api/v1/health`
- Upload leads: `POST /api/v1/leads/upload` (multipart file upload)
- List processed leads: `GET /api/v1/leads`
- Chat assistant: `POST /api/v1/chat`

Use the UI at `/` to perform uploads, run the pipeline, review/edit drafts, and export or send.

---

## Demo video

The demo video included with the repo is at:

- [Demo Video/Lead Generation And Outreach Engine.mp4](Demo Video/Lead Generation And Outreach Engine.mp4)

Play it directly in this README (top of file) or download it to view locally.

---

## Credits

- Demo & project: Yatrik Patel
- Demo video included in the repository: [Demo Video/Lead Generation And Outreach Engine.mp4]
- Questions, issues, or contributions: please open an issue or submit a pull request.

---