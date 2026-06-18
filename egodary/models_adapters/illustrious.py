"""Illustrious / danbooru-style tag formatter."""

from __future__ import annotations

from egodary.core.models import PromptBuckets
from egodary.core.rules_loader import get_model_gen_rules
from egodary.models_adapters.prompt_format import (
    DEFAULT_ILLUSTRIOUS_BUCKET_ORDER,
    format_buckets_as_tag_string,
)

GLOBAL_NEGATIVE_PROMPT = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, blurry"
)


class IllustriousAdapter:
    id = "illustrious"
    label = "Illustrious"
    prompt_style = "tags"
    supports_negative = True
    supports_cfg = True

    def assemble_order(self, complexity: str = "standard") -> list[str]:
        _ = complexity
        rules = get_model_gen_rules(self.id)
        order = (rules.format or {}).get("bucket_order")
        if order:
            return list(order)
        return list(DEFAULT_ILLUSTRIOUS_BUCKET_ORDER)

    def format_tag(self, item, raw: str | None = None) -> str:
        if raw:
            return raw
        return item.tags.get(self.id, "")

    def format_output(self, buckets: PromptBuckets, complexity: str = "standard") -> str:
        rules = get_model_gen_rules(self.id)
        fmt = rules.format or {}
        suffix = fmt.get("technical_suffix") or []
        suffix_tags = [str(t) for t in suffix if str(t).strip()] if isinstance(suffix, list) else []
        return format_buckets_as_tag_string(
            buckets,
            bucket_order=self.assemble_order(complexity),
            separator=str(fmt.get("separator") or ", "),
            dedupe_tags=bool(fmt.get("dedupe_tags", True)),
            tag_case=fmt.get("tag_case"),
            suffix_tags=suffix_tags,
        )

    def negative_prompt(self) -> str | None:
        return GLOBAL_NEGATIVE_PROMPT

    def generation_defaults(self) -> dict:
        rules = get_model_gen_rules(self.id)
        gen = (rules.format or {}).get("generation_defaults")
        if isinstance(gen, dict) and gen:
            sampler = str(gen.get("sampler") or "euler_a")
            if sampler == "euler_a":
                sampler = "Euler a"
            return {
                "sampler": sampler,
                "schedule": "Karras",
                "steps": int(gen.get("steps", 28)),
                "cfg": float(gen.get("cfg_scale", gen.get("cfg", 7.0))),
                "width": 832,
                "height": 1216,
            }
        return {
            "sampler": "Euler a",
            "schedule": "Karras",
            "steps": 28,
            "cfg": 7.0,
            "width": 832,
            "height": 1216,
        }
