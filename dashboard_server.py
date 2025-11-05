from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from cartesia_client import CartesiaClient
from config import AGENT_ID


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LEADS_FILE = DATA_DIR / "leads.json"


def _read_leads() -> Dict[str, Any]:
    if not LEADS_FILE.exists():
        return {"accepted": {}, "declined": {}}
    try:
        return json.loads(LEADS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"accepted": {}, "declined": {}}


def _write_leads(data: Dict[str, Any]) -> None:
    LEADS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


app = FastAPI(title="Renovation Leads Dashboard")


@app.get("/", response_class=HTMLResponse)
async def dashboard() -> str:
    # Minimal client-side UI; calls our API routes
    return (
        """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Leads Dashboard</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin: 24px; }
      .row { display: grid; grid-template-columns: 360px 1fr; gap: 24px; }
      .card { border: 1px solid #e2e2e2; border-radius: 8px; padding: 12px; }
      .btn { padding: 6px 10px; border: 1px solid #444; border-radius: 6px; background: white; cursor: pointer; }
      .btn.primary { background: #0b5; color: white; border: none; }
      .btn.danger { background: #d33; color: white; border: none; }
      .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #f3f3f3; }
      .muted { color: #666; }
      ul { list-style: none; padding: 0; margin: 0; }
      li { padding: 8px; border-bottom: 1px solid #eee; cursor: pointer; }
      li:hover { background: #fafafa; }
      audio { width: 100%; margin-top: 8px; }
      .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    </style>
  </head>
  <body>
    <h1>Leads Dashboard</h1>
    <div class="row">
      <div class="card">
        <h3>Recent Calls</h3>
        <ul id="calls"></ul>
      </div>
      <div class="card">
        <h3 id="title">Select a call</h3>
        <div id="details" class="muted">No call selected.</div>
      </div>
    </div>
    <script>
      const callsEl = document.getElementById('calls');
      const detailsEl = document.getElementById('details');
      const titleEl = document.getElementById('title');

      async function loadCalls() {
        const res = await fetch('/api/calls');
        const data = await res.json();
        callsEl.innerHTML = '';
        (data.data || []).forEach(call => {
          const li = document.createElement('li');
          const when = call.start_time || 'N/A';
          const status = call.status;
          const caller = call.telephony_params?.to || 'Unknown';
          li.innerHTML = `<div><strong>${caller}</strong> <span class="pill">${status}</span></div><div class="muted">${when}</div>`;
          li.onclick = () => selectCall(call.id);
          callsEl.appendChild(li);
        });
      }

      async function selectCall(id) {
        titleEl.textContent = `Call ${id}`;
        detailsEl.innerHTML = 'Loading...';
        const [callRes, metaRes] = await Promise.all([
          fetch(`/api/calls/${id}`),
          fetch('/api/leads')
        ]);
        const call = await callRes.json();
        const leads = await metaRes.json();
        const accepted = !!leads.accepted[id];
        const declined = !!leads.declined[id];

        const transcript = call.transcript || [];
        const lines = transcript.map(t => `${t.role}: ${t.text || ''}`).join('\n');

        detailsEl.innerHTML = `
          <div>
            <div><strong>Status:</strong> ${call.status}</div>
            <div><strong>From:</strong> ${call.telephony_params?.to || ''}</div>
            <div><strong>To:</strong> ${call.telephony_params?.from || ''}</div>
            <div><strong>Summary:</strong> ${call.summary || ''}</div>
            <div class="mono" style="white-space: pre-wrap; margin-top: 8px;">${lines}</div>
            <audio controls src="/api/calls/${id}/audio"></audio>
            <div style="margin-top: 8px; display: flex; gap: 8px;">
              <button class="btn primary" onclick="acceptLead('${id}')" ${accepted ? 'disabled' : ''}>Accept Lead</button>
              <button class="btn danger" onclick="declineLead('${id}')" ${declined ? 'disabled' : ''}>Decline</button>
            </div>
          </div>
        `;
      }

      async function acceptLead(id) {
        await fetch(`/api/calls/${id}/accept`, { method: 'POST' });
        await selectCall(id);
      }
      async function declineLead(id) {
        await fetch(`/api/calls/${id}/decline`, { method: 'POST' });
        await selectCall(id);
      }

      loadCalls();
    </script>
  </body>
</html>
        """
    )


@app.get("/api/calls")
async def api_list_calls(limit: int = 25) -> JSONResponse:
    async with CartesiaClient() as _:
        pass
    client = CartesiaClient()
    try:
        data = await client.list_calls(AGENT_ID, expand_transcript=True, limit=limit)
    finally:
        await client.aclose()
    return JSONResponse(data)


@app.get("/api/calls/{call_id}")
async def api_get_call(call_id: str) -> JSONResponse:
    client = CartesiaClient()
    try:
        data = await client.get_call(call_id)
    finally:
        await client.aclose()
    return JSONResponse(data)


@app.get("/api/calls/{call_id}/audio")
async def api_get_call_audio(call_id: str) -> StreamingResponse:
    client = CartesiaClient()
    try:
        resp = await client.stream_call_audio(call_id)
        async def _gen():
            async for chunk in resp.aiter_bytes():
                yield chunk
        return StreamingResponse(_gen(), media_type="audio/wav")
    finally:
        await client.aclose()


@app.get("/api/leads")
async def api_leads() -> JSONResponse:
    return JSONResponse(_read_leads())


@app.post("/api/calls/{call_id}/accept")
async def api_accept(call_id: str) -> Response:
    data = _read_leads()
    data.setdefault("accepted", {})[call_id] = True
    # If previously declined, remove it
    data.setdefault("declined", {}).pop(call_id, None)
    _write_leads(data)
    return Response(status_code=204)


@app.post("/api/calls/{call_id}/decline")
async def api_decline(call_id: str) -> Response:
    data = _read_leads()
    data.setdefault("declined", {})[call_id] = True
    data.setdefault("accepted", {}).pop(call_id, None)
    _write_leads(data)
    return Response(status_code=204)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()


