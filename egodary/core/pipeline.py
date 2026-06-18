"""Prompt assembly pipeline — collect buckets → format output."""

from __future__ import annotations

import logging

from egodary.core.conflicts import apply_state_conflicts, is_couple_pose
from egodary.core.quality_boosters import finalize_quality_bucket
from egodary.core.fetish_skip import should_skip_fetish_item
from egodary.core.models import AssembledPrompt, PromptBuckets, PromptState
from egodary.core.registry import TagRegistry
from egodary.core.runtime_registry import RuntimeRegistry

RegistryLike = TagRegistry | RuntimeRegistry
from egodary.models_adapters.anima import AnimaAdapter
from egodary.models_adapters.illustrious import IllustriousAdapter
from egodary.models_adapters.zimage_turbo import ZImageTurboAdapter

logger = logging.getLogger(__name__)


def _dedupe_tags_preserve_order(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        key = tag.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(tag)
    return out


ADAPTERS = {
    "illustrious": IllustriousAdapter(),
    "anima": AnimaAdapter(),
    "zimage_turbo": ZImageTurboAdapter(),
}


class PromptEngine:
    def __init__(self, registry: RegistryLike) -> None:
        self.registry = registry

    def get_adapter(self, model_id: str):
        adapter = ADAPTERS.get(model_id)
        if adapter is None:
            logger.warning("Unknown model %s, falling back to illustrious", model_id)
            return ADAPTERS["illustrious"]
        return adapter

    def assemble(self, state: PromptState, complexity: str = "standard") -> AssembledPrompt:
        adapter = self.get_adapter(state.model_id)
        state, _ = apply_state_conflicts(state)
        buckets = self._collect_buckets(state)
        buckets = self._apply_quality(buckets, state, adapter.id)
        positive = adapter.format_output(buckets, complexity)
        negative = adapter.negative_prompt() if adapter.supports_negative else None
        return AssembledPrompt(
            positive=positive,
            negative=negative,
            buckets=buckets,
            model_id=adapter.id,
        )

    def _collect_buckets(self, state: PromptState) -> PromptBuckets:
        style_quality, style_tags = self._collect_style_buckets(state)
        hair_tags, makeup_tags, appearance_tags = self._collect_appearance_buckets(state)
        return PromptBuckets(
            subject=self._collect_subject_bucket(state),
            character=self._collect_character_bucket(state),
            face=self._collect_face_bucket(state),
            hair=hair_tags,
            makeup=makeup_tags,
            appearance=appearance_tags,
            outfit=self._collect_outfit_bucket(state),
            scene=self._collect_scene_bucket(state),
            situation=self._collect_situation_bucket(state),
            pose=self._collect_pose_bucket(state),
            camera=self._collect_camera_bucket(state),
            lighting=self._collect_lighting_bucket(state),
            atmosphere=[],
            fetish=self._collect_fetish_bucket(state),
            quality=style_quality,
            extra=[],
            style=style_tags,
        )

    def _collect_style_buckets(self, state: PromptState) -> tuple[list[str], list[str]]:
        style = state.style
        if not style.enabled:
            return [], []

        quality: list[str] = []
        style_tags: list[str] = []
        if style.art_style:
            resolved = self._resolve_selection(style.art_style, "style.art_style", state.model_id)
            if resolved:
                style_tags.extend(self._split_tags(resolved))
        if style.artist_style:
            resolved = self._resolve_selection(style.artist_style, "style.artist_style", state.model_id)
            if resolved:
                style_tags.extend(self._split_tags(resolved))
        for item_id in style.quality:
            resolved = self._resolve_selection(item_id, "style.quality", state.model_id)
            if resolved:
                quality.extend(self._split_tags(resolved))
        for item_id in style.aesthetic:
            resolved = self._resolve_selection(item_id, "style.aesthetic", state.model_id)
            if resolved:
                style_tags.extend(self._split_tags(resolved))
        for item_id in style.technique:
            resolved = self._resolve_selection(item_id, "style.technique", state.model_id)
            if resolved:
                style_tags.extend(self._split_tags(resolved))
        return quality, style_tags

    def _collect_subject_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        tags.append("1girl")
        if state.pose and is_couple_pose(state.pose) and state.group_mode:
            tags.append("2girls")
            tags.append("couple")
        else:
            tags.append("solo")
            if state.group_mode and state.characters.secondary:
                tags.append("2girls")
                if state.characters.auto_contrast:
                    tags.append("visual contrast between characters")
                tags.append("group composition")
        return _dedupe_tags_preserve_order(tags)

    def _collect_character_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        ch = state.character
        char_single_fields = [
            ("age_appearance", "character.age_appearance"),
            ("body_type", "character.body_type"),
            ("breast_size", "character.breast_size"),
            ("breast_shape", "character.breast_shape"),
            ("waist", "character.waist"),
            ("hips_ass", "character.hips_ass"),
            ("legs", "character.legs"),
            ("overall_figure", "character.overall_figure"),
            ("height_build", "character.height_build"),
            ("ethnicity", "character.ethnicity"),
            ("skin_tone", "character.skin_tone"),
        ]
        for field_name, category_id in char_single_fields:
            value = getattr(ch, field_name)
            if value:
                resolved = self._resolve_selection(value, category_id, state.model_id)
                if resolved:
                    tags.extend(self._split_tags(resolved))
        for item_id in ch.body_details:
            resolved = self._resolve_selection(item_id, "character.body_details", state.model_id)
            if resolved:
                tags.extend(self._split_tags(resolved))
        return _dedupe_tags_preserve_order([t for t in tags if t])

    def _collect_appearance_buckets(self, state: PromptState) -> tuple[list[str], list[str], list[str]]:
        hair_tags: list[str] = []
        makeup_tags: list[str] = []
        appearance_tags: list[str] = []
        if state.appearance.hair:
            resolved = self._resolve_selection(state.appearance.hair, "appearance.hair", state.model_id)
            if resolved:
                parts = self._split_tags(resolved)
                hair_tags.extend(parts)
                appearance_tags.extend(parts)
        if state.appearance.hair_color:
            resolved = self._resolve_selection(
                state.appearance.hair_color, "appearance.hair_color", state.model_id
            )
            if resolved:
                parts = self._split_tags(resolved)
                hair_tags.extend(parts)
                appearance_tags.extend(parts)
        for makeup_id in state.appearance.makeup:
            resolved = self._resolve_selection(makeup_id, "appearance.makeup", state.model_id)
            if resolved:
                parts = self._split_tags(resolved)
                makeup_tags.extend(parts)
                appearance_tags.extend(parts)
        for accessory_id in state.appearance.accessories:
            resolved = self._resolve_selection(accessory_id, "appearance.accessories", state.model_id)
            if resolved:
                parts = self._split_tags(resolved)
                hair_tags.extend(parts)
                appearance_tags.extend(parts)
        return (
            _dedupe_tags_preserve_order([t for t in hair_tags if t]),
            _dedupe_tags_preserve_order([t for t in makeup_tags if t]),
            _dedupe_tags_preserve_order([t for t in appearance_tags if t]),
        )

    def _collect_face_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        face_fields = [
            ("facial_expression", "face.facial_expression"),
            ("mouth_lips", "face.mouth_lips"),
            ("eyes", "face.eyes"),
            ("eye_color", "face.eye_color"),
            ("skin", "face.skin"),
            ("face_shape", "face.face_shape"),
            ("eyebrows", "face.eyebrows"),
            ("nose", "face.nose"),
            ("jaw_chin", "face.jaw_chin"),
            ("age_maturity", "face.age_maturity"),
            ("beauty_archetype", "face.beauty_archetype"),
            ("facial_details", "face.facial_details"),
        ]
        for field_name, category_id in face_fields:
            value = getattr(state.face, field_name)
            if value:
                resolved = self._resolve_selection(value, category_id, state.model_id)
                if resolved:
                    tags.extend(self._split_tags(resolved))
        return _dedupe_tags_preserve_order([t for t in tags if t])

    def _collect_outfit_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        outfit = state.outfit
        field_categories = [
            ("dress", "outfit.dress"),
            ("top", "outfit.top"),
            ("bottom", "outfit.bottom"),
            ("underwear_layer", "outfit.underwear_layer"),
            ("legwear", "outfit.legwear"),
            ("jacket", "outfit.jacket"),
            ("footwear", "outfit.footwear"),
            ("gloves", "outfit.gloves"),
            ("cape", "outfit.cape"),
        ]
        for field_name, category_suffix in field_categories:
            value = getattr(outfit, field_name)
            if value:
                resolved = self._resolve_selection(value, category_suffix, state.model_id)
                if resolved:
                    tags.extend(self._split_tags(resolved))
            condition_id = (outfit.conditions or {}).get(field_name, "")
            if condition_id:
                resolved = self._resolve_selection(
                    condition_id, "outfit.clothing_condition", state.model_id
                )
                if resolved:
                    tags.extend(self._split_tags(resolved))
        return tags

    def _collect_scene_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        scene = state.scene
        mapping = [
            (scene.time, "scene.time"),
            (scene.weather, "scene.weather"),
            (scene.season, "scene.season"),
        ]
        for value, category in mapping:
            if value:
                resolved = self._resolve_selection(value, category, state.model_id)
                if resolved:
                    tags.extend(self._split_tags(resolved))
        if scene.location:
            loc = self._resolve_selection(scene.location, "scene.location", state.model_id)
            if loc:
                tags.extend(self._split_tags(loc))
        env = state.environment
        if env.location:
            resolved = self._resolve_selection(env.location, "environment.location", state.model_id)
            if resolved:
                tags.extend(self._split_tags(resolved))
        for modifier_id in env.modifiers:
            resolved = self._resolve_selection(modifier_id, "environment.modifiers", state.model_id)
            if resolved:
                tags.extend(self._split_tags(resolved))
        return tags

    def _collect_situation_bucket(self, state: PromptState) -> list[str]:
        env = state.environment
        if not env.situation:
            return []
        resolved = self._resolve_selection(env.situation, "environment.situation", state.model_id)
        if not resolved:
            return []
        return self._split_tags(resolved)

    def _collect_pose_bucket(self, state: PromptState) -> list[str]:
        if not state.pose:
            return []
        for category_id in ("pose.solo", "pose.couple"):
            resolved = self._resolve_selection(state.pose, category_id, state.model_id)
            if resolved:
                return self._split_tags(resolved)
        return [state.pose]

    def _collect_camera_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        cam = state.camera
        mapping = [
            (cam.angle, "camera.angle"),
            (cam.framing, "camera.framing"),
            (cam.lens, "camera.lens"),
            (cam.focus, "camera.focus"),
            (cam.composition, "camera.composition"),
            (cam.nsfw_shot, "camera.nsfw_shot"),
        ]
        for value, category in mapping:
            if value:
                resolved = self._resolve_selection(value, category, state.model_id)
                if resolved:
                    tags.extend(self._split_tags(resolved))
        return tags

    def _collect_lighting_bucket(self, state: PromptState) -> list[str]:
        tags: list[str] = []
        light = state.lighting
        mapping = [
            (light.light_type, "lighting.light_type"),
            (light.direction, "lighting.direction"),
            (light.quality, "lighting.quality"),
            (light.color_mood, "lighting.color_mood"),
            (light.nsfw, "lighting.nsfw"),
        ]
        for value, category in mapping:
            if value:
                resolved = self._resolve_selection(value, category, state.model_id)
                if resolved:
                    tags.extend(self._split_tags(resolved))
        return tags

    def _collect_fetish_bucket(self, state: PromptState) -> list[str]:
        if not state.fetish.elements:
            return []
        tags: list[str] = []
        for item_id in state.fetish.elements:
            if should_skip_fetish_item(state, item_id):
                continue
            resolved = self._resolve_selection(item_id, "fetish.elements", state.model_id)
            if not resolved:
                continue
            tags.extend(self._split_tags(resolved))
        return tags

    def _resolve_selection(self, item_id: str, category_id: str, model_id: str) -> str | None:
        if not item_id:
            return None
        tag = self.registry.resolve_tag(category_id, item_id, model_id)
        if tag:
            return tag
        if ":" in item_id:
            cat, iid = item_id.split(":", 1)
            tag = self.registry.resolve_tag(cat, iid, model_id)
            if tag:
                return tag
        category = self.registry.get_category(category_id)
        if category:
            normalized = item_id.lower().replace("-", "_")
            for item in category.items:
                if item.id.lower() == normalized:
                    return self.registry.resolve_tag(category_id, item.id, model_id)
        logger.debug("Unresolved selection %s in %s for %s", item_id, category_id, model_id)
        return None

    @staticmethod
    def _split_tags(text: str) -> list[str]:
        return [part.strip() for part in text.split(",") if part.strip()]

    @staticmethod
    def _apply_quality(buckets: PromptBuckets, state: PromptState, model_id: str) -> PromptBuckets:
        buckets.quality = finalize_quality_bucket(buckets.quality, state.style, model_id)
        return buckets
