# Gemini Basic Chat Template

Single system prompt chat agent using Gemini API.

## Customization

To customize this agent for your use case, follow the instructions below.

### Update constants in `config.py`

- **AGENT_PROMPT**: Define the agent's personality, role, and conversation style
- **LOCATION**: Set the agent's current location context
- **INITIAL_MESSAGE**: Set the first message sent to the user when the call is started. Set to None for outbound agents.

## Running the Agent

### Quick Start

```bash
uv run main.py
```

The agent will start on `http://localhost:8000`. Use the `/chats` endpoint to obtain a websocket url that you can connect to to talk to your agent.

### Environment Variables

Required:
- `GEMINI_API_KEY`: Your Google Gemini API key

Optional:
- `PORT`: Server port (default: 8000)

## Leads Dashboard (Calls, Transcripts, and Audio)

We provide a simple dashboard to review calls for a specific agent, play call audio, read transcripts, and accept leads.

### Configure

Set the following environment variables:

- `CARTESIA_API_KEY` (required)
- `AGENT_ID` (default: `agent_tLP2HN5nF4SMpHBSYMWzZY`)
- `AGENT_PHONE_NUMBER` (default: `+12173874858`) – used for a sanity check
- `DASHBOARD_PORT` (default: `8080`)

### Run

```bash
uv run dashboard_server.py
```

Open `http://localhost:8080` to view calls. The dashboard lists recent calls for the configured agent (with transcripts) and exposes an audio player for each call.