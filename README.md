# Crypto Council

A public hearing for crypto calls, built for the RYO-CHAN Hackathon 2026 (Track 1 Autonomous Agents, with Track 2 Dashboards and Interfaces as a second entry).

A bull and a bear argue about a token using only live evidence from RYO's read-only research tools. A judge rules. You can interrupt at any time with a challenge such as "what if funding flips?" or "check safety on that token again". The council re-runs the relevant RYO tools live, the agents answer with the new evidence, and the receipt records the call before and after.

## What makes the reasoning checkable

- Every tool call is stored as numbered evidence (E1, E2 and so on) with its arguments, timestamp and status.
- Every claim must cite evidence. Every number in a claim is checked against the cited evidence. Claims that fail are removed and recorded with the reason.
- A tool that fails or is rate limited is recorded as unavailable. Nothing is estimated or filled in. Agents are told what is missing, and the judge lists it as unresolved.
- Practice levels (entry, stop, target) are computed in code from the reported price and ATR(14). They are never written by the model.
- Cases, evidence and events live in SQLite. A restart keeps every receipt, marks unfinished hearings as interrupted, and the event stream resumes from the last event id.

## Layout

```
backend/    FastAPI service, RYO MCP client, agents, cross-examination, storage
frontend/   React and TypeScript interface (Trial Room, Case Board, Receipt)
docs/       Receipt schema
```

Backend modules: `ryo/` (MCP client, schema adapter, ledger, cache), `agents/` (model interface, prompts, bull, bear, judge, claim checks, plan), `crossexam/` (challenge planning, before and after diff), `receipts/` (schema, SQLite store, event bus), `api/` (routes, server-sent events, health), `orchestrator.py` (the hearing and cross-examination flow).

## Run it

Requirements: Python 3.11 or newer, Node 20 or newer.

```
cp .env.example .env
```

Fill in `RYO_MCP_URL` and the RYO credentials from the MCP Builder Guide, plus `LLM_MODEL` and `LLM_API_KEY`.

```
cd backend
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app.main:app --port 8000
```

```
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Trial Room shows a notice if the model or the RYO server is not reachable, and `GET /api/health` lists the tools the RYO server offers and any it does not.

With Docker: `docker compose up --build`, then open http://localhost:8080.

## Configuration notes

- RYO transport is `streamable_http` by default. Set `RYO_TRANSPORT=sse` if the server uses SSE.
- The auth header defaults to `Authorization: Bearer <RYO_API_TOKEN>`. Change `RYO_AUTH_HEADER` and `RYO_AUTH_SCHEME` if the guide specifies otherwise.
- Tool inputs are mapped from the schemas the server publishes, so argument names are not hard coded.
- `LLM_PROVIDER=anthropic` uses the Anthropic Messages API. Any other value uses an OpenAI compatible chat completions endpoint at `LLM_BASE_URL`.

## Tests

```
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest
```

The suite starts a real MCP server over streamable HTTP and drives the client, tools, orchestrator and API against it. The test server returns fixed synthetic data and exists only under `backend/tests`. A scripted model stands in for the LLM in tests so no key is needed.

`backend/scripts/seed_cases.py` runs real hearings against the live RYO server to populate the Case Board: `python -m scripts.seed_cases BTC ETH SOL`.

## Disclosures

Libraries: FastAPI, Uvicorn, httpx, Pydantic, pydantic-settings, the official MCP Python SDK, React, React Router, Vite, TypeScript, pytest. No starter template was used. The bring-your-own model is set by `LLM_MODEL`.

The RYO research tools are read-only. Practice levels are shown for discussion and nothing is traded.

## Not built yet

Reputation scoring (calls resolved at a fixed horizon and scored on calibration, not profit) and the asynchronous jury room are the next two features. The receipt format already leaves room for both.
