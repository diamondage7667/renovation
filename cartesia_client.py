from typing import Any, Dict, Optional

import httpx

from config import CARTESIA_API_KEY


API_BASE_URL = "https://api.cartesia.ai"
API_VERSION = "2025-04-16"


class CartesiaClient:
    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = (api_key or CARTESIA_API_KEY).strip()
        if not self.api_key:
            raise RuntimeError("CARTESIA_API_KEY is required to query Cartesia APIs")

        self._client = httpx.AsyncClient(
            base_url=API_BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Cartesia-Version": API_VERSION,
            },
            timeout=httpx.Timeout(20.0, read=60.0),
        )

    async def list_calls(self, agent_id: str, expand_transcript: bool = True, limit: int = 25) -> Dict[str, Any]:
        params: Dict[str, Any] = {"agent_id": agent_id, "limit": limit}
        if expand_transcript:
            params["expand"] = "transcript"
        resp = await self._client.get("/agents/calls", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_call(self, call_id: str) -> Dict[str, Any]:
        resp = await self._client.get(f"/agents/calls/{call_id}")
        resp.raise_for_status()
        return resp.json()

    async def stream_call_audio(self, call_id: str) -> httpx.Response:
        # Caller is responsible for streaming bytes to client
        resp = await self._client.get(f"/agents/calls/{call_id}/audio")
        resp.raise_for_status()
        return resp

    async def aclose(self) -> None:
        await self._client.aclose()


