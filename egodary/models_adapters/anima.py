"""Anima model adapter — structured 14-block formatter with sanitization."""

from __future__ import annotations

import re

from egodary.core.models import PromptBuckets
from egodary.core.rules_loader import get_model_gen_rules
from egodary.models_adapters.illustrious import GLOBAL_NEGATIVE_PROMPT

ANIMA_FORBIDDEN_RE = re.compile(
    r"\b("
    r"photo(?:graphy|realistic)?|"
    r"photoreal(?:istic|ism)?|"
    r"dslr|film\s*grain|"
    r"depth of field|bokeh|"
    r"8k|uhd|raw photo"
    r")\b",
    re.IGNORECASE,
)

# Repeated tail phrases baked into content-pack anima tags.
ANIMA_BOILERPLATE = (
    "cinematic lighting",
    "cinematic framing",
    "detailed face",
    "styled outfit",
    "styled accessory",
    "face makeup",
    "detailed hairstyle",
    "dynamic pose",
    "clothing detail",
)

MAKEUP_MARKERS = (
    "blush",
    "gloss",
    "dewy",
    "lipstick",
    "eyeliner",
    "makeup",
    "eyeshadow",
    "mascara",
)

SUBJECT_MARKERS = (
    "1girl",
    "2girls",
    "solo",
    "couple",
    "group composition",
    "visual contrast between characters",
    "years old",
)

BODY_MARKERS = (" body",)

HAIR_MAKEUP_MARKERS = (
    "hair",
    "makeup",
    "hairstyle",
    "slicked",
    "braid",
    "ponytail",
    "bun",
    "bangs",
    "curls",
    "waves",
    "pixie",
    "bob",
)

FACE_MARKERS = (
    "eyes",
    "smirk",
    "lips",
    "skin",
    "jaw",
    "chin",
    "nose",
    "brow",
    "face",
    "tan",
    "beauty",
    "saliva",
    "tongue",
    "expression",
    "ahegao",
    "pleasure",
    "drunk",
    "lust",
    "moaning",
    "blushing",
    "seductive",
    "teasing",
)

ACCESSORY_MARKERS = (
    "choker",
    "collar",
    "necklace",
    "earring",
    "harness",
    "chain",
    "belt",
    "bag",
    "backpack",
    "hat",
    "headpiece",
)


