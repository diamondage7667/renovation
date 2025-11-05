# Renovation Dashboard

A real-time dashboard for monitoring and managing voice calls using the Cartesia Line SDK.

## Features

- Real-time call monitoring
- Live call transcripts
- Call history
- Responsive web interface
- WebSocket updates

## Prerequisites

- Python 3.8+
- Cartesia API key
- Ports 8000 and 8001 available

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root with the following variables:

```
CARTESIA_API_KEY=your_api_key_here
```

## Running the Dashboard

1. Start the dashboard server:

```bash
uvicorn dashboard:app --reload --port 8000
```

2. Start the voice agent (in a separate terminal):

```bash
uvicorn dashboard:voice_app.app --reload --port 8001
```

3. Open the dashboard in your browser:
   - Dashboard: http://localhost:8000
   - Voice Agent: http://localhost:8001

## Architecture

The dashboard consists of two main components:

1. **Web Dashboard** (port 8000)
   - Serves the web interface
   - Handles WebSocket connections for real-time updates
   - Displays active calls and call history

2. **Voice Agent** (port 8001)
   - Handles incoming/outgoing calls
   - Processes voice streams
   - Maintains call state

## Environment Variables

- `CARTESIA_API_KEY`: Your Cartesia API key (required)
- `PORT`: Port for the web dashboard (default: 8000)
- `VOICE_PORT`: Port for the voice agent (default: 8001)

## Development

To run in development mode with auto-reload:

```bash
# Terminal 1 - Web Dashboard
uvicorn dashboard:app --reload --port 8000

# Terminal 2 - Voice Agent
uvicorn dashboard:voice_app.app --reload --port 8001
```

## License

MIT
