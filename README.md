# Smart Lead Qualifier & Outreach Agent

A lightweight multi-agent sales intelligence POC built with **FastAPI** that helps teams go from a raw lead list to a prioritized, personalized outreach workflow.

This system takes a CSV of companies, researches each lead, scores it against an Ideal Customer Profile (ICP), drafts personalized outreach, and lets a human review/edit before export or send.

---

## What This Demo Shows

This POC demonstrates how AI can support an early-stage lead qualification workflow without requiring a complex CRM integration.

### Core flow

1. **Upload leads** from a CSV file.
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

### 1. CSV lead ingestion
Upload a lead list from the UI using a simple CSV file.

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
2. CSV `contact_email`
3. discovered email from website
4. prompt user during send if no email is available

### 7. Single-lead regeneration
Users can regenerate one lead at a time without re-uploading the full CSV.

This allows fast iteration when:

- research looks weak
- ICP has changed
- outreach needs a fresh version

### 8. Export for PM / finance / stakeholders
Users can export the last run as:

- CSV
- JSON

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
- CSV ingestion
- pipeline orchestration
- ICP store
- in-memory pipeline context
- email discovery
- LLM provider factory
- optional SMTP send

---

## Project Structure

```text
SmartLeadEngine/
├── frontend/
│   └── index.html
├── smartlead/
│   ├── agents/
│   │   ├── chat_agent.py
│   │   ├── outreach_agent.py
│   │   ├── research_agent.py
│   │   └── scoring_agent.py
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── chat.py
│   │       │   ├── health.py
│   │       │   ├── icp.py
│   │       │   └── leads.py
│   │       └── schemas/
│   │           ├── chat.py
│   │           └── leads.py
│   ├── core/
│   │   └── settings.py
│   ├── services/
│   │   ├── csv_ingest.py
│   │   ├── email_discovery.py
│   │   ├── gemini_llm.py
│   │   ├── openai_llm.py
│   │   ├── grok_llm.py
│   │   ├── icp.py
│   │   ├── icp_store.py
│   │   ├── llm_factory.py
│   │   ├── pipeline.py
│   │   ├── pipeline_context.py
│   │   └── tavily_search.py
│   └── main.py
├── test_leads.csv
├── test_leads_alt.csv
├── test_real_data.csv
├── requirements.txt
├── Dockerfile
└── docker-compose.yml