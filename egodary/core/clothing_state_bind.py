"""Bind per-slot clothing state modifiers to the garment tag for that slot."""

from __future__ import annotations

CLOTHING_STATE_DIMENSION_ORDER: tuple[str, ...] = (
    "partial_removal",
    "disorder",
    "fit",
    "damage",
    "transparency",
    "moisture",
    "stains",
    "extra",
    "color",
)

_ANIMA_EXTRA_SUFFIXES = frozenset({"clothing detail", "styled outfit"})


def _dedupe_preserve_order(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for part in parts:
        key = part.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(part.strip())
    return out


def _split_tag_pieces(tag: str) -> list[str]:
    return [piece.strip() for piece in tag.split(",") if piece.strip()]


def _strip_wearing_prefix(text: str) -> str:
    lowered = text.lower()
    if lowered.startswith("wearing "):
        return text[8:].strip()
    return text.strip()


def normalize_clothing_modifier(text: str, model_id: str) -> str:
    """Turn catalog state text into a short modifier phrase (no generic 'clothing')."""
    piece = _strip_wearing_prefix(text)
    piece_lower = piece.lower()
    if piece_lower in _ANIMA_EXTRA_SUFFIXES:
        return ""
    for prefix in ("clothing ", "wearing "):
        if piece_lower.startswith(prefix):
            piece = piece[len(prefix) :].strip()
            piece_lower = piece.lower()
    for suffix in (" clothing", " fabric", " edges"):
        if piece_lower.endswith(suffix):
            piece = piece[: -len(suffix)].strip()
            piece_lower = piece.lower()
    if piece_lower in _ANIMA_EXTRA_SUFFIXES:
        return ""
    if piece_lower.startswith("clothing with "):
        piece = piece[14:].strip()
    return piece


def _garment_primary_and_suffixes(garment: str, model_id: str) -> tuple[str, list[str]]:
    pieces = _split_tag_pieces(garment)
    if not pieces:
        return "", []
    primary = pieces[0]
    suffixes = pieces[1:]
    if model_id == "zimage_turbo":
        primary = _strip_wearing_prefix(primary)
    return primary, suffixes


def bind_clothing_modifiers_to_garment(
    garment: str,
    modifiers: list[str],
    *,
    model_id: str,
) -> str:
    """Prefix slot state modifiers onto the garment phrase for that slot."""
    modifier_parts: list[str] = []
    for mod in modifiers:
        for piece in _split_tag_pieces(mod):
            normalized = normalize_clothing_modifier(piece, model_id)
            if normalized:
                modifier_parts.append(normalized)
    modifier_parts = _dedupe_preserve_order(modifier_parts)

    garment_primary, garment_suffixes = _garment_primary_and_suffixes(garment, model_id)
    if not modifier_parts:
        return garment
    if not garment_primary:
        joined = " ".join(modifier_parts)
        if model_id == "zimage_turbo":
            return f"wearing {joined}"
        return joined

    bound_primary = f"{' '.join(modifier_parts)} {garment_primary}".strip()

    if model_id == "zimage_turbo":
        return f"wearing {bound_primary}"

    suffixes = [s for s in garment_suffixes if s.lower() not in _ANIMA_EXTRA_SUFFIXES or s.lower() == "styled outfit"]
    if model_id == "anima":
        if "styled outfit" in garment_suffixes and "styled outfit" not in suffixes:
            suffixes.append("styled outfit")
        if modifier_parts and "clothing detail" not in [s.lower() for s in suffixes]:
            suffixes.append("clothing detail")
    if suffixes:
        return f"{bound_primary}, {', '.join(suffixes)}"
    return bound_primary


def collect_bound_outfit_tags(
    *,
    garment_value: str,
    garment_category: str,
    condition_dims: dict[str, str] | str,
    model_id: str,
    resolve,
) -> list[str]:
    """Resolve one outfit slot: garment tag(s) with slot states bound in-place."""
    resolved_garment = ""
    if garment_value:
        resolved_garment = resolve(garment_value, garment_category, model_id) or ""

    if isinstance(condition_dims, str):
        condition_dims = {}
    modifier_chunks: list[str] = []
    for dimension in CLOTHING_STATE_DIMENSION_ORDER:
        tag_id = (condition_dims or {}).get(dimension, "")
        if not tag_id:
            continue
        resolved = resolve(tag_id, "outfit.clothing_state", model_id)
        if resolved:
            modifier_chunks.append(resolved)

    if not resolved_garment:
        return []

    if modifier_chunks:
        return [
            bind_clothing_modifiers_to_garment(
                resolved_garment,
                modifier_chunks,
                model_id=model_id,
            )
        ]

    # Keep comma-grouped anima/zimage garment phrases intact (styled outfit, wearing …).
    return [resolved_garment]
