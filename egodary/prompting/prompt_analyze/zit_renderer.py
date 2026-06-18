"""Rule-based Z-Image Turbo prose renderer v1.1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from egodary.prompting.prompt_analyze.zit_semantics import ZitSemantics, extract_zit_semantics


@dataclass
class ZitRenderResult:
    text: str
    semantics: ZitSemantics
    paragraphs: list[str]
    used_llm: bool = False
    draft_text: str | None = None


def _join_clauses(parts: list[str], fallback: str = "") -> str:
    clean = [p.strip().rstrip(".,;") for p in parts if p and p.strip()]
    if not clean:
        return fallback
    if len(clean) == 1:
        return clean[0] + "."
    return clean[0].rstrip(".") + ", " + ", ".join(clean[1:]) + "."


def _paragraph_subject_pose_view(sem: ZitSemantics) -> str:
    opener = sem.subject_opener or "A young woman"
    view_bits = [p for p in sem.pose_action_view if any(m in p.lower() for m in ("view", "angle", "shot", "side", "dutch"))]
    action_bits = [p for p in sem.pose_action_view if p not in view_bits]
    parts = [opener]
    if action_bits:
        parts.append(action_bits[0] if len(action_bits) == 1 else ", ".join(action_bits[:2]))
    if view_bits:
        parts.append(f"captured from {view_bits[0]}")
    elif sem.camera_composition_focus:
        cam = sem.camera_composition_focus[0]
        if any(m in cam.lower() for m in ("view", "angle", "shot")):
            parts.append(f"captured from {cam}")
    scene_hint = sem.scene[0] if sem.scene else ""
    if scene_hint and any(m in scene_hint.lower() for m in ("gallery", "room", "interior", "outdoor", "street")):
        loc = scene_hint if scene_hint.lower().startswith("in ") else f"in {scene_hint}"
        return f"{opener} {action_bits[0] if action_bits else 'stands naturally'}, {loc}, {_join_clauses(view_bits, 'seen from a balanced angle').rstrip('.')}.".replace("  ", " ")
    body = f"{opener}"
    if action_bits:
        body += f" {action_bits[0]}"
    if view_bits:
        body += f", captured from {view_bits[0]}"
    elif sem.camera_composition_focus and any(m in sem.camera_composition_focus[0].lower() for m in ("side", "dutch", "angle")):
        body += f", captured from {sem.camera_composition_focus[0]}"
    return body.strip().rstrip(",") + "."


def _paragraph_appearance(sem: ZitSemantics) -> str:
    if not sem.appearance:
        return ""
    details = ", ".join(sem.appearance[:8])
    expr = next((p for p in sem.appearance if "expression" in p.lower() or "smile" in p.lower()), "")
    if expr and expr in details:
        return f"She has {details}, with {expr}.".replace("with with", "with")
    return f"She has {details}."


def _paragraph_outfit(sem: ZitSemantics) -> str:
    outfit_parts = list(sem.outfit)
    nsfw_fabric = [p for p in sem.nsfw_neutral if any(m in p.lower() for m in ("unbuttoned", "slipping", "sheer", "wet", "open", "exposed"))]
    all_parts = outfit_parts + nsfw_fabric
    if not all_parts:
        return ""
    clothing = ", ".join(all_parts[:6])
    return f"She wears {clothing}, with elegant drapery and subtle fabric movement."


def _paragraph_scene(sem: ZitSemantics) -> str:
    if not sem.scene:
        return ""
    scene = ", ".join(sem.scene[:5])
    return f"The scene is set in {scene}."


def _paragraph_lighting(sem: ZitSemantics) -> str:
    parts = list(sem.lighting_atmosphere_mood)
    nsfw_light = [p for p in sem.nsfw_neutral if any(m in p.lower() for m in ("light", "spotlight", "rim", "glow", "highlight"))]
    parts.extend(nsfw_light)
    if not parts:
        return ""
    lighting = ", ".join(parts[:6])
    return f"The lighting is {lighting}, creating atmospheric depth and a cohesive mood."


def _paragraph_camera(sem: ZitSemantics) -> str:
    cam_parts = [p for p in sem.camera_composition_focus if p not in sem.pose_action_view]
    if not cam_parts:
        cam_parts = sem.camera_composition_focus
    if not cam_parts:
        return ""
    focus = ", ".join(cam_parts[:4])
    return f"The composition uses {focus}, with careful emphasis on the subject."


def _paragraph_materials(sem: ZitSemantics) -> str:
    parts = list(sem.materials_textures)
    nsfw_mat = [p for p in sem.nsfw_neutral if p not in parts and any(m in p.lower() for m in ("skin", "texture", "fabric", "satin", "highlights"))]
    parts.extend(nsfw_mat)
    if not parts:
        return ""
    mats = ", ".join(parts[:5])
    return f"Materials and textures include {mats}, with delicate highlights across hair, skin and fabric."


def _paragraph_render_line(sem: ZitSemantics) -> str:
    hint = (sem.style_render_hint or "").lower()
    if "realistic" in hint or "photoreal" in hint:
        return "The image has realistic rendering, clear anatomy and a cohesive elegant atmosphere."
    if "anime" in hint:
        return "The image has polished anime-style rendering, clear anatomy and a cohesive atmospheric mood."
    if sem.style_render_hint:
        return f"The image has {sem.style_render_hint}, clear anatomy and a cohesive atmosphere."
    return "The image has realistic rendering, clear anatomy and a cohesive atmosphere."


def render_zimage_turbo_v11(json_prompt: dict[str, Any]) -> ZitRenderResult:
    semantics = extract_zit_semantics(json_prompt)
    builders = (
        _paragraph_subject_pose_view,
        _paragraph_appearance,
        _paragraph_outfit,
        _paragraph_scene,
        _paragraph_lighting,
        _paragraph_camera,
        _paragraph_materials,
        _paragraph_render_line,
    )
    paragraphs = [p for fn in builders if (p := fn(semantics).strip())]
    text = "\n\n".join(paragraphs)
    return ZitRenderResult(text=text, semantics=semantics, paragraphs=paragraphs)