class AnimaAdapter:
    id = "anima"
    label = "Anima"
    prompt_style = "structured_blocks"
    supports_negative = True
    supports_cfg = True

    def _rules(self):
        return get_model_gen_rules(self.id)

    def _format(self) -> dict:
        return self._rules().format or {}

    def _boilerplate(self) -> tuple[str, ...]:
        items = self._format().get("strip_boilerplate")
        if isinstance(items, list) and items:
            return tuple(str(item) for item in items)
        return ANIMA_BOILERPLATE

    def _forbidden_re(self) -> re.Pattern[str]:
        patterns = self._format().get("forbidden_patterns")
        if isinstance(patterns, list) and patterns:
            body = "|".join(re.escape(str(pattern)) for pattern in patterns)
            return re.compile(rf"\b({body})\b", re.IGNORECASE)
        return ANIMA_FORBIDDEN_RE

    def assemble_order(self, complexity: str = "standard") -> list[str]:
        _ = complexity
        order = self._format().get("bucket_order")
        if order:
            return list(order)
        return [
            "quality",
            "character",
            "outfit",
            "pose",
            "camera",
            "scene",
            "lighting",
            "atmosphere",
            "extra",
            "fetish",
        ]

    def format_tag(self, item, raw: str | None = None) -> str:
        if raw:
            return raw
        return item.tags.get(self.id, item.tags.get("illustrious", ""))

    def format_output(self, buckets: PromptBuckets, complexity: str = "standard") -> str:
        _ = complexity
        bucket_map = buckets.model_dump()
        blocks = self._build_14_blocks(bucket_map)
        cleaned = [self._sanitize_block(block) for block in blocks if block.strip()]
        return "\n\n".join(cleaned)

    def _build_14_blocks(self, bucket_map: dict) -> list[str]:
        subject = self._clean_tags(bucket_map.get("subject", []))
        body = self._clean_tags(bucket_map.get("character", []))
        face = self._clean_tags(bucket_map.get("face", []))
        hair = self._clean_tags(bucket_map.get("appearance", []))
        outfit = self._clean_tags(bucket_map.get("outfit", []))
        pose = self._clean_tags(
            list(bucket_map.get("pose", [])) + list(bucket_map.get("situation", []))
        )
        camera = self._resolve_camera(self._clean_tags(bucket_map.get("camera", [])))
        scene = self._clean_tags(bucket_map.get("scene", []))
        lighting = self._resolve_lighting(self._clean_tags(bucket_map.get("lighting", [])))
        atmosphere = self._clean_tags(bucket_map.get("atmosphere", []))
        style_extra = self._clean_tags(
            list(bucket_map.get("extra", [])) + list(bucket_map.get("style", []))
        )
        fetish = self._clean_tags(bucket_map.get("fetish", []))
        quality_extra = self._clean_tags(bucket_map.get("quality", []))
        quality_parts = list(quality_extra)
        quality = self._join(quality_parts)
        if face:
            face.append("detailed face")

        return [
            quality,
            self._join(style_extra, "anime style"),
            self._join(subject, "1girl, solo"),
            self._join(body, "athletic body"),
            self._join(face),
            self._join(hair, "detailed hair"),
            self._join(outfit, "cohesive outfit design"),
            self._join(pose, "natural pose"),
            self._join(camera, "upper body, portrait framing"),
            self._join(scene, "stylized environment"),
            self._join(lighting, "soft natural lighting"),
            self._join(atmosphere, "clean atmospheric depth"),
            self._join(fetish),
            "clean anatomy, coherent composition",
        ]

    def _partition_character(self, tags: list[str]) -> tuple[list[str], list[str], list[str]]:
        subject: list[str] = []
        body: list[str] = []
        hair_misc: list[str] = []
        for tag in self._clean_tags(tags):
            low = tag.lower()
            if any(marker in low for marker in SUBJECT_MARKERS):
                subject.append(tag)
            elif any(marker in low for marker in BODY_MARKERS):
                body.append(tag)
            elif any(marker in low for marker in HAIR_MAKEUP_MARKERS) or any(
                marker in low for marker in MAKEUP_MARKERS
            ):
                hair_misc.append(tag)
            elif any(marker in low for marker in ACCESSORY_MARKERS):
                hair_misc.append(tag)
            else:
                subject.append(tag)
        return subject, body, hair_misc

    def _resolve_lighting(self, tags: list[str]) -> list[str]:
        if not tags:
            return []
        normalized = [self._normalize_lighting_tag(tag) for tag in tags]
        primary = normalized[0]
        accent = ""
        for candidate in normalized[1:]:
            if self._lighting_overlap(primary, candidate):
                continue
            accent = candidate
            break
        if accent:
            return [primary, accent]
        return [primary]

    @staticmethod
    def _normalize_lighting_tag(tag: str) -> str:
        cleaned = re.sub(r"\bcinematic\s+lighting\b", "lighting", tag, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
        return cleaned or tag

    @staticmethod
    def _lighting_overlap(left: str, right: str) -> bool:
        left_tokens = set(re.findall(r"[a-z]+", left.lower()))
        right_tokens = set(re.findall(r"[a-z]+", right.lower()))
        shared = left_tokens & right_tokens
        lighting_words = {
            "light",
            "lighting",
            "lit",
            "glow",
            "shadow",
            "rim",
            "back",
            "side",
            "dramatic",
            "cinematic",
            "warm",
            "golden",
            "soft",
            "natural",
        }
        return len(shared & lighting_words) >= 2

    def _resolve_camera(self, tags: list[str]) -> list[str]:
        if not tags:
            return []
        joined = " ".join(tags).lower()
        has_full_body = "full body" in joined
        has_submission_angle = "submission" in joined or (
            "high angle" in joined and "portrait" not in joined and "upper body" not in joined
        )
        if has_full_body and has_submission_angle:
            tags = [tag for tag in tags if "full body" not in tag.lower()]
        if len(tags) > 3:
            tags = tags[:3]
        return tags

    def _clean_tags(self, tags: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in tags:
            for part in self._split_parts(raw):
                normalized = self._strip_boilerplate(part)
                if not normalized:
                    continue
                key = normalized.lower()
                if key in seen:
                    continue
                seen.add(key)
                cleaned.append(normalized)
        return cleaned

    @staticmethod
    def _split_parts(text: str) -> list[str]:
        return [part.strip() for part in text.split(",") if part.strip()]

    def _strip_boilerplate(self, tag: str) -> str:
        result = tag.strip(" ,")
        for phrase in self._boilerplate():
            result = re.sub(rf",\s*{re.escape(phrase)}\s*", "", result, flags=re.IGNORECASE)
            result = re.sub(rf"^{re.escape(phrase)}\s*,\s*", "", result, flags=re.IGNORECASE)
            if result.lower() == phrase:
                return ""
        return result.strip(" ,")

    @staticmethod
    def _join(tags: list[str], default: str = "") -> str:
        unique: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(tag)
        if unique:
            return ", ".join(unique)
        return default

    def _sanitize_block(self, block: str) -> str:
        cleaned = self._forbidden_re().sub("", block)
        cleaned = re.sub(r"\s+,", ",", cleaned)
        cleaned = re.sub(r",\s*,", ", ", cleaned)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return cleaned.strip(" ,") or "anime style"

    def negative_prompt(self) -> str | None:
        template = (self._rules().negative or {}).get("template")
        if isinstance(template, str) and template.strip():
            return f"{template.strip()}, worst quality, low quality, score_1, score_2, score_3, artist name"
        return (
            f"{GLOBAL_NEGATIVE_PROMPT}, worst quality, low quality, score_1, score_2, score_3, artist name"
        )

    def generation_defaults(self) -> dict:
        gen = self._rules().generation_defaults or {}
        if isinstance(gen, dict) and gen:
            sampler = str(gen.get("sampler") or "euler_a")
            if sampler == "euler_a":
                sampler = "Euler a"
            return {
                "sampler": sampler,
                "schedule": str(gen.get("schedule") or "Beta"),
                "steps": int(gen.get("steps", 32)),
                "cfg": float(gen.get("cfg_scale", gen.get("cfg", 5.2))),
                "width": int(gen.get("width", 832)),
                "height": int(gen.get("height", 1216)),
            }
        return {
            "sampler": "Euler a",
            "schedule": "Beta",
            "steps": 32,
            "cfg": 5.2,
            "width": 832,
            "height": 1216,
        }
