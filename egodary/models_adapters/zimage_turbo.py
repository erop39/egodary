"""Z-Image Turbo adapter — natural language narrative prompt."""

from __future__ import annotations

from egodary.core.models import PromptBuckets
from egodary.core.rules_loader import get_model_gen_rules
from egodary.core.zit_lexicon import (
    extract_subject_count_tags,
    is_subject_count,
    subject_opener_from_count_tags,
    transform_token_for_prose,
)


class ZImageTurboAdapter:
    id = "zimage_turbo"
    label = "Z-Image Turbo"
    prompt_style = "natural_language"
    supports_negative = False
    supports_cfg = False

    def _rules(self):
        return get_model_gen_rules(self.id)

    def _format(self) -> dict:
        return self._rules().format or {}

    def assemble_order(self, complexity: str = "standard") -> list[str]:
        _ = complexity
        order = self._format().get("bucket_order")
        if order:
            return list(order)
        return [
            "subject",
            "character",
            "face",
            "appearance",
            "pose",
            "situation",
            "outfit",
            "scene",
            "lighting",
            "atmosphere",
            "camera",
            "extra",
            "fetish",
        ]

    def format_tag(self, item, raw: str | None = None) -> str:
        if raw:
            return raw
        return item.tags.get(self.id, item.tags.get("anima", item.tags.get("illustrious", "")))

    def format_output(self, buckets: PromptBuckets, complexity: str = "standard") -> str:
        _ = complexity
        data = buckets.model_dump()
        templates = self._format().get("sentence_templates") or {}

        subject = list(data.get("subject", []))
        count_tags = extract_subject_count_tags(subject)
        opener = subject_opener_from_count_tags(count_tags)
        subject_extra = [tag for tag in subject if not is_subject_count(tag)]

        character_prose = self._prose_tags(
            subject_extra
            + list(data.get("character", []))
            + list(data.get("face", []))
            + list(data.get("hair", []))
            + list(data.get("makeup", []))
            + list(data.get("appearance", []))
        )
        character = opener
        if character_prose:
            character = f"{opener} with {', '.join(character_prose)}"

        pose = self._prose_phrase(
            list(data.get("pose", [])) + list(data.get("situation", [])),
            "stands naturally",
        )
        outfit_items = self._prose_tags(list(data.get("outfit", [])))
        outfit = f"wears {', '.join(outfit_items)}" if outfit_items else "wears a cohesive outfit"
        scene = self._prose_phrase(list(data.get("scene", [])), "in a detailed environment")
        lighting = self._prose_phrase(list(data.get("lighting", [])), "with cinematic lighting")
        atmosphere = self._prose_phrase(list(data.get("atmosphere", [])), "and atmospheric depth")
        camera = self._camera_phrase(list(data.get("camera", [])))
        extra_tags = (
            list(data.get("quality", []))
            + list(data.get("style", []))
            + list(data.get("extra", []))
        )
        extra = self._prose_phrase(extra_tags, "")
        fetish = self._prose_phrase(list(data.get("fetish", [])), "")

        sentences = [
            templates.get("main", "{character} {pose} and {outfit}.").format(
                character=character, pose=pose, outfit=outfit
            ),
            templates.get("scene", "The scene is {scene}, {lighting}, {atmosphere}.").format(
                scene=scene, lighting=lighting, atmosphere=atmosphere
            ),
            templates.get("camera", "The image is {camera}.").format(camera=camera),
            templates.get(
                "quality_hint",
                "Keep style coherent, avoid contradictory aesthetics, and prioritize clear anatomy.",
            ),
        ]
        if extra:
            sentences.append(f"Additional direction: {extra}.")
        if fetish:
            sentences.append(f"Sensual intent: {fetish}.")
        return " ".join(s.strip() for s in sentences if s.strip())

    def negative_prompt(self) -> str | None:
        return None

    def generation_defaults(self) -> dict:
        gen = self._rules().generation_defaults or {}
        if isinstance(gen, dict) and gen:
            sampler = str(gen.get("sampler") or "Euler")
            return {
                "sampler": sampler,
                "schedule": str(gen.get("schedule") or "Automatic"),
                "steps": int(gen.get("steps", 10)),
                "cfg": float(gen.get("guidance", gen.get("cfg", 0.0))),
                "width": int(gen.get("width", 1024)),
                "height": int(gen.get("height", 1024)),
            }
        return {
            "sampler": "Euler",
            "schedule": "Automatic",
            "steps": 10,
            "cfg": 0.0,
            "width": 1024,
            "height": 1024,
        }

    @staticmethod
    def _prose_tags(tags: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for tag in tags:
            phrase = transform_token_for_prose(tag)
            if not phrase:
                continue
            key = phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(phrase)
        return out

    @classmethod
    def _prose_phrase(cls, tags: list[str], fallback: str) -> str:
        prose = cls._prose_tags(tags)
        if not prose:
            return fallback
        return ", ".join(prose)

    @classmethod
    def _camera_phrase(cls, tags: list[str]) -> str:
        prose = cls._prose_phrase(tags, "framed in a balanced composition")
        if prose.lower().startswith("with "):
            return prose[5:]
        return prose
