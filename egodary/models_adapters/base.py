"""Model adapter protocol."""

from __future__ import annotations

from typing import Literal, Protocol

from egodary.core.models import PromptBuckets, TagItem

PromptStyle = Literal["tags", "structured_blocks", "natural_language"]


class ModelAdapter(Protocol):
    id: str
    label: str
    prompt_style: PromptStyle
    supports_negative: bool
    supports_cfg: bool

    def assemble_order(self, complexity: str = "standard") -> list[str]: ...

    def format_tag(self, item: TagItem, raw: str | None = None) -> str: ...

    def format_output(self, buckets: PromptBuckets, complexity: str = "standard") -> str: ...

    def negative_prompt(self) -> str | None: ...

    def generation_defaults(self) -> dict: ...
