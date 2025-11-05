import os
from typing import Any, Dict, Optional

import httpx


class CartesiaClient:
    """Minimal Cartesia REST client for calls and agent phone numbers."""

    def __init__(self, api_key: Optional[str] = None, api_version: str = "2025-04-16"):
        self.api_key = api_key or os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            raise RuntimeError("CARTESIA_API_KEY is required")
        self.api_version = os.getenv("CARTESIA_VERSION", api_version)
        self.base_url = os.getenv("CARTESIA_BASE_URL", "https://api.cartesia.ai")
        self._client = httpx.AsyncClient(timeout=30.0)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Cartesia-Version": self.api_version,
        }

    async def list_calls(self, agent_id: str, expand_transcript: bool = True, limit: int = 20) -> Dict[str, Any]:
        params: Dict[str, Any] = {"agent_id": agent_id, "limit": limit}
        if expand_transcript:
            params["expand"] = "transcript"
        resp = await self._client.get(f"{self.base_url}/agents/calls", headers=self._headers(), params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_call(self, call_id: str) -> Dict[str, Any]:
        resp = await self._client.get(f"{self.base_url}/agents/calls/{call_id}", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def stream_call_audio(self, call_id: str) -> httpx.Response:
        # Returns the raw streaming response (WAV)
        resp = await self._client.get(
            f"{self.base_url}/agents/calls/{call_id}/audio",
            headers=self._headers(),
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp

    async def list_agent_phone_numbers(self, agent_id: str) -> Any:
        resp = await self._client.get(
            f"{self.base_url}/agents/{agent_id}/phone-numbers", headers=self._headers()
        )
        resp.raise_for_status()
        return resp.json()

    async def aclose(self) -> None:
        await self._client.aclose()


