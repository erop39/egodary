"""Runtime LLM settings and cached health status."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class LlmHealthReport(BaseModel):
    ok: bool = False
    reachable: bool = False
    model_listed: bool = False
    json_probe_ok: bool = False
    latency_ms: int | None = None
    error: str | None = None
    models_available: list[str] = Field(default_factory=list)


class LlmSettings(BaseModel):
    enabled: bool = False
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3"
    temperature: float = 0.3
    top_p: float = 0.9
    timeout: float = 30.0
    max_retries: int = 1
    health_ttl_seconds: int = 45
    last_health: LlmHealthReport | None = None
    last_health_at: datetime | None = None

    def to_api_dict(self) -> dict:
        payload = self.model_dump()
        if self.last_health_at is not None:
            payload["last_health_at"] = self.last_health_at.isoformat()
        return payload

