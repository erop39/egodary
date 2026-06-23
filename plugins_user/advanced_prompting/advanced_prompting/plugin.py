"""Advanced Prompting — ui_extension плагин для eGOdary.

Добавляет:
  POST /api/advanced-prompting/rebuild  — пересборка positive из
      отредактированных/переупорядоченных buckets.
  GET  /api/advanced-prompting/info     — мета-информация о плагине.

UI-часть живёт в static/advanced_prompting.js и подключается через
<script> тег, который плагин инжектирует в index.html через middleware.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import pathlib

_STATIC_DIR = pathlib.Path(__file__).resolve().parent.parent / "static"

router = APIRouter(prefix="/api/advanced-prompting", tags=["advanced-prompting"])


# ---------------------------------------------------------------------------
# Схемы запроса
# ---------------------------------------------------------------------------

class BucketBlock(BaseModel):
    name: str
    tags: list[str]


class RebuildRequest(BaseModel):
    blocks: list[BucketBlock]
    model_id: str = "illustrious"


class RebuildResponse(BaseModel):
    positive: str
    blocks: list[BucketBlock]


# ---------------------------------------------------------------------------
# Порядок бакетов по умолчанию (совпадает с PromptBuckets в models.py)
# ---------------------------------------------------------------------------

BUCKET_ORDER = [
    "quality", "subject", "character", "face", "hair",
    "makeup", "appearance", "outfit", "tattoos", "pose",
    "situation", "scene", "lighting", "atmosphere",
    "camera", "fetish", "extra", "style",
]

BUCKET_LABELS: dict[str, str] = {
    "quality":     "Quality",
    "subject":     "Subject",
    "character":   "Character",
    "face":        "Face",
    "hair":        "Hair",
    "makeup":      "Makeup",
    "appearance":  "Appearance",
    "outfit":      "Outfit",
    "tattoos":     "Tattoos",
    "pose":        "Pose",
    "situation":   "Situation",
    "scene":       "Scene",
    "lighting":    "Lighting",
    "atmosphere":  "Atmosphere",
    "camera":      "Camera",
    "fetish":      "Fetish",
    "extra":       "Extra",
    "style":       "Style",
}


# ---------------------------------------------------------------------------
# Роуты
# ---------------------------------------------------------------------------

@router.get("/info")
def info() -> dict[str, Any]:
    return {
        "id": "advanced_prompting",
        "version": "0.1.0",
        "bucket_order": BUCKET_ORDER,
        "bucket_labels": BUCKET_LABELS,
    }


@router.post("/rebuild", response_model=RebuildResponse)
def rebuild(req: RebuildRequest) -> RebuildResponse:
    """Принимает список блоков в произвольном порядке,
    собирает positive строку простой конкатенацией через запятую.

    Для Illustrious это полностью корректно.
    Для Anima/ZIT — результат может отличаться от pipeline-сборки,
    но это ожидаемо: пользователь явно управляет порядком.
    """
    parts: list[str] = []
    for block in req.blocks:
        for tag in block.tags:
            t = tag.strip()
            if t:
                parts.append(t)

    positive = ", ".join(parts)
    return RebuildResponse(positive=positive, blocks=req.blocks)


@router.post("/from-generate")
def from_generate(buckets: dict[str, list[str]]) -> dict[str, Any]:
    """Принимает dict buckets из /api/generate и возвращает
    список блоков в стандартном порядке для редактора.
    """
    blocks: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Сначала в стандартном порядке
    for name in BUCKET_ORDER:
        tags = buckets.get(name, [])
        if tags:
            blocks.append({
                "name": name,
                "label": BUCKET_LABELS.get(name, name.title()),
                "tags": tags,
            })
        seen.add(name)

    # Потом любые нестандартные
    for name, tags in buckets.items():
        if name not in seen and tags:
            blocks.append({
                "name": name,
                "label": name.title(),
                "tags": tags,
            })

    return {"blocks": blocks}


# ---------------------------------------------------------------------------
# Протокол UiExtensionPlugin
# ---------------------------------------------------------------------------

class _AdvancedPromptingPlugin:
    id = "advanced_prompting"

    def register(self, app: FastAPI) -> None:
        app.include_router(router)

        # Раздаём статику плагина
        if _STATIC_DIR.is_dir():
            app.mount(
                "/static/plugins/advanced_prompting",
                StaticFiles(directory=str(_STATIC_DIR)),
                name="advanced_prompting_static",
            )

        # Middleware: инжектируем <script> тег в index.html
        from starlette.middleware.base import BaseHTTPMiddleware

        class InjectScriptMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                response = await call_next(request)
                if (
                    request.url.path in ("/", "/index.html")
                    and response.status_code == 200
                    and "text/html" in response.headers.get("content-type", "")
                ):
                    body = b""
                    async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                        body += chunk
                    inject = b'<script src="/static/plugins/advanced_prompting/advanced_prompting.js" defer></script>'
                    body = body.replace(b"</body>", inject + b"\n</body>")
                    headers = dict(response.headers)
                    # The injected <script> tag changes the body length, so the
                    # Content-Length copied from the original response is now
                    # stale (too small). Drop it (and content-encoding, in case
                    # the original body was compressed) so Starlette recomputes
                    # a correct Content-Length from the new body below —
                    # otherwise uvicorn raises "Response content longer than
                    # Content-Length" and the request fails outright.
                    headers.pop("content-length", None)
                    headers.pop("content-encoding", None)
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=headers,
                        media_type=response.media_type,
                    )
                return response

        app.add_middleware(InjectScriptMiddleware)


plugin = _AdvancedPromptingPlugin()
