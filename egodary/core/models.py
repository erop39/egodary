"""Базовые модели данных контентного слоя.

Эти модели — целевой формат, в который контент-пак-плагины приводят свои
`tags.yaml`. На этой фазе (1) они не привязаны ни к какому конкретному
формату вывода под модель — это сознательно: правила форматирования под
Illustrious/Anima/Z-Image Turbo появятся в фазах 4–5 как отдельные адаптеры,
а сами теги должны быть нейтральны к ним.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class TagItem(BaseModel):
    """Один тег/опция внутри категории.

    `tags` — варианты записи под разные целевые модели, например
    `{"illustrious": "...", "anima": "...", "zimage": "..."}`. Ключ модели,
    для которой явного варианта нет, на этапе форматирования будет
    разрешаться адаптером модели (фаза 4–5), а не здесь.
    """

    id: str
    label: str
    tags: dict[str, str] = Field(default_factory=dict)
    min_level: int | None = None  # для слайдеров интенсивности (используется позже, фаза 7)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("TagItem.id не может быть пустым")
        return value

    @model_validator(mode="after")
    def _normalize_meta_compat(self) -> TagItem:
        if self.meta is None:
            self.meta = {}
        subgroup = str(self.meta.get("subgroup") or "").strip()
        subcategory_id = str(self.meta.get("subcategory_id") or "").strip()
        if subgroup and not subcategory_id:
            # dual-read/dual-write compatibility with legacy subgroup-only payloads
            self.meta["subcategory_id"] = subgroup
        elif subcategory_id and not subgroup:
            self.meta["subgroup"] = subcategory_id

        if "normalized_name" not in self.meta or not str(self.meta.get("normalized_name") or "").strip():
            self.meta["normalized_name"] = self.label.strip().lower()
        if "aliases" not in self.meta or not isinstance(self.meta.get("aliases"), list):
            self.meta["aliases"] = []
        if "is_active" not in self.meta:
            self.meta["is_active"] = True
        return self


class TagCategory(BaseModel):
    """Категория тегов (например `scene.time_of_day`)."""

    id: str
    title: str
    items: list[TagItem] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _id_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("TagCategory.id не может быть пустым")
        return value

    def item_ids(self) -> set[str]:
        return {item.id for item in self.items}


class ConflictGroup(BaseModel):
    """Группа взаимоисключающих id тегов (аналог `FETISH_CONFLICT_GROUPS`).

    Хранится здесь как нейтральные данные; сам движок разрешения конфликтов —
    в `core/conflicts.py`, появится в фазе 6.
    """

    category_id: str
    ids: list[str]
    reason: str | None = None


CHARACTER_SCALAR_FIELDS = (
    "age_appearance",
    "body_type",
    "breast_size",
    "breast_shape",
    "waist",
    "hips_ass",
    "legs",
    "overall_figure",
    "height_build",
    "ethnicity",
    "skin_tone",
)


def coerce_character_payload(data: object) -> object:
    """Normalize legacy UI payloads where single-select fields were sent as lists."""
    if not isinstance(data, dict):
        return data
    for field in CHARACTER_SCALAR_FIELDS:
        value = data.get(field)
        if isinstance(value, list):
            data[field] = value[0] if value else ""
    body_details = data.get("body_details")
    if body_details is None:
        data["body_details"] = []
    elif not isinstance(body_details, list):
        data["body_details"] = [str(body_details)] if body_details else []
    if "thighs" in data and "legs" not in data:
        data["legs"] = data.pop("thighs")
    return data


class CharacterState(BaseModel):
    age_appearance: str = ""
    body_type: str = ""
    breast_size: str = ""
    breast_shape: str = ""
    waist: str = ""
    hips_ass: str = ""
    legs: str = ""
    overall_figure: str = ""
    height_build: str = ""
    ethnicity: str = ""
    skin_tone: str = ""
    body_details: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_payload(cls, data: object) -> object:
        return coerce_character_payload(data)


class CharacterPairState(BaseModel):
    primary: CharacterState = Field(default_factory=CharacterState)
    secondary: CharacterState | None = None
    auto_contrast: bool = True
    dna_linking: bool = False


class OutfitState(BaseModel):
    dress: str = ""
    top: str = ""
    bottom: str = ""
    legwear: str = ""
    jacket: str = ""
    footwear: str = ""
    gloves: str = ""
    cape: str = ""
    conditions: dict[str, dict[str, str]] = Field(default_factory=dict)

    @field_validator("conditions", mode="before")
    @classmethod
    def coerce_conditions(cls, value: object) -> dict[str, dict[str, str]]:
        if not isinstance(value, dict):
            return {}
        out: dict[str, dict[str, str]] = {}
        for slot, raw in value.items():
            if isinstance(raw, str):
                out[str(slot)] = {}
            elif isinstance(raw, dict):
                out[str(slot)] = {
                    str(dim): str(tag_id)
                    for dim, tag_id in raw.items()
                    if tag_id
                }
        return out


class AppearanceState(BaseModel):
    hair: str = ""
    hair_color: str = ""
    makeup: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    tattoos: list[str] = Field(default_factory=list)


class FaceState(BaseModel):
    facial_expression: str = ""
    mouth_lips: str = ""
    eyes: str = ""
    eye_color: str = ""
    skin: str = ""
    face_shape: str = ""
    eyebrows: str = ""
    nose: str = ""
    jaw_chin: str = ""
    age_maturity: str = ""
    beauty_archetype: str = ""
    facial_details: str = ""


class CharacterLibraryHair(BaseModel):
    hair: str = ""
    hair_color: str = ""


class CharacterLibraryPayload(BaseModel):
    """Character preset: body (Character) + Face + Hair only."""

    character: CharacterState = Field(default_factory=CharacterState)
    face: FaceState = Field(default_factory=FaceState)
    appearance: CharacterLibraryHair = Field(default_factory=CharacterLibraryHair)


class SceneState(BaseModel):
    time: str = ""
    weather: str = ""
    season: str = ""
    location: str = ""


class EnvironmentState(BaseModel):
    location: str = ""
    situation: str = ""
    modifiers: list[str] = Field(default_factory=list)


class CameraState(BaseModel):
    angle: str = ""
    framing: str = ""
    lens: str = ""
    focus: str = ""
    composition: str = ""
    nsfw_shot: str = ""


class LightingState(BaseModel):
    light_type: str = ""
    direction: str = ""
    quality: str = ""
    color_mood: str = ""
    nsfw: str = ""


class FetishState(BaseModel):
    elements: list[str] = Field(default_factory=list)


class StyleState(BaseModel):
    enabled: bool = True
    art_style: str = "anime_style"
    artist_style: str = ""
    quality: list[str] = Field(default_factory=list)
    aesthetic: list[str] = Field(default_factory=list)
    technique: list[str] = Field(default_factory=list)
    quality_boosters_enabled: bool = True
    quality_boosters_level: str = "high"


class InteractionState(BaseModel):
    partner: str = ""
    action: str = ""


class PromptState(BaseModel):
    model_id: str = "illustrious"
    character: CharacterState = Field(default_factory=CharacterState)
    characters: CharacterPairState = Field(default_factory=CharacterPairState)
    outfit: OutfitState = Field(default_factory=OutfitState)
    appearance: AppearanceState = Field(default_factory=AppearanceState)
    face: FaceState = Field(default_factory=FaceState)
    scene: SceneState = Field(default_factory=SceneState)
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    pose: str = ""
    camera: CameraState = Field(default_factory=CameraState)
    lighting: LightingState = Field(default_factory=LightingState)
    fetish: FetishState = Field(default_factory=FetishState)
    interaction: InteractionState = Field(default_factory=InteractionState)
    personality: str = ""
    expression: str = ""
    mood_preset: str = ""
    atmosphere: list[str] = Field(default_factory=list)
    occupation: str = ""
    archetype: str = ""
    waist: str = ""
    neck_accessories: list[str] = Field(default_factory=list)
    leg_detail_focus: bool = False
    intensity: int = 5
    lewdness: int = 3
    detail: int = 5
    style: StyleState = Field(default_factory=StyleState)
    group_mode: bool = False
    god_mode_bundle: str = ""

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_payload(cls, data: object) -> object:
        """Accept slightly malformed UI/session payloads instead of returning 422."""
        if not isinstance(data, dict):
            return data

        character = data.get("character")
        if isinstance(character, dict):
            data["character"] = coerce_character_payload(character)

        lighting = data.get("lighting")
        if isinstance(lighting, dict):
            quality = lighting.get("quality")
            if isinstance(quality, list):
                lighting["quality"] = quality[0] if quality else ""

        for list_path in (
            ("style", "quality"),
            ("style", "aesthetic"),
            ("style", "technique"),
            ("appearance", "makeup"),
            ("appearance", "accessories"),
            ("environment", "modifiers"),
            ("fetish", "elements"),
        ):
            parent_key, child_key = list_path
            parent = data.get(parent_key)
            if isinstance(parent, dict) and parent.get(child_key) is None:
                parent[child_key] = []

        outfit = data.get("outfit")
        if isinstance(outfit, dict) and outfit.get("conditions") is None:
            outfit["conditions"] = {}

        return data


class PromptBuckets(BaseModel):
    quality: list[str] = Field(default_factory=list)
    subject: list[str] = Field(default_factory=list)
    character: list[str] = Field(default_factory=list)
    face: list[str] = Field(default_factory=list)
    hair: list[str] = Field(default_factory=list)
    makeup: list[str] = Field(default_factory=list)
    appearance: list[str] = Field(default_factory=list)
    outfit: list[str] = Field(default_factory=list)
    tattoos: list[str] = Field(default_factory=list)
    pose: list[str] = Field(default_factory=list)
    situation: list[str] = Field(default_factory=list)
    scene: list[str] = Field(default_factory=list)
    lighting: list[str] = Field(default_factory=list)
    atmosphere: list[str] = Field(default_factory=list)
    camera: list[str] = Field(default_factory=list)
    fetish: list[str] = Field(default_factory=list)
    extra: list[str] = Field(default_factory=list)
    style: list[str] = Field(default_factory=list)


class AssembledPrompt(BaseModel):
    positive: str
    negative: str | None = None
    buckets: PromptBuckets
    model_id: str
