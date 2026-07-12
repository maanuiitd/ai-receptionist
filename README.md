# AI Receptionist — Vapi + LangGraph + Airtable + Google Calendar

An AI phone receptionist for an HVAC business. Vapi handles the voice call;
this FastAPI server runs a LangGraph that executes tools (CRM lookup, booking,
FAQ, emergency escalation) and persists per-call state.

## Architecture

```
Caller ──▶ Vapi (voice + turn-taking, GPT-4.1)
              │  tool calls (webhook, HMAC-verified)
              ▼
        FastAPI /vapi/webhook
              │  thread_id = call_id
              ▼
          LangGraph
   emergency_gate ─▶ classify ─▶ identify / book / reschedule /
                                 cancel / faq / handoff
              │
   Airtable (Contacts, Appointments, CallLogs)
   Google Calendar (availability + events)
```

Design decisions:
- **Emergency gate is deterministic regex, first hop, pre-LLM.** A gas-leak
  call must never depend on model judgment.
- **Google Calendar is source of truth for time**; Airtable mirrors for reporting.
- **Prompts are .md files** in `src/ai_receptionist/prompts/` — edit without code.
- **KB is whole-doc injection**, no vector store, because it's one small doc.
- **MemorySaver checkpointer for dev** — swap for SqliteSaver/Postgres in prod.

## Setup

```bash
echo "3.12" > .python-version      # 3.14 wheels not ready for all deps
uv venv && source .venv/bin/activate
uv sync
cp .env.example .env               # fill in keys
uvicorn ai_receptionist.main:app --reload --port 8000
```

Expose locally with `ngrok http 8000`, then:

```bash
python scripts/deploy_vapi_assistant.py https://<your-ngrok-domain>
```

## Airtable schema

- **Contacts**: Name, Email, Phone, Address
- **Appointments**: Contact (link), Start (date), CalendarEventId, Service, Status
- **CallLogs**: CallId, CallerPhone, Summary, Outcome, Emergency (checkbox), Timestamp

## Google Calendar

Create a service account, download JSON to `secrets/service-account.json`,
share the calendar with the service-account email ("Make changes to events").

## Tests

```bash
uv run pytest
```

## Editing behavior

- Greeting / AI disclosure / tone → `prompts/system.md`
- FAQ content → `data/knowledge_base.md` (restart or call `reload_kb()`)
- Emergency triggers → `services/emergency.py`
