import asyncio
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from line import VoiceAgentApp, VoiceAgentSystem, Bridge
from line.events import (
    UserTranscriptionReceived,
    UserStartedSpeaking,
    UserStoppedSpeaking,
    CallStarted,
    CallEnded,
)
from pydantic import BaseModel

# Data models
class CallInfo(BaseModel):
    call_id: str
    from_number: str
    to_number: str
    start_time: str
    status: str = "incoming"
    transcript: List[Dict[str, str]] = []

# In-memory storage for active calls and call history
active_calls: Dict[str, CallInfo] = {}
call_history: Dict[str, CallInfo] = {}

# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# Create FastAPI app
app = FastAPI(title="Renovation Dashboard")

# Mount static files for the web interface
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Web UI
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Renovation Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        <script src="https://unpkg.com/htmx.org@1.9.6"></script>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold mb-8">Renovation Dashboard</h1>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Active Calls -->
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-xl font-semibold mb-4">Active Calls</h2>
                    <div id="active-calls" class="space-y-4">
                        <!-- Calls will be populated here -->
                    </div>
                </div>
                
                <!-- Call History -->
                <div class="bg-white rounded-lg shadow p-6 md:col-span-2">
                    <h2 class="text-xl font-semibold mb-4">Call History</h2>
                    <div id="call-history" class="space-y-2">
                        <!-- Call history will be populated here -->
                    </div>
                </div>
            </div>
        </div>

        <script>
            // Connect to WebSocket for real-time updates
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log('Received:', data);
                
                if (data.type === 'call_update') {
                    updateCallDisplay(data.call);
                } else if (data.type === 'call_ended') {
                    removeCallDisplay(data.call_id);
                    updateCallHistory(data.call);
                }
            };

            function updateCallDisplay(call) {
                let callElement = document.getElementById(`call-${call.call_id}`);
                
                if (!callElement) {
                    callElement = document.createElement('div');
                    callElement.id = `call-${call.call_id}`;
                    callElement.className = 'p-4 border rounded-lg';
                    document.getElementById('active-calls').prepend(callElement);
                }
                
                callElement.innerHTML = `
                    <div class="font-medium">From: ${call.from_number}</div>
                    <div class="text-sm text-gray-600">To: ${call.to_number}</div>
                    <div class="text-sm text-gray-500">Status: ${call.status}</div>
                    <div class="mt-2 text-sm">
                        <div class="font-medium">Transcript:</div>
                        <div class="bg-gray-50 p-2 rounded mt-1 max-h-40 overflow-y-auto">
                            ${call.transcript.map(t => 
                                `<div class="${t.role === 'user' ? 'text-blue-600' : 'text-green-600'}">
                                    <strong>${t.role}:</strong> ${t.text}
                                </div>`
                            ).join('')}
                        </div>
                    </div>
                `;
            }

            function removeCallDisplay(callId) {
                const callElement = document.getElementById(`call-${callId}`);
                if (callElement) {
                    callElement.remove();
                }
            }

            function updateCallHistory(call) {
                const historyElement = document.createElement('div');
                historyElement.className = 'p-3 border-b';
                historyElement.innerHTML = `
                    <div class="flex justify-between">
                        <div>
                            <span class="font-medium">${call.from_number}</span>
                            <span class="text-sm text-gray-500 ml-2">${new Date(call.start_time).toLocaleString()}</span>
                        </div>
                        <span class="text-sm ${call.status === 'completed' ? 'text-green-600' : 'text-red-600'}">
                            ${call.status}
                        </span>
                    </div>
                `;
                
                const historyContainer = document.getElementById('call-history');
                historyContainer.insertBefore(historyElement, historyContainer.firstChild);
            }
        </script>
    </body>
    </html>
    """

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Voice agent handler
async def handle_call(system: VoiceAgentSystem, call_request):
    call_info = CallInfo(
        call_id=call_request.call_id,
        from_number=call_request.from_number,
        to_number=call_request.to_number,
        start_time=call_request.start_time.isoformat(),
        status="in_progress"
    )
    
    # Add to active calls
    active_calls[call_request.call_id] = call_info
    
    # Notify dashboard
    await manager.broadcast({
        "type": "call_update",
        "call": call_info.dict()
    })
    
    # Create a node for this call
    class CallNode:
        def __init__(self, call_id: str):
            self.call_id = call_id
    
    node = CallNode(call_request.call_id)
    bridge = Bridge(node)
    
    # Handle user speech events
    @bridge.on(UserTranscriptionReceived)
    async def on_transcription(event: UserTranscriptionReceived):
        call_info = active_calls.get(node.call_id)
        if call_info:
            call_info.transcript.append({
                "role": "user",
                "text": event.content,
                "timestamp": event.timestamp.isoformat()
            })
            await manager.broadcast({
                "type": "call_update",
                "call": call_info.dict()
            })
    
    # Handle agent responses
    @bridge.on("AgentResponse")
    async def on_agent_response(event):
        call_info = active_calls.get(node.call_id)
        if call_info:
            call_info.transcript.append({
                "role": "agent",
                "text": event.content,
                "timestamp": event.timestamp.isoformat()
            })
            await manager.broadcast({
                "type": "call_update",
                "call": call_info.dict()
            })
    
    # Handle call end
    @bridge.on("CallEnded")
    async def on_call_ended(_):
        call_info = active_calls.pop(node.call_id, None)
        if call_info:
            call_info.status = "completed"
            call_history[call_info.call_id] = call_info
            
            await manager.broadcast({
                "type": "call_ended",
                "call_id": call_info.call_id,
                "call": call_info.dict()
            })
    
    # Add node to system
    system.with_speaking_node(node, bridge)

# Create VoiceAgentApp
voice_app = VoiceAgentApp(handle_call)

# Mount voice app endpoints
app.mount("/voice", voice_app.app)

# Start the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
