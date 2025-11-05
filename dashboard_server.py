import os
import env  # noqa: F401  Ensures .env is loaded on import
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from loguru import logger

from cartesia_client import CartesiaClient


AGENT_ID = os.getenv("AGENT_ID", "agent_tLP2HN5nF4SMpHBSYMWzZY")
EXPECTED_AGENT_NUMBER = os.getenv("AGENT_PHONE_NUMBER", "+12173874858")


app = FastAPI(title="Renovation Leads Dashboard")
client = CartesiaClient()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return (
        """
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Contractor Leads</title>
    <style>
      body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 20px; }
      h1 { margin-bottom: 8px; }
      .call { border: 1px solid #ddd; border-radius: 8px; padding: 12px; margin: 10px 0; }
      .meta { color: #555; font-size: 14px; }
      .row { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
      audio { width: 320px; }
      .transcript { white-space: pre-wrap; background: #fafafa; padding: 8px; border-radius: 6px; border: 1px solid #eee; max-height: 240px; overflow: auto; }
      button { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 8px 12px; cursor: pointer; }
      button[disabled] { background: #94a3b8; cursor: not-allowed; }
      .error { color: #b91c1c; margin: 8px 0; }
    </style>
  </head>
  <body>
    <h1>Contractor Leads</h1>
    <div id="phone" class="meta"></div>
    <div id="error" class="error"></div>
    <div id="calls"></div>
    <script>
      function escapeHtml(s){
        return String(s||'').replace(/[&<>"']/g, function(c){
          return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);
        });
      }
      async function fetchJson(url){
        const r = await fetch(url);
        if(!r.ok){ throw new Error(await r.text()); }
        return r.json();
      }
      function transcriptText(items){
        var lines = [];
        (items||[]).forEach(function(t){ lines.push((t.role||'')+': '+(t.text||'')); });
        return lines.join('\n');
      }
      function callTile(c){
        var id = c.id;
        var audioUrl = '/calls/' + encodeURIComponent(id) + '/audio';
        var tele = c.telephony_params || {};
        var html = '' +
          '<div class="call">' +
            '<div class="row">' +
              '<div><strong>Call</strong> ' + escapeHtml(id) + '</div>' +
              '<div class="meta">Status: ' + escapeHtml(c.status) + ' • From: ' + escapeHtml(tele.to||'') + ' • To: ' + escapeHtml(tele.from||'') + '</div>' +
            '</div>' +
            '<div class="row" style="margin-top:8px;">' +
              '<audio controls src="' + audioUrl + '"></audio>' +
              '<button onclick="acceptLead(\'' + escapeHtml(id) + '\', this)">Accept Lead</button>' +
            '</div>' +
            '<div style="margin-top:8px;">' +
              '<div class="meta">Summary:</div>' +
              '<div>' + escapeHtml(c.summary || 'No summary') + '</div>' +
            '</div>' +
            '<div style="margin-top:8px;">' +
              '<div class="meta">Transcript:</div>' +
              '<div class="transcript">' + escapeHtml(transcriptText(c.transcript)) + '</div>' +
            '</div>' +
          '</div>';
        return html;
      }
      async function acceptLead(id, btn){
        btn.disabled = true; btn.textContent = 'Accepted';
        try { await fetch('/leads/' + encodeURIComponent(id) + '/accept', { method: 'POST' }); }
        catch(e){ console.error(e); btn.disabled = false; btn.textContent = 'Accept Lead'; }
      }
      async function refresh(){
        var err = document.getElementById('error');
        err.textContent = '';
        try {
          var phone = await fetchJson('/agent/phone');
          document.getElementById('phone').textContent = 'Agent ' + (phone.agent_id||'') + ' phone: ' + (phone.number||'unknown');
          var data = await fetchJson('/calls');
          var list = data.data || [];
          document.getElementById('calls').innerHTML = list.map(callTile).join('');
        } catch(e){
          console.error(e);
          err.textContent = 'Failed to load calls: ' + e.message;
        }
      }
      refresh();
      setInterval(refresh, 15000);
    </script>
  </body>
</html>
        """
    )


@app.get("/calls")
async def list_calls() -> Dict[str, Any]:
    try:
        return await client.list_calls(AGENT_ID, expand_transcript=True, limit=50)
    except Exception as e:
        logger.exception("Failed to list calls")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/calls/{call_id}")
async def get_call(call_id: str) -> Dict[str, Any]:
    try:
        return await client.get_call(call_id)
    except Exception as e:
        logger.exception("Failed to get call")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/calls/{call_id}/audio")
async def get_call_audio(call_id: str) -> Response:
    try:
        resp = await client.stream_call_audio(call_id)
        return StreamingResponse(resp.aiter_bytes(), media_type="audio/wav")
    except Exception as e:
        logger.exception("Failed to stream call audio")
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/agent/phone")
async def get_agent_phone() -> Dict[str, Any]:
    try:
        numbers = await client.list_agent_phone_numbers(AGENT_ID)
        number = numbers[0]["number"] if numbers else None
        if number and EXPECTED_AGENT_NUMBER and number.replace("+","") != EXPECTED_AGENT_NUMBER.replace("+",""):
            logger.warning(f"Agent phone mismatch. API={number} EXPECTED={EXPECTED_AGENT_NUMBER}")
        return {"agent_id": AGENT_ID, "number": number}
    except Exception as e:
        logger.exception("Failed to fetch agent phone numbers")
        raise HTTPException(status_code=502, detail=str(e))


# Minimal in-memory store for accepted leads
ACCEPTED: dict[str, str] = {}


@app.post("/leads/{call_id}/accept")
async def accept_lead(call_id: str) -> Dict[str, str]:
    ACCEPTED[call_id] = "accepted"
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("DASHBOARD_PORT", "8080"))
    uvicorn.run("dashboard_server:app", host="0.0.0.0", port=port, reload=False)


