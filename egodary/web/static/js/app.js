/** eGOdary web UI — thin client for FastAPI backend */

const API = "/api";
const SESSION_STORAGE_KEY = "egodary.session.v1";
const SESSION_FILE_VERSION = 9;

const BODY_DETAILS_ID_MIGRATION = {
  smooth_skin: "smooth_flawless_skin",
  dewy_skin: "dewy__glowing_skin",
  oily__shiny_skin: "oily_shiny_skin",
  skin_texture_finish_matte_skin: "matte_skin",
  additional_details_beauty_marks__moles: "beauty_marks__moles",
};

function migrateBodyDetailsIds(data) {
  const details = data.character?.body_details;
  if (!Array.isArray(details) || !details.length) return;
  const migrated = [];
  for (const rawId of details) {
    const id = String(rawId || "").trim();
    if (!id) continue;
    const mapped = BODY_DETAILS_ID_MIGRATION[id] || id;
    if (!migrated.includes(mapped)) migrated.push(mapped);
  }
  data.character.body_details = migrated;
}

function migrateSkinSubgroups(data) {
  migrateBodyDetailsIds(data);
}

const FACE_SKIN_TONE_MIGRATION = {
  fair_porcelain_skin: "fair__porcelain",
  light_beige: "light_beige",
  warm_tan: "warm_tan",
  golden_olive: "golden__olive",
  deep_brown: "deep_tan",
  ebony: "dark__ebony",
  pale_with_pink_undertones: "pale_with_pink_undertones",
  sun_kissed_skin: "tan",
};

const CLOTHING_STATE_DIMENSIONS = [
  { id: "moisture", label: "Moisture & Wetness" },
  { id: "damage", label: "Damage & Wear" },
  { id: "transparency", label: "Transparency & Sheerness" },
  { id: "fit", label: "Fit & Tension" },
  { id: "disorder", label: "Disorder & Messiness" },
  { id: "partial_removal", label: "Partial Removal & Exposure" },
  { id: "stains", label: "Stains & Fluids" },
  { id: "color", label: "Color" },
  { id: "extra", label: "Additional states" },
];

function createDefaultOutfitConditions() {
  return {
    dress: {},
    top: {},
    bottom: {},
    underwear_layer: {},
    legwear: {},
    jacket: {},
    footwear: {},
    gloves: {},
    cape: {},
  };
}

function sanitizeSlotConditions(raw) {
  if (!raw || typeof raw === "string") return {};
  if (typeof raw !== "object" || Array.isArray(raw)) return {};
  const out = {};
  for (const [dim, tagId] of Object.entries(raw)) {
    if (tagId) out[dim] = String(tagId);
  }
  return out;
}

function sanitizeOutfitConditions(raw, template = createDefaultOutfitConditions()) {
  const out = { ...template };
  for (const key of Object.keys(template)) {
    out[key] = sanitizeSlotConditions(raw?.[key]);
  }
  return out;
}

function countSlotConditions(slotConditions) {
  if (!slotConditions) return 0;
  if (typeof slotConditions === "string") return slotConditions ? 1 : 0;
  return Object.values(slotConditions).filter(Boolean).length;
}

function migrateSkinFromFace(data) {
  const faceSkin = data.face?.skin;
  if (!faceSkin) return;
  if (!data.character) data.character = {};
  if (FACE_SKIN_TONE_MIGRATION[faceSkin]) {
    data.character.skin_tone = FACE_SKIN_TONE_MIGRATION[faceSkin];
  } else if (faceSkin) {
    if (!Array.isArray(data.character.body_details)) data.character.body_details = [];
    if (!data.character.body_details.includes(faceSkin)) {
      data.character.body_details.push(faceSkin);
    }
  }
  data.face.skin = "";
}

function migrateOutfitConditionsShape(data) {
  const outfit = data.outfit;
  if (!outfit) return;
  outfit.conditions = sanitizeOutfitConditions(outfit.conditions);
}

function migrateSessionData(data) {
  let version = Number(data.version) || 0;
  if (version < 7) {
    migrateSkinFromFace(data);
    version = 7;
  }
  if (version < 8) {
    migrateOutfitConditionsShape(data);
    version = 8;
  }
  if (version < 9) {
    migrateSkinSubgroups(data);
    version = 9;
  }
  data.version = version;
  return data;
}

const MODEL_LABELS = {
  illustrious: "Illustrious",
  anima: "Anima",
  zimage_turbo: "Z-Image Turbo",
};

let favoritesGenDefaults = null;
let activeFavoriteId = null;
let editingFavoriteId = null;
let addTagCategoriesCache = [];
let tagStudioListerItems = [];
let tagStudioSelectedTagRow = null;
let tagStudioListerInitialized = false;

function createDefaultCharacter() {
  return {
    age_appearance: "",
    body_type: "",
    breast_size: "",
    breast_shape: "",
    waist: "",
    hips_ass: "",
    legs: "",
    overall_figure: "",
    height_build: "",
    ethnicity: "",
    skin_tone: "",
    body_details: [],
  };
}

function createDefaultState() {
  return {
    model_id: "illustrious",
    style: {
      enabled: true,
      art_style: "anime_style",
      artist_style: "",
      quality: [],
      aesthetic: [],
      technique: [],
      quality_boosters_enabled: true,
      quality_boosters_level: "high",
    },
    character: createDefaultCharacter(),
    scene: { time: "", weather: "", season: "", location: "" },
    environment: { location: "", situation: "", modifiers: [] },
    outfit: {
      dress: "",
      top: "",
      bottom: "",
      underwear_layer: "",
      legwear: "",
      jacket: "",
      footwear: "",
      gloves: "",
      cape: "",
      conditions: {
        dress: {},
        top: {},
        bottom: {},
        underwear_layer: {},
        legwear: {},
        jacket: {},
      },
    },
    appearance: {
      hair: "",
      hair_color: "",
      makeup: [],
      accessories: [],
      tattoos: [],
    },
    face: {
      facial_expression: "",
      mouth_lips: "",
      eyes: "",
      eye_color: "",
      skin: "",
      face_shape: "",
      eyebrows: "",
      nose: "",
      jaw_chin: "",
      age_maturity: "",
      beauty_archetype: "",
      facial_details: "",
    },
    pose: "",
    camera: { angle: "", framing: "", lens: "", focus: "", composition: "", nsfw_shot: "" },
    lighting: { light_type: "", direction: "", quality: "", color_mood: "", nsfw: "" },
    fetish: { elements: [] },
    intensity: 5,
    lewdness: 3,
    detail: 5,
    group_mode: false,
  };
}

const state = createDefaultState();

const TAB_META = {
  style: { title: "Style", desc: "Художественный стиль, качество рендера и эстетика · Off убирает стиль из промпта" },
  character: { title: "Character", desc: "Библиотека персонажей — карточка вверху · сохранить / загрузить пресет" },
  face: { title: "Face", desc: "Выражение, возраст, архетип и детали лица" },
  makeup: { title: "Makeup", desc: "Макияж · multi-select до 6" },
  outfit: { title: "Outfit", desc: "Одежда по категориям" },
  accessories: { title: "Accessories", desc: "Аксессуары · multi-select до 4" },
  pose: { title: "Pose", desc: "Одна поза · solo или couple (couple только с Group mode)" },
  camera: { title: "Camera", desc: "Ракурс, кадрирование, объектив · Off / Random" },
  lighting: { title: "Lighting", desc: "Источники света, направление, качество и цвет · Off / Random" },
  environment: { title: "Environment", desc: "Время, погода, сезон, локация, ситуация и атмосферные модификаторы · Off / Random" },
  fetish: { title: "Fetish", desc: "Элементы фетиша · multi-select до 6 на группу" },
  prompting: { title: "Prompting", desc: "Analyze · Import · NSFW Styler — работа с текстом промпта" },
  tagstudio: { title: "Tag Studio", desc: "Категории и подкатегории тегов, дедупликация, миграция и rollback runtime overlay" },
  wildcards: { title: "Wildcards", desc: "Свои текстовые списки тегов — привязка к категории/подгруппе, чекбоксы вкл/выкл" },
  favorites: { title: "Favorites", desc: "Сохраненные промпты: просмотр, редактирование, экспорт, превью ссылок" },
  llm: { title: "LLM Settings", desc: "Ollama: модель, температура, таймаут · для classify и NSFW refine" },
  advanced: { title: "Advanced", desc: "Rules, Debug, Changelog · Import prompt → state" },
};

const PROMPTING_TREE = [
  { id: "prompt_analyze", label: "Prompt Analyze", panel: "analyze", hint: "extract_core · convert_to_model · convert_to_json · normalize_weights" },
  { id: "prompt_import", label: "Prompt Import", panel: "import", hint: "parse · classify · merge_to_registry" },
  { id: "prompt_nsfw", label: "NSFW Styler", panel: "nsfw", hint: "Каталог + rules · LLM refine или full rewrite (не как свободный чат)" },
];

let activePromptingLeafId = "prompt_analyze";
let activeNsfwIntensity = "medium";
let llmSettingsCache = null;
let llmProgressDepth = 0;
let llmProgressTicker = null;
let llmProgressStartedAt = 0;
let llmProgressExpectedMs = 30000;

const DRESS_LAYER_SUBGROUPS = new Set(["micro_mini", "sheer", "bodysuit_harness"]);

const OUTFIT_TREE = [
  {
    id: "dress",
    label: "Dress",
    children: [
      { id: "dress_micro_mini", label: "Micro / Mini", field: "dress", categoryId: "outfit.dress", subgroup: "micro_mini", conditionField: "dress" },
      { id: "dress_sheer", label: "Sheer / Transparent", field: "dress", categoryId: "outfit.dress", subgroup: "sheer", conditionField: "dress" },
      { id: "dress_latex_vinyl", label: "Latex / Vinyl / Wetlook", field: "dress", categoryId: "outfit.dress", subgroup: "latex_vinyl", conditionField: "dress" },
      { id: "dress_high_slit", label: "High Slit & Cutout", field: "dress", categoryId: "outfit.dress", subgroup: "high_slit_cutout", conditionField: "dress" },
      { id: "dress_bodysuit", label: "Bodysuit / Harness", field: "dress", categoryId: "outfit.dress", subgroup: "bodysuit_harness", conditionField: "dress" },
    ],
  },
  {
    id: "top",
    label: "Top",
    children: [
      { id: "top_harness", label: "Harness / Strappy", field: "top", categoryId: "outfit.top", subgroup: "harness_strappy", conditionField: "top" },
      { id: "top_sheer", label: "Sheer / See-through", field: "top", categoryId: "outfit.top", subgroup: "sheer_crop", conditionField: "top" },
      { id: "top_transparent_sheer", label: "Transparent / Sheer Tops", field: "top", categoryId: "outfit.top", subgroup: "transparent_sheer_tops", conditionField: "top" },
      { id: "top_bodysuits", label: "Bodysuits & Leotards", field: "top", categoryId: "outfit.top", subgroup: "bodysuits", conditionField: "top" },
      { id: "top_latex", label: "Latex / Vinyl", field: "top", categoryId: "outfit.top", subgroup: "latex_vinyl", conditionField: "top" },
      { id: "top_micro", label: "Micro / Extreme", field: "top", categoryId: "outfit.top", subgroup: "micro_extreme", conditionField: "top" },
    ],
  },
  {
    id: "bottoms",
    label: "Bottom",
    children: [
      { id: "long_pants", label: "Long Pants", field: "bottom", categoryId: "outfit.bottom", subgroup: "long_pants", conditionField: "bottom" },
      { id: "skirts", label: "Skirts", field: "bottom", categoryId: "outfit.bottom", subgroup: "skirts" },
      { id: "transparent_plastic_skirts", label: "Transparent / Plastic Skirts", field: "bottom", categoryId: "outfit.bottom", subgroup: "transparent_plastic_skirts" },
      { id: "shorts", label: "Shorts", field: "bottom", categoryId: "outfit.bottom", subgroup: "shorts" },
      { id: "underwear", label: "Underwear", field: "bottom", categoryId: "outfit.bottom", subgroup: "underwear", conditionField: "underwear_layer" },
      { id: "underwear_layer", label: "Underwear layer", field: "underwear_layer", categoryId: "outfit.underwear_layer", conditionField: "underwear_layer" },
      { id: "legwear_classic", label: "Stockings & Tights", field: "legwear", categoryId: "outfit.legwear", subgroup: "classic", conditionField: "legwear" },
      { id: "legwear_neon", label: "Neon & Bright Legwear", field: "legwear", categoryId: "outfit.legwear", subgroup: "neon_legwear", conditionField: "legwear" },
    ],
  },
  {
    id: "jacket",
    label: "Jacket",
    children: [
      { id: "jacket_cropped", label: "Cropped", field: "jacket", categoryId: "outfit.jacket", subgroup: "cropped", conditionField: "jacket" },
      { id: "jacket_long", label: "Long / Dramatic", field: "jacket", categoryId: "outfit.jacket", subgroup: "long_dramatic", conditionField: "jacket" },
      { id: "jacket_fetish", label: "Leather / Latex / Fetish", field: "jacket", categoryId: "outfit.jacket", subgroup: "leather_latex_fetish", conditionField: "jacket" },
      { id: "jacket_sheer", label: "Sheer / Revealing", field: "jacket", categoryId: "outfit.jacket", subgroup: "sheer_revealing", conditionField: "jacket" },
    ],
  },
  {
    id: "footwear",
    label: "Footwear",
    children: [
      { id: "footwear_thigh", label: "Thigh High & OTK", field: "footwear", categoryId: "outfit.footwear", subgroup: "thigh_high", conditionField: "footwear" },
      { id: "footwear_platform", label: "Platform & High Heels", field: "footwear", categoryId: "outfit.footwear", subgroup: "platform_heels", conditionField: "footwear" },
      { id: "footwear_fetish", label: "Fetish & Alt Boots", field: "footwear", categoryId: "outfit.footwear", subgroup: "fetish_boots", conditionField: "footwear" },
      { id: "footwear_casual", label: "Casual / Sporty NSFW", field: "footwear", categoryId: "outfit.footwear", subgroup: "casual_nsfw", conditionField: "footwear" },
    ],
  },
  {
    id: "gloves",
    label: "Gloves",
    children: [
      { id: "gloves_long", label: "Long / Opera", field: "gloves", categoryId: "outfit.gloves", subgroup: "long_opera", conditionField: "gloves" },
      { id: "gloves_short", label: "Short & Fashion", field: "gloves", categoryId: "outfit.gloves", subgroup: "short_fashion", conditionField: "gloves" },
      { id: "gloves_harness", label: "Harness / Bondage", field: "gloves", categoryId: "outfit.gloves", subgroup: "harness_bondage", conditionField: "gloves" },
      { id: "gloves_fingerless", label: "Fingerless & Alt", field: "gloves", categoryId: "outfit.gloves", subgroup: "fingerless_alt", conditionField: "gloves" },
    ],
  },
  {
    id: "cape",
    label: "Cape",
    children: [
      { id: "cape_long", label: "Long Dramatic", field: "cape", categoryId: "outfit.cape", subgroup: "long_dramatic", conditionField: "cape" },
      { id: "cape_short", label: "Short / Cropped", field: "cape", categoryId: "outfit.cape", subgroup: "short_cropped", conditionField: "cape" },
      { id: "cape_hooded", label: "Hooded & Fetish", field: "cape", categoryId: "outfit.cape", subgroup: "hooded_fetish", conditionField: "cape" },
      { id: "cape_sheer", label: "Sheer / Revealing", field: "cape", categoryId: "outfit.cape", subgroup: "sheer_revealing", conditionField: "cape" },
    ],
  },
];

const HAIR_TREE = [
  {
    id: "hair",
    label: "Hair",
    children: [
      { id: "hair_long", label: "Long Styles", field: "hair", categoryId: "appearance.hair", subgroup: "long" },
      { id: "hair_updos", label: "Updos & Buns", field: "hair", categoryId: "appearance.hair", subgroup: "updos_buns" },
      { id: "hair_braids", label: "Braids & Ponytails", field: "hair", categoryId: "appearance.hair", subgroup: "braids_ponytails" },
      { id: "hair_short", label: "Short & Alternative", field: "hair", categoryId: "appearance.hair", subgroup: "short_alt" },
      { id: "hair_color", label: "Hair Color", field: "hair_color", categoryId: "appearance.hair_color", subgroup: "hair_color" },
    ],
  },
];

const MAKEUP_TREE = [
  {
    id: "makeup",
    label: "Makeup",
    children: [
      { id: "makeup_eyes", label: "Eyes", field: "makeup", categoryId: "appearance.makeup", subgroup: "eyes", multi: true },
      { id: "makeup_lips", label: "Lips", field: "makeup", categoryId: "appearance.makeup", subgroup: "lips", multi: true },
      { id: "makeup_full", label: "Full Face / Fetish", field: "makeup", categoryId: "appearance.makeup", subgroup: "full_face", multi: true },
    ],
  },
];

const ACCESSORIES_TREE = [
  {
    id: "accessories",
    label: "Accessories",
    children: [
      { id: "acc_body", label: "Body Jewelry & Harness", field: "accessories", categoryId: "appearance.accessories", subgroup: "body_jewelry", multi: true },
      { id: "acc_belts", label: "Belts & Waist", field: "accessories", categoryId: "appearance.accessories", subgroup: "belts_waist", multi: true },
      { id: "acc_headwear", label: "Headwear & Hats", field: "accessories", categoryId: "appearance.accessories", subgroup: "headwear", multi: true },
      { id: "acc_chokers", label: "Chokers & Neck", field: "accessories", categoryId: "appearance.accessories", subgroup: "chokers_neck", multi: true },
      { id: "acc_bags", label: "Bags & Extra", field: "accessories", categoryId: "appearance.accessories", subgroup: "bags_extra", multi: true },
      { id: "acc_backpacks", label: "Backpacks", field: "accessories", categoryId: "appearance.accessories", subgroup: "backpacks", multi: true },
      { id: "acc_gaming", label: "Gaming", field: "accessories", categoryId: "appearance.accessories", subgroup: "gaming", multi: true },
      { id: "acc_sport", label: "Sport", field: "accessories", categoryId: "appearance.accessories", subgroup: "sport", multi: true },
      { id: "acc_angelic", label: "Angelic", field: "accessories", categoryId: "appearance.accessories", subgroup: "angelic", multi: true },
      { id: "acc_demonic", label: "Demonic", field: "accessories", categoryId: "appearance.accessories", subgroup: "demonic", multi: true },
      { id: "acc_crowns", label: "Crowns & Tiaras", field: "accessories", categoryId: "appearance.accessories", subgroup: "crowns_tiaras", multi: true },
      { id: "acc_medical", label: "Medical / Hospital", field: "accessories", categoryId: "appearance.accessories", subgroup: "medical", multi: true },
      { id: "acc_religious", label: "Religious / Church", field: "accessories", categoryId: "appearance.accessories", subgroup: "religious", multi: true },
      {
        id: "acc_tattoos_group",
        label: "Tattoos & Body Art",
        children: [
          { id: "acc_tattoo_styles", label: "Tattoo Styles", field: "tattoos", categoryId: "appearance.tattoos", subgroup: "styles", multi: true },
          { id: "acc_tattoo_placements", label: "Tattoo Placements", field: "tattoos", categoryId: "appearance.tattoos", subgroup: "placements", multi: true },
          { id: "acc_tattoo_themes", label: "Tattoo Themes", field: "tattoos", categoryId: "appearance.tattoos", subgroup: "themes", multi: true },
          { id: "acc_tattoo_specific", label: "Specific Tattoos", field: "tattoos", categoryId: "appearance.tattoos", subgroup: "specific", multi: true },
          { id: "acc_tattoo_temporary", label: "Temporary Tattoos", field: "tattoos", categoryId: "appearance.tattoos", subgroup: "temporary", multi: true },
        ],
      },
    ],
  },
];

let activeCharacterLeafId = "character_age_appearance_ranges";
let activeFaceLeafId = "face_facial_expression_seductive_teasing";
let activeOutfitLeafId = "dress_micro_mini";
let activeMakeupLeafId = "makeup_eyes";
let activeAccessoriesLeafId = "acc_body";
let activePoseLeafId = "pose_standing_seductive";
let pendingActiveTab = null;
let sessionPersistTimer = null;

const POSE_TREE = [
  {
    id: "pose_solo",
    label: "Solo",
    children: [
      { id: "pose_standing_seductive", label: "Standing Seductive & Power", categoryId: "pose.solo", subgroup: "standing_seductive" },
      { id: "pose_standing_tease", label: "Standing Revealing / Tease", categoryId: "pose.solo", subgroup: "standing_tease" },
      { id: "pose_sitting_kneeling", label: "Sitting & Kneeling", categoryId: "pose.solo", subgroup: "sitting_kneeling" },
      { id: "pose_lying_bed", label: "Lying & Bed", categoryId: "pose.solo", subgroup: "lying_bed" },
      { id: "pose_all_fours", label: "On All Fours", categoryId: "pose.solo", subgroup: "all_fours" },
      { id: "pose_dynamic", label: "Dynamic & Action", categoryId: "pose.solo", subgroup: "dynamic_action" },
      { id: "pose_self_touch", label: "Self-Touch", categoryId: "pose.solo", subgroup: "self_touch" },
      { id: "pose_extreme", label: "Extreme Solo", categoryId: "pose.solo", subgroup: "extreme_solo" },
    ],
  },
  {
    id: "pose_couple",
    label: "Couple",
    requiresGroup: true,
    children: [
      { id: "pose_couple_standing", label: "Standing Intimate", categoryId: "pose.couple", subgroup: "standing_intimate", requiresGroup: true },
      { id: "pose_couple_kissing", label: "Kissing & Foreplay", categoryId: "pose.couple", subgroup: "kissing_foreplay", requiresGroup: true },
      { id: "pose_couple_sex_standing", label: "Sexual Standing", categoryId: "pose.couple", subgroup: "sexual_standing", requiresGroup: true },
      { id: "pose_couple_oral", label: "Oral & Foreplay", categoryId: "pose.couple", subgroup: "oral_foreplay", requiresGroup: true },
      { id: "pose_couple_penetration", label: "Penetration / Sex", categoryId: "pose.couple", subgroup: "penetration", requiresGroup: true },
      { id: "pose_couple_aftercare", label: "Tease & Aftercare", categoryId: "pose.couple", subgroup: "tease_aftercare", requiresGroup: true },
    ],
  },
];

const itemSubgroupMaps = {};
const itemLabelCache = {};
const fieldSelectionModes = new Map();
let conflictPreviewTimer = null;
let conflictPreviewRequest = 0;
let qualityPreviewRequest = 0;
let promptPreviewTimer = null;
let promptPreviewRequest = 0;

// Undo stack — serialized buildPayload() snapshots, before each state-mutating click
const UNDO_STACK_MAX = 30;
const undoStack = [];

// Forge settings cache
let forgeSettingsCache = null;

const FACE_VIBE_FIELDS = ["facial_expression", "age_maturity", "beauty_archetype", "facial_details"];
const CHARACTER_FACE_FIELDS = [
  "mouth_lips", "eyes", "eye_color", "skin", "face_shape", "eyebrows", "nose", "jaw_chin",
];
const CHARACTER_FACE_GROUP_IDS = new Set([
  "face_mouth_lips",
  "face_eyes",
  "face_face_shape",
  "face_eyebrows",
  "face_nose",
  "face_jaw_chin",
]);
const FACE_VIBE_GROUP_IDS = new Set([
  "face_facial_expression",
  "face_age_maturity",
  "face_beauty_archetype",
  "face_facial_details",
]);

const TAB_COUNTS = {
  character: () => {
    const ch = state.character;
    let count = 0;
    for (const [key, val] of Object.entries(ch)) {
      if (key === "body_details") count += val.length;
      else if (val) count += 1;
    }
    count += CHARACTER_FACE_FIELDS.filter((field) => state.face[field]).length;
    if (state.appearance.hair) count += 1;
    if (state.appearance.hair_color) count += 1;
    return count;
  },
  face: () => FACE_VIBE_FIELDS.filter((field) => {
    const value = state.face[field];
    return typeof value === "string" ? Boolean(value) : Array.isArray(value) && value.length > 0;
  }).length,
  style: () => {
    if (!state.style.enabled) return 0;
    return (state.style.art_style ? 1 : 0)
      + (state.style.artist_style ? 1 : 0)
      + state.style.quality.length
      + state.style.aesthetic.length
      + state.style.technique.length;
  },
  environment: () => {
    const sceneCount = ["time", "weather", "season"].filter((key) => state.scene[key]).length;
    return sceneCount + (state.environment.location ? 1 : 0)
      + (state.environment.situation ? 1 : 0)
      + state.environment.modifiers.length;
  },
  outfit: () => {
    const garmentFields = ["dress", "top", "bottom", "underwear_layer", "legwear", "jacket", "footwear", "gloves", "cape"];
    let count = garmentFields.filter((key) => state.outfit[key]).length;
    count += Object.values(state.outfit.conditions || {}).reduce(
      (sum, slot) => sum + countSlotConditions(slot),
      0,
    );
    return count;
  },
  makeup: () => state.appearance.makeup.length,
  accessories: () => state.appearance.accessories.length + (state.appearance.tattoos?.length || 0),
  pose: () => (state.pose ? 1 : 0),
  camera: () => Object.values(state.camera).filter((v) => v).length,
  lighting: () => Object.values(state.lighting).filter((v) => v).length,
  fetish: () => state.fetish.elements.length,
};

function filterFaceTreeByGroups(groupIds) {
  return (window.FACE_TREE || []).filter((node) => groupIds.has(node.id));
}

function getCharacterStructureTree() {
  return [
    ...(window.CHARACTER_TREE || []),
    ...filterFaceTreeByGroups(CHARACTER_FACE_GROUP_IDS),
    ...HAIR_TREE,
  ];
}

function getFaceVibeTree() {
  return filterFaceTreeByGroups(FACE_VIBE_GROUP_IDS);
}

function isFaceVibeLeafId(leafId) {
  return Boolean(findTreeLeaf(leafId, getFaceVibeTree()));
}

function getTreePanels() {
  return [
    { getTree: getCharacterTree, elId: "character-tree" },
    { getTree: getFaceTree, elId: "face-tree" },
    { getTree: getOutfitTree, elId: "outfit-tree" },
    { getTree: getMakeupTree, elId: "makeup-tree" },
    { getTree: getAccessoriesTree, elId: "accessories-tree" },
    { getTree: getPoseTree, elId: "pose-tree" },
    { getTree: getCameraTree, elId: "camera-tree" },
    { getTree: getLightingTree, elId: "lighting-tree" },
    { getTree: getEnvironmentTree, elId: "environment-tree" },
    { getTree: getStyleTree, elId: "style-tree" },
    { getTree: getFetishTree, elId: "fetish-tree" },
  ];
}

const selectionCountEls = new Map();
let clothingStateCatalog = null;
let clothingStateLoadingPromise = null;
let clothingStateOpenSections = new Set();
let advancedTodoItems = [];
let advancedTodoSaveTimer = null;

const CONDITION_FIELD_LABELS = {
  dress: "Dress wear condition",
  top: "Top wear condition",
  bottom: "Pants / jeans condition",
  underwear_layer: "Lingerie condition",
  legwear: "Stockings / fishnets condition",
  jacket: "Outerwear condition",
  footwear: "Footwear condition",
  gloves: "Gloves condition",
  cape: "Cape condition",
};

function getGarmentForConditionField(field) {
  if (field === "underwear_layer") {
    if (state.outfit.underwear_layer) return state.outfit.underwear_layer;
    const bottomMap = itemSubgroupMaps["outfit.bottom"] || {};
    if (bottomMap[state.outfit.bottom] === "underwear") return state.outfit.bottom;
    return "";
  }
  return state.outfit[field] || "";
}

function garmentMatchesLeaf(node, garmentId) {
  if (!garmentId) return false;
  if (!node.subgroup) return true;
  const map = itemSubgroupMaps[node.categoryId] || {};
  return map[garmentId] === node.subgroup;
}

async function ensureClothingStateCatalog() {
  if (clothingStateCatalog) return clothingStateCatalog;
  if (clothingStateLoadingPromise) return clothingStateLoadingPromise;
  clothingStateLoadingPromise = (async () => {
    try {
      const data = await api("/categories/outfit.clothing_state");
      const byDimension = {};
      for (const item of data.items || []) {
        const dimension = item.meta?.dimension;
        if (!dimension) continue;
        if (!byDimension[dimension]) byDimension[dimension] = [];
        byDimension[dimension].push(item);
      }
      clothingStateCatalog = byDimension;
    } catch (_) {
      clothingStateCatalog = {};
    }
    return clothingStateCatalog;
  })();
  await clothingStateLoadingPromise;
  clothingStateLoadingPromise = null;
  return clothingStateCatalog;
}

function getSlotConditions(conditionField) {
  if (!conditionField) return {};
  const raw = state.outfit.conditions?.[conditionField];
  return sanitizeSlotConditions(raw);
}

function setSlotConditionDimension(conditionField, dimension, tagId) {
  if (!conditionField) return;
  if (!state.outfit.conditions) state.outfit.conditions = createDefaultOutfitConditions();
  const slot = { ...getSlotConditions(conditionField) };
  if (tagId) slot[dimension] = tagId;
  else delete slot[dimension];
  state.outfit.conditions[conditionField] = slot;
  notifyStateChange();
}

function applyClothingStatePreset(conditionField, presetConditions = {}) {
  if (!conditionField) return;
  if (!state.outfit.conditions) state.outfit.conditions = createDefaultOutfitConditions();
  const slot = { ...getSlotConditions(conditionField), ...presetConditions };
  state.outfit.conditions[conditionField] = slot;
  notifyStateChange();
}

function clothingStatePresetMatches(conditionField, preset) {
  const slot = getSlotConditions(conditionField);
  return Object.entries(preset.conditions || {}).every(([dim, tagId]) => slot[dim] === tagId);
}

function renderClothingStateQuick(conditionField, garmentId) {
  const root = document.getElementById("clothing-state-quick");
  if (!root) return;
  const presets = window.CLOTHING_STATE_PRESETS || [];
  if (!garmentId || !presets.length) {
    root.innerHTML = "";
    return;
  }
  root.innerHTML = `
    <div class="clothing-state-quick-label">Quick states</div>
    <div class="clothing-state-quick-chips">
      ${presets.map((preset) => {
        const active = clothingStatePresetMatches(conditionField, preset) ? " active" : "";
        return `<button type="button" class="chip clothing-state-preset${active}" data-preset-id="${escapeHtml(preset.id)}" title="${escapeHtml(preset.hint || "")}">${escapeHtml(preset.label)}</button>`;
      }).join("")}
    </div>
  `;
  root.querySelectorAll(".clothing-state-preset").forEach((btn) => {
    btn.onclick = () => {
      const preset = presets.find((row) => row.id === btn.dataset.presetId);
      if (!preset) return;
      applyClothingStatePreset(conditionField, preset.conditions || {});
      renderClothingStatePanel({ conditionField });
    };
  });
}

function renderClothingStateAccordion(conditionField, catalog, garmentId) {
  const root = document.getElementById("clothing-state-accordion");
  if (!root) return;
  if (!garmentId) {
    root.innerHTML = '<div class="tagstudio-output-empty">Select garment first</div>';
    return;
  }
  root.innerHTML = CLOTHING_STATE_DIMENSIONS.map((dimension) => {
    const items = catalog[dimension.id] || [];
    const slot = getSlotConditions(conditionField);
    const selected = slot[dimension.id] || "";
    const selectedCount = selected ? 1 : 0;
    const isOpen = clothingStateOpenSections.has(dimension.id);
    return `
      <section class="accordion-section${isOpen ? " is-open" : ""}" data-dimension="${escapeHtml(dimension.id)}">
        <button type="button" class="accordion-header">
          <span>${escapeHtml(dimension.label)}</span>
          ${selectedCount ? `<span class="accordion-badge">${selectedCount}</span>` : ""}
        </button>
        <div class="accordion-body">
          <div class="chip-panel clothing-state-chips">
            <button type="button" class="chip${selected ? "" : " active"}" data-dimension="${escapeHtml(dimension.id)}" data-tag-id="">— None —</button>
            ${items.map((item) => `<button type="button" class="chip${selected === item.id ? " active" : ""}" data-dimension="${escapeHtml(dimension.id)}" data-tag-id="${escapeHtml(item.id)}">${escapeHtml(item.label)}</button>`).join("")}
          </div>
        </div>
      </section>
    `;
  }).join("");

  root.querySelectorAll(".accordion-header").forEach((btn) => {
    btn.onclick = () => {
      const section = btn.closest(".accordion-section");
      const dimension = section?.dataset.dimension;
      if (!dimension) return;
      if (clothingStateOpenSections.has(dimension)) clothingStateOpenSections.delete(dimension);
      else {
        if (clothingStateOpenSections.size >= 2) {
          const first = clothingStateOpenSections.values().next().value;
          clothingStateOpenSections.delete(first);
        }
        clothingStateOpenSections.add(dimension);
      }
      renderClothingStateAccordion(conditionField, catalog, garmentId);
    };
  });

  root.querySelectorAll(".clothing-state-chips .chip").forEach((chip) => {
    chip.onclick = () => {
      const dimension = chip.dataset.dimension;
      const tagId = chip.dataset.tagId || "";
      setSlotConditionDimension(conditionField, dimension, tagId);
      renderClothingStatePanel({ conditionField });
    };
  });
}

async function renderClothingStatePanel(leaf) {
  const panel = document.getElementById("outfit-condition-panel");
  if (!panel) return;
  const conditionField = leaf?.conditionField;
  if (!conditionField) {
    panel.classList.add("hidden");
    return;
  }
  const catalog = await ensureClothingStateCatalog();
  const garmentId = getGarmentForConditionField(conditionField);
  panel.classList.remove("hidden");
  const title = document.querySelector(".clothing-state-title");
  if (title) title.textContent = CONDITION_FIELD_LABELS[conditionField] || "Clothing states";
  renderClothingStateQuick(conditionField, garmentId);
  renderClothingStateAccordion(conditionField, catalog, garmentId);
  panel.classList.toggle("is-disabled", !garmentId);
}

function clearConditionForField(field) {
  if (!field || !state.outfit.conditions) return;
  state.outfit.conditions[field] = {};
}

function registerCategoryItems(categoryId, items) {
  if (!itemSubgroupMaps[categoryId]) itemSubgroupMaps[categoryId] = {};
  if (!itemLabelCache[categoryId]) itemLabelCache[categoryId] = {};
  for (const item of items) {
    itemLabelCache[categoryId][item.id] = item.label;
    const subcategory = item.meta?.subcategory_id || item.meta?.subgroup;
    if (subcategory) {
      itemSubgroupMaps[categoryId][item.id] = subcategory;
    }
  }
}

function countSingleInSubgroup(categoryId, subgroup, value) {
  if (!value) return 0;
  if (!subgroup) return 1;
  const map = itemSubgroupMaps[categoryId] || {};
  return map[value] === subgroup ? 1 : 0;
}

function countItemsInSubgroup(categoryId, subgroup, values) {
  const map = itemSubgroupMaps[categoryId] || {};
  return values.filter((id) => map[id] === subgroup).length;
}

function sumTreeNodeCount(node) {
  if (!node.children) return getTreeLeafSelectionState(node).count;
  return sumTreeNodeSelectionCount(node);
}

function nodeSelectionScopeKey(node) {
  if (!node) return "";
  return `${node.categoryId || ""}|${node.subgroup || ""}|${node.field || ""}`;
}

function setFieldSelectionMode(scopeKey, mode) {
  if (!scopeKey) return;
  if (mode === "item") fieldSelectionModes.delete(scopeKey);
  else fieldSelectionModes.set(scopeKey, mode);
}

function getFieldSelectionMode(scopeKey, count = 0) {
  const stored = fieldSelectionModes.get(scopeKey);
  if (count > 0) {
    if (stored === "random" || stored === "preset") return stored;
    return "item";
  }
  if (stored) return stored;
  return "none";
}

function resetFieldSelectionModes() {
  fieldSelectionModes.clear();
}

function getStateValueForTreeNode(node) {
  if (!node?.field) return "";
  if (node.field === "makeup") return state.appearance.makeup;
  if (node.field === "accessories") return state.appearance.accessories;
  if (node.field === "tattoos") return state.appearance.tattoos || [];
  if (node.field === "elements" && node.categoryId === "fetish.elements") return state.fetish.elements;
  if (node.categoryId?.startsWith("pose.")) return state.pose || "";
  if (node.field === "hair") return state.appearance.hair || "";
  if (node.field === "hair_color") return state.appearance.hair_color || "";
  if (node.categoryId?.startsWith("style.") && state.style) {
    const value = state.style[node.field];
    return Array.isArray(value) ? value : (value || "");
  }
  if (node.categoryId?.startsWith("lighting.") && state.lighting) return state.lighting[node.field] || "";
  if (node.stateSection === "scene" && state.scene) return state.scene[node.field] || "";
  if (node.field === "modifiers" && state.environment) return state.environment.modifiers;
  if (node.field && state.environment && Object.prototype.hasOwnProperty.call(state.environment, node.field)) {
    const value = state.environment[node.field];
    return Array.isArray(value) ? value : (value || "");
  }
  if (node.categoryId?.startsWith("camera.") && state.camera) return state.camera[node.field] || "";
  if (node.categoryId?.startsWith("face.") && state.face) return state.face[node.field] ?? "";
  if (node.categoryId?.startsWith("character.") && state.character) {
    const value = state.character[node.field];
    return Array.isArray(value) ? value : (value || "");
  }
  if (node.field && Object.prototype.hasOwnProperty.call(state.outfit, node.field)) {
    return state.outfit[node.field] || "";
  }
  return "";
}

function valueMatchesNodeSubgroup(node, value) {
  if (!value) return false;
  if (!node.subgroup) return true;
  const map = itemSubgroupMaps[node.categoryId] || {};
  return map[value] === node.subgroup;
}

function isActiveTreeLeaf(node) {
  if (!node?.id) return false;
  return node.id === activeCharacterLeafId
    || node.id === activeFaceLeafId
    || node.id === activeOutfitLeafId
    || node.id === activeMakeupLeafId
    || node.id === activeAccessoriesLeafId
    || node.id === activePoseLeafId
    || node.id === activeCameraLeafId
    || node.id === activeLightingLeafId
    || node.id === activeEnvironmentLeafId
    || node.id === activeStyleLeafId
    || node.id === activeFetishLeafId;
}

function countScalarForTreeNode(node, value) {
  if (!value) return 0;
  if (!node.subgroup) return 1;
  const map = itemSubgroupMaps[node.categoryId] || {};
  const mapped = map[value];
  if (mapped === node.subgroup) return 1;
  if (mapped && mapped !== node.subgroup) return 0;
  if (isActiveTreeLeaf(node)) return 1;
  return 0;
}

function getTreeLeafSelectionState(node) {
  const scopeKey = nodeSelectionScopeKey(node);
  if (node.presetPanel && node.presetScope) {
    const activeId = getActiveScopePresetId(node.presetScope);
    let count = 0;
    if (node.presetPanel === "builtin" && activeId.startsWith("builtin:")) count = 1;
    if (node.presetPanel === "custom" && activeId.startsWith("user:")) count = 1;
    return { count, mode: count > 0 ? "preset" : "none", scopeKey: node.presetScope };
  }
  if (node.categoryId?.startsWith("style.") && !state.style?.enabled) {
    return { count: 0, mode: "off", scopeKey };
  }
  const value = getStateValueForTreeNode(node);
  let count = 0;
  if (Array.isArray(value)) {
    count = countItemsInSubgroup(node.categoryId, node.subgroup, value);
  } else {
    count = countScalarForTreeNode(node, value);
  }
  if (node.conditionField) {
    const garmentId = getGarmentForConditionField(node.conditionField);
    const slotConditions = state.outfit.conditions?.[node.conditionField];
    if (garmentId && countSlotConditions(slotConditions) && garmentMatchesLeaf(node, garmentId)) {
      count += countSlotConditions(slotConditions);
    }
  }
  const mode = getFieldSelectionMode(scopeKey, count);
  return { count, mode, scopeKey };
}

function applyCountDisplay(el, { count, mode }) {
  if (!el) return;
  el.classList.remove("tree-count-random", "tree-count-off", "tree-count-item", "tree-count-preset");
  const effectiveMode = count > 0 && mode === "off" ? "item" : mode;
  if (effectiveMode === "off") {
    el.textContent = "0";
    el.classList.add("tree-count-off");
    return;
  }
  if (effectiveMode === "preset" && count > 0) {
    el.textContent = String(count);
    el.classList.add("tree-count-preset");
    return;
  }
  if (effectiveMode === "random" && count > 0) {
    el.textContent = String(count);
    el.classList.add("tree-count-random");
    return;
  }
  if (count > 0) {
    el.textContent = String(count);
    el.classList.add("tree-count-item");
    return;
  }
  el.textContent = "";
}

function sumTreeNodeSelectionCount(node) {
  if (!node.children) return getTreeLeafSelectionState(node).count;
  return node.children.reduce((sum, child) => sum + sumTreeNodeSelectionCount(child), 0);
}

function getTreeLeafCount(node) {
  return getTreeLeafSelectionState(node).count;
}

function initNavCounters() {
  document.querySelectorAll(".nav-item[data-tab]").forEach((btn) => {
    const tab = btn.dataset.tab;
    if (!TAB_COUNTS[tab] || btn.querySelector(".nav-count")) return;
    const icon = btn.querySelector(".nav-icon");
    const labelText = Array.from(btn.childNodes)
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent.trim())
      .join(" ")
      .trim();
    btn.textContent = "";
    if (icon) btn.appendChild(icon);
    const label = document.createElement("span");
    label.className = "nav-label";
    label.textContent = labelText;
    const count = document.createElement("span");
    count.className = "nav-count";
    count.dataset.countTab = tab;
    btn.appendChild(label);
    btn.appendChild(count);
  });
}

function updateNavCounters() {
  document.querySelectorAll(".nav-count[data-count-tab]").forEach((el) => {
    const counter = TAB_COUNTS[el.dataset.countTab];
    if (!counter) return;
    const value = counter();
    el.textContent = value > 0 ? String(value) : "";
  });
}

function updateSelectionCounts() {
  selectionCountEls.forEach(({ getVal, el, scopeKey }) => {
    const value = getVal();
    const count = Array.isArray(value) ? value.length : (value ? 1 : 0);
    const mode = getFieldSelectionMode(scopeKey || "", count);
    applyCountDisplay(el, { count, mode });
  });
}

function updateTreeCountsInContainer(nodes, container) {
  if (!container) return;
  function walk(ns) {
    for (const node of ns) {
      if (node.children) {
        const groupEl = container.querySelector(`[data-group-id="${node.id}"]`);
        const countEl = groupEl?.querySelector(".tree-count");
        const count = sumTreeNodeSelectionCount(node);
        if (countEl) applyCountDisplay(countEl, { count, mode: count > 0 ? "item" : "none" });
        walk(node.children);
        continue;
      }
      const btn = container.querySelector(`[data-node-id="${node.id}"]`);
      const countEl = btn?.querySelector(".tree-count");
      applyCountDisplay(countEl, getTreeLeafSelectionState(node));
    }
  }
  walk(nodes);
}

function refreshAllTreeCounts() {
  for (const { getTree, elId } of getTreePanels()) {
    updateTreeCountsInContainer(getTree(), document.getElementById(elId));
  }
}

function renderConflictWarnings(warnings) {
  const root = document.getElementById("conflict-warnings");
  if (!root) return;
  if (!warnings.length) {
    root.innerHTML = "";
    root.classList.add("hidden");
    return;
  }
  root.innerHTML = warnings.map((w) => `<li>${w}</li>`).join("");
  root.classList.remove("hidden");
}

async function refreshConflictWarnings() {
  const requestId = ++conflictPreviewRequest;
  try {
    const payload = buildPayload();
    const result = await api("/conflicts/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (requestId !== conflictPreviewRequest) return;
    renderConflictWarnings(result.warnings || []);
  } catch (_) {
    if (requestId !== conflictPreviewRequest) return;
    renderConflictWarnings([]);
  }
}

function qualityBadgeClass(score) {
  if (score >= 90) return "quality-excellent";
  if (score >= 75) return "quality-good";
  if (score >= 60) return "quality-medium";
  return "quality-poor";
}

function renderQualityScore(data) {
  const panel = document.getElementById("quality-score-panel");
  const badge = document.getElementById("quality-score-badge");
  const line = document.getElementById("quality-score-line");
  const issuesWrap = document.getElementById("quality-issues-wrap");
  const issuesEl = document.getElementById("quality-issues");
  const recsWrap = document.getElementById("quality-recs-wrap");
  const recsEl = document.getElementById("quality-recommendations");
  if (!panel || !badge || !line) return;

  if (!data || typeof data.score !== "number") {
    badge.textContent = "—";
    badge.className = "quality-badge";
    line.textContent = "—";
    issuesWrap?.classList.add("hidden");
    recsWrap?.classList.add("hidden");
    return;
  }

  badge.textContent = `${data.score}/100`;
  badge.className = `quality-badge ${qualityBadgeClass(data.score)}`;
  line.textContent = `Quality Score: ${data.score}/100 (${data.level || "—"})`;

  const issues = data.issues || [];
  if (issuesEl && issuesWrap) {
    if (!issues.length) {
      issuesWrap.classList.add("hidden");
      issuesEl.innerHTML = "";
    } else {
      issuesWrap.classList.remove("hidden");
      issuesEl.innerHTML = issues
        .map((issue) => {
          const label = issue.severity_label || issue.severity || "";
          const suffix = label ? ` (${label})` : "";
          return `<li>${issue.message}${suffix} → ${issue.penalty}</li>`;
        })
        .join("");
    }
  }

  const recs = data.recommendations || [];
  if (recsEl && recsWrap) {
    if (!recs.length) {
      recsWrap.classList.add("hidden");
      recsEl.innerHTML = "";
    } else {
      recsWrap.classList.remove("hidden");
      recsEl.innerHTML = recs.map((rec) => `<li>${rec}</li>`).join("");
    }
  }
}

async function refreshQualityScore() {
  const requestId = ++qualityPreviewRequest;
  try {
    const payload = buildPayload();
    const result = await api("/quality/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (requestId !== qualityPreviewRequest) return;
    renderQualityScore(result);
  } catch (_) {
    if (requestId !== qualityPreviewRequest) return;
    renderQualityScore(null);
  }
}

async function refreshPromptPreview() {
  const requestId = ++promptPreviewRequest;
  try {
    syncStateFromFormControls();
    const result = await api("/generate/preview", {
      method: "POST",
      body: JSON.stringify(buildPayload()),
    });
    if (requestId !== promptPreviewRequest) return;
    document.getElementById("output-positive").value = result.positive;
    document.getElementById("output-negative").value = result.negative || "";
    document.getElementById("output-buckets").textContent = JSON.stringify(result.buckets, null, 2);
    if (result.warnings?.length) renderConflictWarnings(result.warnings);
    if (result.quality_score) renderQualityScore(result.quality_score);
  } catch (_) {
    if (requestId !== promptPreviewRequest) return;
  }
}

function notifyStateChange() {
  // Push undo snapshot before state is externally committed
  _undoPush();
  updateNavCounters();
  updateSelectionCounts();
  refreshAllTreeCounts();
  scheduleSessionPersist();
  clearTimeout(conflictPreviewTimer);
  conflictPreviewTimer = setTimeout(() => {
    refreshConflictWarnings();
    refreshQualityScore();
  }, 250);
  clearTimeout(promptPreviewTimer);
  promptPreviewTimer = setTimeout(refreshPromptPreview, 350);
}

function createDefaultUiState() {
  return {
    activeTab: "style",
    activeCharacterLeafId: "character_age_appearance_ranges",
    activeFaceLeafId: "face_facial_expression_seductive_teasing",
    activeOutfitLeafId: "dress_micro_mini",
    activeMakeupLeafId: "makeup_eyes",
    activeAccessoriesLeafId: "acc_body",
    activePoseLeafId: "pose_standing_seductive",
    activeEnvironmentLeafId: "environment_scene_time",
    activeStyleLeafId: "style_art_style_anime_stylized",
    activeCameraLeafId: "camera_angle_standard_angles",
    activeLightingLeafId: "lighting_light_type_natural",
    activeFetishLeafId: "fetish_bdsm_restraints_items",
  };
}

function applyDefaultUiState() {
  const ui = createDefaultUiState();
  activeCharacterLeafId = ui.activeCharacterLeafId;
  activeFaceLeafId = ui.activeFaceLeafId;
  activeOutfitLeafId = ui.activeOutfitLeafId;
  activeMakeupLeafId = ui.activeMakeupLeafId;
  activeAccessoriesLeafId = ui.activeAccessoriesLeafId;
  activePoseLeafId = ui.activePoseLeafId;
  activeEnvironmentLeafId = ui.activeEnvironmentLeafId;
  activeStyleLeafId = ui.activeStyleLeafId;
  activeCameraLeafId = ui.activeCameraLeafId;
  activeLightingLeafId = ui.activeLightingLeafId;
  activeFetishLeafId = ui.activeFetishLeafId;
  pendingActiveTab = ui.activeTab;
}

function getCurrentTab() {
  return document.querySelector(".nav-item.active")?.dataset.tab || "character";
}

function collectUiState() {
  return {
    activeTab: getCurrentTab(),
    activeCharacterLeafId,
    activeFaceLeafId,
    activeOutfitLeafId,
    activeMakeupLeafId,
    activeAccessoriesLeafId,
    activePoseLeafId,
    activeEnvironmentLeafId,
    activeStyleLeafId,
    activeCameraLeafId,
    activeLightingLeafId,
    activeFetishLeafId,
  };
}

function applyUiState(ui = {}) {
  if (ui.activeFaceLeafId) {
    if (isFaceVibeLeafId(ui.activeFaceLeafId)) {
      activeFaceLeafId = ui.activeFaceLeafId;
    } else if (!ui.activeCharacterLeafId) {
      activeCharacterLeafId = ui.activeFaceLeafId;
    }
  }
  if (ui.activeCharacterLeafId) activeCharacterLeafId = ui.activeCharacterLeafId;
  if (ui.activeHairLeafId && !ui.activeCharacterLeafId) {
    activeCharacterLeafId = ui.activeHairLeafId;
  }
  if (ui.activeOutfitLeafId) activeOutfitLeafId = ui.activeOutfitLeafId;
  if (ui.activeMakeupLeafId) activeMakeupLeafId = ui.activeMakeupLeafId;
  if (ui.activeAccessoriesLeafId) activeAccessoriesLeafId = ui.activeAccessoriesLeafId;
  if (ui.activePoseLeafId) activePoseLeafId = ui.activePoseLeafId;
  if (ui.activeEnvironmentLeafId) activeEnvironmentLeafId = ui.activeEnvironmentLeafId;
  if (ui.activeStyleLeafId) activeStyleLeafId = ui.activeStyleLeafId;
  if (ui.activeCameraLeafId) activeCameraLeafId = ui.activeCameraLeafId;
  if (ui.activeLightingLeafId) activeLightingLeafId = ui.activeLightingLeafId;
  if (ui.activeFetishLeafId) activeFetishLeafId = ui.activeFetishLeafId;
  if (ui.activeTab) pendingActiveTab = normalizeActiveTab(ui.activeTab);
}

function syncStateFromFormControls() {
  state.group_mode = Boolean(document.getElementById("opt-group-mode")?.checked);
}

function syncFormControlsFromState() {
  const groupModeEl = document.getElementById("opt-group-mode");
  if (groupModeEl) groupModeEl.checked = Boolean(state.group_mode);
  const negativeCard = document.getElementById("negative-card");
  if (negativeCard) {
    negativeCard.style.display = state.model_id === "zimage_turbo" ? "none" : "";
  }
  syncQualityBoostersPanel();
}

function restoreOutputs(outputs = {}) {
  const positiveEl = document.getElementById("output-positive");
  const negativeEl = document.getElementById("output-negative");
  const bucketsEl = document.getElementById("output-buckets");
  if (positiveEl && typeof outputs.positive === "string") positiveEl.value = outputs.positive;
  if (negativeEl && typeof outputs.negative === "string") negativeEl.value = outputs.negative;
  if (bucketsEl && outputs.buckets) {
    bucketsEl.textContent = typeof outputs.buckets === "string"
      ? outputs.buckets
      : JSON.stringify(outputs.buckets, null, 2);
  }
}

function collectOutputs() {
  return {
    positive: document.getElementById("output-positive")?.value || "",
    negative: document.getElementById("output-negative")?.value || "",
    buckets: document.getElementById("output-buckets")?.textContent || "",
  };
}

function applyPayloadToState(data) {
  if (!data || typeof data !== "object") return;
  const normalized = sanitizePromptPayload(data);
  state.model_id = normalized.model_id;
  state.style = { ...normalized.style };
  if (!state.style.enabled) {
    state.style.art_style = "";
    state.style.artist_style = "";
    state.style.quality = [];
    state.style.aesthetic = [];
    state.style.technique = [];
  }
  state.character = sanitizeCharacter(normalized.character);
  state.scene = { ...normalized.scene };
  state.environment = {
    location: normalized.environment.location,
    situation: normalized.environment.situation,
    modifiers: [...normalized.environment.modifiers],
  };
  state.outfit = {
    ...normalized.outfit,
    conditions: { ...normalized.outfit.conditions },
  };
  state.appearance = {
    hair: normalized.appearance.hair,
    hair_color: normalized.appearance.hair_color,
    makeup: [...normalized.appearance.makeup],
    accessories: [...normalized.appearance.accessories],
    tattoos: [...(normalized.appearance.tattoos || [])],
  };
  state.face = { ...normalized.face };
  state.camera = { ...normalized.camera };
  state.lighting = { ...normalized.lighting };
  state.pose = normalized.pose;
  state.fetish.elements = [...normalized.fetish.elements];
  state.intensity = normalized.intensity;
  state.lewdness = normalized.lewdness;
  state.detail = normalized.detail;
  state.group_mode = normalized.group_mode;
}

function serializeSession() {
  syncStateFromFormControls();
  return {
    version: SESSION_FILE_VERSION,
    saved_at: new Date().toISOString(),
    ...buildPayload(),
    ui: collectUiState(),
    outputs: collectOutputs(),
  };
}

function persistSession() {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(serializeSession()));
  } catch (_) {
    /* ignore quota / private mode */
  }
}

function scheduleSessionPersist() {
  clearTimeout(sessionPersistTimer);
  sessionPersistTimer = setTimeout(persistSession, 400);
}

function loadPersistedSession() {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (!data.version || data.version < 6) {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      return false;
    }
    if (data.version < SESSION_FILE_VERSION) {
      migrateSessionData(data);
    }
    applyPayloadToState(data);
    if (data.ui) applyUiState(data.ui);
    if (data.outputs) restoreOutputs(data.outputs);
    return true;
  } catch (_) {
    return false;
  }
}

function refreshAllPanels() {
  initCharacterPanel();
  initFacePanel();
  initEnvironmentPanel();
  initStylePanel();
  initOutfitPanel();
  initMakeupPanel();
  initAccessoriesPanel();
  initPosePanel();
  initCameraPanel();
  initLightingPanel();
  initFetishPanel();
  initStaticChips();
}

function applySession(data, options = {}) {
  applyPayloadToState(data);
  if (data.ui) applyUiState(data.ui);
  if (!options.skipOutputs && data.outputs) restoreOutputs(data.outputs);
  if (!options.skipRefresh) {
    refreshAllPanels();
    syncFormControlsFromState();
    if (pendingActiveTab) switchTab(pendingActiveTab);
    notifyStateChange();
  }
}

function resetSession() {
  if (!window.confirm("Сбросить все настройки к значениям по умолчанию?")) return;
  const fresh = createDefaultState();
  for (const key of Object.keys(state)) delete state[key];
  Object.assign(state, fresh);
  applyDefaultUiState();
  restoreOutputs({ positive: "", negative: "", buckets: "{}" });
  refreshAllPanels();
  syncFormControlsFromState();
  switchTab("style");
  persistSession();
  notifyStateChange();
  toast("Настройки сброшены");
}

function downloadSessionFile() {
  syncStateFromFormControls();
  const blob = new Blob([JSON.stringify(serializeSession(), null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `egodary-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
  toast("JSON сохранён");
}

async function handleSessionFileInput(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    applySession(data);
    persistSession();
    toast("Настройки загружены");
  } catch (error) {
    toast(`Ошибка загрузки: ${error.message}`);
  }
  event.target.value = "";
}

async function preloadSubgroupMaps() {
  const categories = [
    "outfit.dress",
    "outfit.top",
    "outfit.bottom",
    "outfit.underwear_layer",
    "outfit.legwear",
    "outfit.jacket",
    "outfit.footwear",
    "outfit.gloves",
    "outfit.cape",
    "appearance.hair",
    "appearance.hair_color",
    "appearance.makeup",
    "appearance.accessories",
    "appearance.tattoos",
    "pose.solo",
    "pose.couple",
    "camera.angle",
    "camera.framing",
    "camera.lens",
    "camera.focus",
    "camera.composition",
    "camera.nsfw_shot",
    "lighting.light_type",
    "lighting.direction",
    "lighting.quality",
    "lighting.color_mood",
    "lighting.nsfw",
    "environment.location",
    "environment.situation",
    "environment.modifiers",
    "scene.time",
    "scene.weather",
    "scene.season",
    "style.art_style",
    "style.artist_style",
    "style.quality",
    "style.aesthetic",
    "style.technique",
    "fetish.elements",
    "character.age_appearance",
    "character.body_type",
    "character.breast_size",
    "character.breast_shape",
    "character.waist",
    "character.hips_ass",
    "character.legs",
    "character.overall_figure",
    "character.height_build",
    "character.ethnicity",
    "character.skin_tone",
    "character.body_details",
    "face.facial_expression",
    "face.mouth_lips",
    "face.eyes",
    "face.eye_color",
    "face.face_shape",
    "face.eyebrows",
    "face.nose",
    "face.jaw_chin",
    "face.age_maturity",
    "face.beauty_archetype",
    "face.facial_details",
  ];
  await Promise.all(
    categories.map(async (categoryId) => {
      try {
        const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
        registerCategoryItems(categoryId, data.items);
      } catch (_) {
        /* category may be unavailable during partial loads */
      }
    }),
  );
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

async function parseApiError(res) {
  const text = await res.text();
  if (!text) return `HTTP ${res.status}`;
  try {
    const parsed = JSON.parse(text);
    if (typeof parsed?.detail === "string") return parsed.detail;
    if (parsed?.detail?.message) return parsed.detail.message;
    return text;
  } catch (_) {
    return text;
  }
}

async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await parseApiError(res));
  return res.json();
}

function getLlmTimeoutMs() {
  const fromCache = Number(llmSettingsCache?.settings?.timeout);
  if (Number.isFinite(fromCache) && fromCache > 0) return fromCache * 1000;
  const fromForm = Number(document.getElementById("llm-timeout")?.value);
  if (Number.isFinite(fromForm) && fromForm > 0) return fromForm * 1000;
  return 30000;
}

function updateLlmProgressUi() {
  const bar = document.getElementById("llm-progress-bar");
  const metaEl = document.getElementById("llm-progress-meta");
  const track = document.querySelector("#llm-progress .llm-progress-track");
  if (!bar || !metaEl) return;
  const elapsed = Date.now() - llmProgressStartedAt;
  const ratio = Math.min(0.92, 0.04 + (elapsed / llmProgressExpectedMs) * 0.88);
  const pct = Math.round(ratio * 100);
  bar.style.width = `${pct}%`;
  if (track) track.setAttribute("aria-valuenow", String(pct));
  const sec = Math.floor(elapsed / 1000);
  const timeoutSec = Math.round(llmProgressExpectedMs / 1000);
  metaEl.textContent = `${sec} с · до ${timeoutSec} с`;
}

function showLlmProgress(label = "Ollama обрабатывает запрос…") {
  llmProgressDepth += 1;
  const root = document.getElementById("llm-progress");
  const bar = document.getElementById("llm-progress-bar");
  const labelEl = document.getElementById("llm-progress-label");
  if (!root || !bar) return;
  if (labelEl) labelEl.textContent = label;
  llmProgressExpectedMs = getLlmTimeoutMs();
  if (llmProgressDepth !== 1) return;
  llmProgressStartedAt = Date.now();
  bar.style.width = "4%";
  root.classList.remove("hidden");
  root.classList.add("show");
  root.setAttribute("aria-busy", "true");
  if (llmProgressTicker) clearInterval(llmProgressTicker);
  llmProgressTicker = setInterval(updateLlmProgressUi, 200);
  updateLlmProgressUi();
}

function hideLlmProgress() {
  if (llmProgressDepth <= 0) return;
  llmProgressDepth -= 1;
  if (llmProgressDepth > 0) return;
  if (llmProgressTicker) {
    clearInterval(llmProgressTicker);
    llmProgressTicker = null;
  }
  const root = document.getElementById("llm-progress");
  const bar = document.getElementById("llm-progress-bar");
  const track = document.querySelector("#llm-progress .llm-progress-track");
  if (bar) bar.style.width = "100%";
  if (track) track.setAttribute("aria-valuenow", "100");
  setTimeout(() => {
    if (llmProgressDepth > 0) return;
    root?.classList.remove("show");
    root?.setAttribute("aria-busy", "false");
    setTimeout(() => {
      root?.classList.add("hidden");
      if (bar) bar.style.width = "0%";
      if (track) track.setAttribute("aria-valuenow", "0");
    }, 220);
  }, 180);
}

async function withLlmProgress(useLlm, label, fn) {
  if (!useLlm) return fn();
  showLlmProgress(label);
  try {
    return await fn();
  } finally {
    hideLlmProgress();
  }
}

function asString(value, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function coerceCharacterScalar(value) {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    const first = value.find((item) => typeof item === "string" && item);
    return first || "";
  }
  return "";
}

function asStringArray(value) {
  return Array.isArray(value) ? value.filter((item) => typeof item === "string" && item) : [];
}

function sanitizeCharacter(char = {}) {
  const defaults = createDefaultCharacter();
  const out = { ...defaults };
  const source = { ...char };
  if (source.thighs && !source.legs) {
    source.legs = source.thighs;
  }
  delete source.thighs;
  for (const key of Object.keys(defaults)) {
    if (key === "body_details") {
      out.body_details = asStringArray(source.body_details).slice(0, 6);
    } else {
      out[key] = coerceCharacterScalar(source[key]);
    }
  }
  return out;
}

function sanitizeStringRecord(record = {}, template = {}) {
  const out = { ...template };
  for (const key of Object.keys(template)) {
    out[key] = asString(record[key]);
  }
  return out;
}

function sanitizePromptPayload(data) {
  const defaults = createDefaultState();
  return {
    model_id: asString(data.model_id, defaults.model_id),
    style: {
      enabled: data.style?.enabled !== false,
      art_style: asString(data.style?.art_style, defaults.style.art_style),
      artist_style: asString(data.style?.artist_style),
      quality: asStringArray(data.style?.quality),
      aesthetic: asStringArray(data.style?.aesthetic),
      technique: asStringArray(data.style?.technique),
      quality_boosters_enabled: data.style?.quality_boosters_enabled !== false,
      quality_boosters_level: normalizeQualityBoosterLevel(data.style?.quality_boosters_level),
    },
    character: sanitizeCharacter(data.character),
    outfit: {
      ...sanitizeStringRecord(data.outfit, defaults.outfit),
      conditions: sanitizeOutfitConditions(data.outfit?.conditions, defaults.outfit.conditions),
    },
    appearance: {
      hair: asString(data.appearance?.hair),
      hair_color: asString(data.appearance?.hair_color),
      makeup: asStringArray(data.appearance?.makeup),
      accessories: asStringArray(data.appearance?.accessories),
      tattoos: asStringArray(data.appearance?.tattoos),
    },
    face: sanitizeStringRecord(data.face, defaults.face),
    scene: sanitizeStringRecord(data.scene, defaults.scene),
    environment: {
      location: asString(data.environment?.location),
      situation: asString(data.environment?.situation),
      modifiers: asStringArray(data.environment?.modifiers),
    },
    pose: asString(data.pose),
    camera: sanitizeStringRecord(data.camera, defaults.camera),
    lighting: sanitizeStringRecord(data.lighting, defaults.lighting),
    fetish: { elements: asStringArray(data.fetish?.elements) },
    intensity: Number.isFinite(data.intensity) ? data.intensity : defaults.intensity,
    lewdness: Number.isFinite(data.lewdness) ? data.lewdness : defaults.lewdness,
    detail: Number.isFinite(data.detail) ? data.detail : defaults.detail,
    group_mode: Boolean(data.group_mode),
  };
}

function buildPayload() {
  return sanitizePromptPayload({
    model_id: state.model_id,
    style: state.style,
    character: state.character,
    outfit: state.outfit,
    appearance: state.appearance,
    face: state.face,
    scene: state.scene,
    environment: state.environment,
    pose: state.pose,
    camera: state.camera,
    lighting: state.lighting,
    fetish: state.fetish,
    intensity: state.intensity,
    lewdness: state.lewdness,
    detail: state.detail,
    group_mode: state.group_mode,
  });
}

function renderChips(container, items, selected, onSelect, opts = {}) {
  const { showControls = true, offValue = "", selectionScope = "", categoryId = "" } = opts;
  container.innerHTML = "";

  const row = document.createElement("div");
  row.className = "chip-row";

  const setActive = (selectedId, mode = "item") => {
    container.querySelectorAll(".chip").forEach((el) => {
      if (el.classList.contains("chip-off")) {
        el.classList.toggle("active", mode === "off");
      } else if (el.classList.contains("chip-random")) {
        el.classList.toggle("active", mode === "random");
      } else {
        const isSelected = (el.dataset.id || "") === selectedId;
        el.classList.toggle("active", isSelected && (mode === "item" || mode === "random"));
      }
    });
  };

  const storedMode = selectionScope ? fieldSelectionModes.get(selectionScope) : null;
  const initialMode = storedMode || (selected === offValue || !selected ? "off" : "item");

  if (showControls) {
    const controls = document.createElement("div");
    controls.className = "chip-controls";

    const offBtn = document.createElement("button");
    offBtn.type = "button";
    offBtn.className = "chip chip-off" + (initialMode === "off" ? " active" : "");
    offBtn.textContent = "Off";
    offBtn.onclick = () => {
      onSelect(offValue);
      setFieldSelectionMode(selectionScope, "off");
      setActive(offValue, "off");
      notifyStateChange();
    };
    controls.appendChild(offBtn);

    const randBtn = document.createElement("button");
    randBtn.type = "button";
    randBtn.className = "chip chip-random" + (initialMode === "random" ? " active" : "");
    randBtn.textContent = "Random";
    randBtn.onclick = () => {
      const pickable = randomizableItems(items);
      if (!pickable.length) return;
      const pick = pickable[Math.floor(Math.random() * pickable.length)];
      onSelect(pick.id);
      setFieldSelectionMode(selectionScope, "random");
      setActive(pick.id, "random");
      notifyStateChange();
    };
    controls.appendChild(randBtn);

    container.appendChild(controls);
  }

  for (const item of items) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = chipItemClass(item, selected === item.id && initialMode !== "off");
    chip.textContent = item.label;
    chip.title = formatItemTooltip(item, categoryId);
    chip.dataset.id = item.id;
    chip.onclick = () => {
      onSelect(item.id);
      setFieldSelectionMode(selectionScope, "item");
      setActive(item.id, "item");
      notifyStateChange();
    };
    row.appendChild(chip);
  }

  container.appendChild(row);

  if (showControls) {
    setActive(selected, initialMode);
  }
}

function filterItemsBySubgroup(items, subgroup) {
  return items.filter(
    (item) => {
      const subcategory = item.meta?.subcategory_id || item.meta?.subgroup;
      return subcategory === subgroup || subcategory === "none";
    },
  );
}

function sortNoneFirst(items) {
  const none = items.filter((item) => item.id === "none");
  const rest = items.filter((item) => item.id !== "none");
  return [...none, ...rest];
}

function randomizableItems(items) {
  return items.filter((item) => item.id !== "none");
}

function chipItemClass(item, isActive) {
  let cls = "chip";
  if (item.id === "none") cls += " chip-none";
  if (isActive) cls += " active";
  return cls;
}

function formatItemTooltip(item, categoryId = "") {
  const ruMap = window.TAG_TOOLTIPS_RU || {};
  const ru = item.meta?.label_ru
    || item.meta?.tooltip_ru
    || ruMap[`${categoryId}:${item.id}`]
    || ruMap[item.id]
    || item.label;
  const modelId = state?.model_id || "illustrious";
  const tag = item.tags?.[modelId] || item.tags?.illustrious || "";
  const lines = [ru];
  if (tag) lines.push(`Тег: ${tag}`);
  return lines.join("\n");
}

function subgroupScopeIds(items) {
  return new Set(items.map((item) => item.id));
}

function buildSubgroupScopeIds(categoryId, subgroup, items) {
  const scopeIds = new Set();
  const map = itemSubgroupMaps[categoryId] || {};
  for (const [id, sg] of Object.entries(map)) {
    if (sg === subgroup) scopeIds.add(id);
  }
  for (const item of items) {
    scopeIds.add(item.id);
  }
  return scopeIds;
}

function applyImportTouched(imported, touched) {
  resetFieldSelectionModes();
  for (const path of touched) {
    if (path === "pose") {
      state.pose = imported.pose || "";
      continue;
    }
    if (path === "group_mode") {
      state.group_mode = Boolean(imported.group_mode);
      continue;
    }
    if (path === "style.enabled") {
      state.style.enabled = imported.style?.enabled !== false;
      continue;
    }
    if (path === "character.age_appearance" && imported.character?.age_appearance) {
      state.character.age_appearance = imported.character.age_appearance;
      continue;
    }
    const dot = path.indexOf(".");
    if (dot === -1) continue;
    const section = path.slice(0, dot);
    const field = path.slice(dot + 1);
    const sectionData = imported[section];
    if (!sectionData || !Object.prototype.hasOwnProperty.call(state[section], field)) continue;
    const value = sectionData[field];
    if (Array.isArray(state[section][field])) {
      state[section][field] = Array.isArray(value) ? [...value] : [];
    } else {
      state[section][field] = value ?? "";
    }
  }
}

function renderImportReport(report) {
  const panel = document.getElementById("import-report");
  const stats = document.getElementById("import-report-stats");
  const matchedList = document.getElementById("import-matched-list");
  const unknownList = document.getElementById("import-unknown-list");
  if (!panel || !stats || !matchedList || !unknownList) return;

  if (!report) {
    panel.classList.add("hidden");
    return;
  }

  const matched = report.matched || [];
  const unknown = report.unknown || [];
  stats.textContent = `Распознано: ${report.matched_count ?? matched.length} · Неизвестно: ${report.unknown_count ?? unknown.length}`;
  matchedList.innerHTML = matched.length
    ? matched.map((m) => `<li><span class="import-tag">${m.label}</span> <span class="import-meta">${m.field_path} · «${m.matched_phrase}»</span></li>`).join("")
    : "<li class='import-empty'>—</li>";
  unknownList.innerHTML = unknown.length
    ? unknown.map((t) => `<li>${t}</li>`).join("")
    : "<li class='import-empty'>—</li>";
  panel.classList.remove("hidden");
}

function clearGeneratedOutput() {
  const pos = document.getElementById("output-positive");
  const neg = document.getElementById("output-negative");
  const buckets = document.getElementById("output-buckets");
  if (pos) pos.value = "";
  if (neg) neg.value = "";
  if (buckets) buckets.textContent = "{}";
}

function wrapGetValForSubgroup(getVal, scopeIds, offValue = "") {
  return () => {
    const value = getVal();
    if (Array.isArray(value)) {
      return value.filter((id) => scopeIds.has(id));
    }
    return scopeIds.has(value) ? value : offValue;
  };
}

function wrapSetValForSubgroup(getVal, setVal, scopeIds, offValue = "") {
  return (value) => {
    const current = getVal();
    if (Array.isArray(value)) {
      const kept = Array.isArray(current) ? current.filter((id) => !scopeIds.has(id)) : [];
      setVal([...kept, ...value]);
      return;
    }
    if (!value || value === offValue) {
      if (Array.isArray(current)) {
        setVal(current.filter((id) => !scopeIds.has(id)));
      } else if (scopeIds.has(current)) {
        setVal(offValue);
      }
      return;
    }
    setVal(value);
  };
}

// ---------------------------------------------------------------------------
// Wildcards section — shown inline inside every subgroup panel, listing the
// custom tags a user uploaded for the panel's parent category (via the
// Wildcards tab). Shown regardless of whether the wildcard's target_subgroup
// matches this particular leaf's subgroup id, since users often type a free
// subgroup name that doesn't correspond to any built-in UI subgroup — without
// this section those tags would never be visible anywhere. Hidden entirely
// when the source wildcard (or all of its lines) is disabled.
const wildcardsByCategoryCache = new Map();

async function invalidateWildcardsByCategoryCache() {
  wildcardsByCategoryCache.clear();
  await loadWildcardsIndex();
  refreshAllPanels();
}

// Synchronous index used while building category trees (getCharacterTree(),
// getOutfitTree(), ...) — these are plain sync functions called throughout
// the app, so wildcard data has to already be in memory by the time they
// run rather than fetched on demand. Built once at startup (see init()) and
// refreshed whenever wildcards are uploaded/toggled/deleted.
let wildcardsIndexByCategory = {};

async function loadWildcardsIndex() {
  try {
    const data = await api("/wildcards");
    const idx = {};
    for (const w of data.wildcards || []) {
      if (!w.enabled || !w.item_count) continue;
      if (!idx[w.target_category]) idx[w.target_category] = [];
      idx[w.target_category].push({
        subgroup: w.target_subgroup,
        label: w.label || w.filename,
        count: w.item_count,
      });
    }
    wildcardsIndexByCategory = idx;
  } catch (e) {
    wildcardsIndexByCategory = {};
  }
}

// Appends a dedicated tree leaf for every wildcard target_subgroup that isn't
// already one of a category's built-in subgroups — e.g. uploading a wildcard
// to appearance.hair / "imported" gets its own "🧩 ..." leaf next to Long
// Styles / Updos & Buns / etc., instead of only being reachable as extra
// chips bolted onto every existing subgroup. Field/multi/conditionField are
// copied from a sibling leaf of the same categoryId so the new leaf reads
// and writes the same state slot as its neighbors.
// Turns a subgroup id into a readable label for the dynamic tree leaf:
// "sexy_outfit" -> "Sexy Outfit". Text the user already typed with normal
// spacing/casing (e.g. "Sexy outfit") passes through essentially unchanged
// (only stray underscores get converted, since a typed subgroup name could
// still contain one).
function humanizeWildcardSubgroupLabel(subgroup) {
  return String(subgroup || "")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function injectWildcardLeaves(nodes) {
  if (!Array.isArray(nodes) || !nodes.length) return nodes;
  return nodes.map((node) => {
    if (!Array.isArray(node.children) || !node.children.length) return node;

    // Recurse first so nested sub-groups (e.g. Accessories > Tattoos & Body
    // Art) get their own orphan wildcard leaves too.
    const children = injectWildcardLeaves(node.children);

    // Bucket this group's own direct leaves (not nested sub-groups) by
    // categoryId — a group can mix more than one category, e.g. Hair +
    // Hair Color both live under the single "Hair" header.
    const byCategory = new Map();
    for (const child of children) {
      if (Array.isArray(child.children) && child.children.length) continue;
      if (!child.categoryId) continue;
      if (!byCategory.has(child.categoryId)) {
        byCategory.set(child.categoryId, { template: child, knownSubgroups: new Set() });
      }
      if (child.subgroup) byCategory.get(child.categoryId).knownSubgroups.add(child.subgroup);
    }

    const extraLeaves = [];
    for (const [categoryId, { template, knownSubgroups }] of byCategory) {
      const wcGroups = wildcardsIndexByCategory[categoryId];
      if (!wcGroups || !wcGroups.length) continue;
      const seen = new Set();
      for (const wc of wcGroups) {
        if (!wc.subgroup || knownSubgroups.has(wc.subgroup) || seen.has(wc.subgroup)) continue;
        seen.add(wc.subgroup);
        extraLeaves.push({
          id: `wc_${categoryId}_${wc.subgroup}`,
          // Label the leaf by the subgroup name the user typed (e.g. "Sexy
          // outfit"), not by the source file's label/filename — the
          // subgroup is the thing distinguishing this leaf from others, and
          // it's also ambiguous which file "wins" the label when several
          // files share one subgroup. The file name is still shown per-file
          // in the Wildcards tab list and in the inline "🧩 Wildcards"
          // section underneath OTHER (non-matching) subgroups, where
          // telling files apart actually matters.
          label: `🧩 ${humanizeWildcardSubgroupLabel(wc.subgroup)}`,
          categoryId,
          subgroup: wc.subgroup,
          field: template.field,
          multi: template.multi,
          conditionField: template.conditionField,
          isWildcardLeaf: true,
        });
      }
    }

    if (!extraLeaves.length && children === node.children) return node;
    return { ...node, children: [...children, ...extraLeaves] };
  });
}

async function fetchWildcardsForCategory(categoryId) {
  if (!categoryId) return [];
  if (!wildcardsByCategoryCache.has(categoryId)) {
    wildcardsByCategoryCache.set(
      categoryId,
      api(`/wildcards/by-category/${encodeURIComponent(categoryId)}`)
        .then((data) => data.wildcards || [])
        .catch(() => []),
    );
  }
  try {
    return await wildcardsByCategoryCache.get(categoryId);
  } catch (e) {
    return [];
  }
}

function wildcardChipIsSelected(getVal, isMulti, id) {
  const v = getVal();
  if (isMulti) return asStringArray(v).includes(id);
  return Array.isArray(v) ? v.includes(id) : v === id;
}

async function appendWildcardsSection(container, categoryId, getVal, setVal, isMulti = false, currentSubgroup = null) {
  if (!container || !categoryId || typeof getVal !== "function" || typeof setVal !== "function") return;
  const token = `${categoryId}#${Math.random()}`;
  container.dataset.wcToken = token;
  let groups = await fetchWildcardsForCategory(categoryId);
  // The user may have switched to a different leaf while this was in flight —
  // bail out so we don't append a stale section onto the wrong panel.
  if (container.dataset.wcToken !== token) return;
  // A wildcard whose target_subgroup matches the leaf we're already on gets
  // its own dedicated tree leaf (see injectWildcardLeaves) and is already
  // showing as regular, first-class chips above — don't repeat it here.
  groups = groups.filter((g) => g.target_subgroup !== currentSubgroup);
  if (!groups.length) return;

  const section = document.createElement("div");
  section.className = "wildcards-section";

  const title = document.createElement("div");
  title.className = "wildcards-section-title";
  title.textContent = "🧩 Wildcards";
  section.appendChild(title);

  const refreshActive = () => {
    section.querySelectorAll(".wildcard-chip").forEach((el) => {
      el.classList.toggle("active", wildcardChipIsSelected(getVal, isMulti, el.dataset.id));
    });
  };

  const toggle = (id) => {
    if (isMulti) {
      const set = new Set(asStringArray(getVal()));
      if (set.has(id)) set.delete(id);
      else set.add(id);
      setVal([...set]);
    } else {
      // Mirrors renderChips' single-select chips: clicking always selects
      // this tag (use the field's own "Off" control above to clear it).
      setVal(id);
    }
    notifyStateChange();
    refreshActive();
  };

  for (const group of groups) {
    const groupEl = document.createElement("div");
    groupEl.className = "wildcards-group";

    const groupTitle = document.createElement("div");
    groupTitle.className = "wildcards-group-title";
    groupTitle.innerHTML = `${escapeHtml(group.label)} <span class="wildcards-group-count">${group.items.length}</span>`;
    groupEl.appendChild(groupTitle);

    const chipsRow = document.createElement("div");
    chipsRow.className = "wildcards-group-chips";
    for (const it of group.items) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = chipItemClass({ id: it.item_id }, wildcardChipIsSelected(getVal, isMulti, it.item_id)) + " wildcard-chip";
      chip.textContent = it.label;
      chip.title = it.label;
      chip.dataset.id = it.item_id;
      chip.onclick = () => toggle(it.item_id);
      chipsRow.appendChild(chip);
    }
    groupEl.appendChild(chipsRow);
    section.appendChild(groupEl);
  }

  container.appendChild(section);
}

async function loadCategoryChips(container, categoryId, getVal, setVal, opts = {}) {
  if (!container) return;
  const { subgroup = null, selectionScope = "", ...chipOpts } = opts;
  const offValue = chipOpts.offValue ?? "";
  const scopeKey = selectionScope || `${categoryId}|${subgroup || ""}`;
  try {
    const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
    registerCategoryItems(categoryId, data.items);
    let items = data.items;
    if (subgroup) {
      items = filterItemsBySubgroup(items, subgroup);
    }
    items = sortNoneFirst(items);
    let effectiveGet = getVal;
    let effectiveSet = setVal;
    if (subgroup) {
      const scopeIds = buildSubgroupScopeIds(categoryId, subgroup, items);
      effectiveGet = wrapGetValForSubgroup(getVal, scopeIds, offValue);
      effectiveSet = wrapSetValForSubgroup(getVal, setVal, scopeIds, offValue);
    }
    renderChips(container, items, effectiveGet(), (v) => effectiveSet(v), {
      ...chipOpts,
      offValue,
      selectionScope: scopeKey,
      categoryId,
    });
    if (subgroup) await appendWildcardsSection(container, categoryId, getVal, setVal, false, subgroup);
  } catch (e) {
    container.innerHTML = `<span style="color:#eb3b5a;font-size:12px">${categoryId}: not loaded</span>`;
  }
}

function renderMultiChips(container, items, selectedIds, onChange, opts = {}) {
  const { max = 4, randomCount = 2, selectionScope = "", categoryId = "" } = opts;
  container.innerHTML = "";
  let current = [...selectedIds];
  const storedMode = selectionScope ? fieldSelectionModes.get(selectionScope) : null;
  const initialMode = storedMode || (current.length ? "item" : "off");

  const syncActive = (mode, ids = current) => {
    container.querySelectorAll(".chip").forEach((el) => {
      if (el.classList.contains("chip-off")) {
        el.classList.toggle("active", mode === "off");
      } else if (el.classList.contains("chip-random")) {
        el.classList.toggle("active", mode === "random");
      } else {
        el.classList.toggle("active", ids.includes(el.dataset.id));
      }
    });
  };

  const controls = document.createElement("div");
  controls.className = "chip-controls";

  const offBtn = document.createElement("button");
  offBtn.type = "button";
  offBtn.className = "chip chip-off" + (initialMode === "off" ? " active" : "");
  offBtn.textContent = "Off";
  offBtn.onclick = () => {
    current = [];
    onChange(current);
    setFieldSelectionMode(selectionScope, "off");
    syncActive("off");
    notifyStateChange();
  };
  controls.appendChild(offBtn);

  const randBtn = document.createElement("button");
  randBtn.type = "button";
  randBtn.className = "chip chip-random" + (initialMode === "random" ? " active" : "");
  randBtn.textContent = "Random";
  randBtn.onclick = () => {
    const pickable = randomizableItems(items);
    if (!pickable.length) return;
    const shuffled = [...pickable].sort(() => Math.random() - 0.5);
    current = shuffled.slice(0, Math.min(randomCount, max, pickable.length)).map((i) => i.id);
    onChange(current);
    setFieldSelectionMode(selectionScope, "random");
    syncActive("random", current);
    notifyStateChange();
  };
  controls.appendChild(randBtn);
  container.appendChild(controls);

  const row = document.createElement("div");
  row.className = "chip-row";
  for (const item of items) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = chipItemClass(item, current.includes(item.id));
    chip.textContent = item.label;
    chip.title = formatItemTooltip(item, categoryId);
    chip.dataset.id = item.id;
    chip.onclick = () => {
      const next = new Set(current);
      if (next.has(item.id)) next.delete(item.id);
      else if (next.size < max) next.add(item.id);
      else return toast(`Max ${max} items`);
      current = [...next];
      onChange(current);
      setFieldSelectionMode(selectionScope, current.length ? "item" : "off");
      syncActive(current.length ? "item" : "off", current);
      notifyStateChange();
    };
    row.appendChild(chip);
  }
  container.appendChild(row);
  syncActive(initialMode, current);
}

async function loadCategoryMultiChips(container, categoryId, getVal, setVal, opts = {}) {
  if (!container) return;
  const { subgroup = null, selectionScope = "", ...chipOpts } = opts;
  const scopeKey = selectionScope || `${categoryId}|${subgroup || ""}`;
  try {
    const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
    registerCategoryItems(categoryId, data.items);
    let items = data.items;
    if (subgroup) {
      items = filterItemsBySubgroup(items, subgroup);
    }
    items = sortNoneFirst(items);
    let effectiveGet = getVal;
    let effectiveSet = setVal;
    if (subgroup) {
      const scopeIds = buildSubgroupScopeIds(categoryId, subgroup, items);
      effectiveGet = wrapGetValForSubgroup(getVal, scopeIds);
      effectiveSet = wrapSetValForSubgroup(getVal, setVal, scopeIds);
    }
    let selected = effectiveGet();
    if (!Array.isArray(selected)) selected = selected ? [selected] : [];
    renderMultiChips(container, items, selected, (v) => effectiveSet(v), {
      ...chipOpts,
      selectionScope: scopeKey,
      categoryId,
    });
    if (subgroup) await appendWildcardsSection(container, categoryId, getVal, setVal, true, subgroup);
  } catch (e) {
    container.innerHTML = `<span style="color:#eb3b5a;font-size:12px">${categoryId}: not loaded</span>`;
  }
}

function makeCategoryCard(title, categoryId, getVal, setVal) {
  const card = document.createElement("div");
  card.className = "card";
  const titleRow = document.createElement("div");
  titleRow.className = "card-title";
  titleRow.append(document.createTextNode(title));
  const countEl = document.createElement("span");
  countEl.className = "selection-count";
  titleRow.appendChild(countEl);
  selectionCountEls.set(categoryId, { getVal, el: countEl });
  card.appendChild(titleRow);
  const panel = document.createElement("div");
  panel.className = "chip-panel";
  panel.id = `chips-${categoryId.replace(/\./g, "-")}`;
  card.appendChild(panel);
  const container = panel;
  const wrappedSetVal = (v) => {
    setVal(v);
    notifyStateChange();
  };
  setTimeout(() => loadCategoryChips(container, categoryId, getVal, wrappedSetVal), 0);
  return card;
}


let activeEnvironmentLeafId = "environment_scene_time";
let refreshEnvironmentPanel = () => {};

function getEnvironmentLeafValue(leaf) {
  if (leaf.stateSection === "scene") return state.scene[leaf.field] || "";
  if (leaf.field === "modifiers") return state.environment.modifiers;
  return state.environment[leaf.field] || "";
}

function setEnvironmentLeafValue(leaf, value) {
  if (leaf.stateSection === "scene") {
    state.scene[leaf.field] = value;
    return;
  }
  if (leaf.field === "modifiers") {
    state.environment.modifiers = value;
    return;
  }
  state.environment[leaf.field] = value;
}

function initEnvironmentPanel() {
  const tree = getEnvironmentTree();
  if (!tree.length) {
    const chips = document.getElementById("environment-chips");
    if (chips) {
      chips.innerHTML = '<span style="color:#eb3b5a;font-size:12px">Environment catalog not loaded (environment-tree-data.js)</span>';
    }
    return;
  }

  const selectLeaf = (leaf) => {
    if (!leaf) return;
    if (leaf.presetPanel && leaf.presetScope) {
      activeEnvironmentLeafId = leaf.id;
      const treeEl = document.getElementById("environment-tree");
      treeEl.innerHTML = "";
      renderCategoryTree(tree, treeEl, activeEnvironmentLeafId, selectLeaf);
      showScopePresetLeaf(
        leaf.presetScope,
        leaf,
        document.getElementById("environment-chips"),
        document.getElementById("environment-detail-title"),
        null,
      );
      return;
    }
    activeEnvironmentLeafId = leaf.id;
    const isMulti = Boolean(leaf.multi);
    const detailSelectionKey = "environment-tree-detail";
    if (isMulti) {
      setDetailTitleWithSelectionCount(
        "environment-detail-title",
        leaf.label,
        detailSelectionKey,
        () => {
          const values = getEnvironmentLeafValue(leaf);
          if (!leaf.subgroup || !Array.isArray(values)) return values;
          const map = itemSubgroupMaps[leaf.categoryId] || {};
          return values.filter((id) => map[id] === leaf.subgroup);
        },
        nodeSelectionScopeKey(leaf),
        addTagContextFromLeaf(leaf),
      );
      updateSelectionCounts();
    } else {
      selectionCountEls.delete(detailSelectionKey);
      setDetailTitleWithSelectionCount(
        "environment-detail-title",
        leaf.label,
        detailSelectionKey,
        () => {
          const value = getEnvironmentLeafValue(leaf);
          if (Array.isArray(value)) return value;
          return valueMatchesNodeSubgroup(leaf, value) ? value : "";
        },
        nodeSelectionScopeKey(leaf),
        addTagContextFromLeaf(leaf),
      );
      updateSelectionCounts();
    }
    const treeEl = document.getElementById("environment-tree");
    treeEl.innerHTML = "";
    renderCategoryTree(tree, treeEl, activeEnvironmentLeafId, selectLeaf);

    const container = document.getElementById("environment-chips");
    container.className = "chip-panel";
    const opts = leaf.subgroup ? { subgroup: leaf.subgroup } : {};
    if (isMulti) {
      loadCategoryMultiChips(
        container,
        leaf.categoryId,
        () => getEnvironmentLeafValue(leaf),
        (v) => {
          setEnvironmentLeafValue(leaf, v);
          clearActiveScopePreset("environment");
          notifyStateChange();
        },
        {
          max: 2,
          randomCount: 1,
          ...opts,
          selectionScope: nodeSelectionScopeKey(leaf),
          categoryId: leaf.categoryId,
        },
      );
    } else {
      loadCategoryChips(
        container,
        leaf.categoryId,
        () => getEnvironmentLeafValue(leaf),
        (v) => {
          setEnvironmentLeafValue(leaf, v);
          clearActiveScopePreset("environment");
          notifyStateChange();
        },
        {
          ...opts,
          selectionScope: nodeSelectionScopeKey(leaf),
          categoryId: leaf.categoryId,
        },
      );
    }
  };

  refreshEnvironmentPanel = () => {
    selectLeaf(findTreeLeaf(activeEnvironmentLeafId, getEnvironmentTree()) || getEnvironmentTree()[0]?.children?.[0]);
  };
  refreshEnvironmentPanel();
}

let activeStyleLeafId = "style_art_style_anime_stylized";
let refreshStylePanel = () => {};

const STYLE_MULTI_LIMITS = {
  quality: { max: 8, randomCount: 2 },
  aesthetic: { max: 56, randomCount: 1 },
  technique: { max: 6, randomCount: 2 },
};

const QUALITY_BOOSTER_LEVELS = [
  {
    id: "low",
    label: "Low",
    tags: "score_7_up",
    description: "Минимальный уровень качества",
  },
  {
    id: "medium",
    label: "Medium",
    tags: "score_8_up, score_7_up",
    description: "Хороший баланс качества",
  },
  {
    id: "high",
    label: "High",
    tags: "score_9, score_8_up, score_7_up",
    description: "Рекомендуется для Anima",
    recommended: true,
  },
];

function normalizeQualityBoosterLevel(level) {
  const value = String(level || "high").toLowerCase();
  return QUALITY_BOOSTER_LEVELS.some((item) => item.id === value) ? value : "high";
}

function syncQualityBoostersPanel() {
  const levelsWrap = document.getElementById("quality-boosters-levels");
  const warning = document.getElementById("quality-boosters-off-warning");
  const tip = document.getElementById("quality-boosters-tip");
  const enabled = state.style.quality_boosters_enabled !== false;
  const level = normalizeQualityBoosterLevel(state.style.quality_boosters_level);

  if (levelsWrap) {
    levelsWrap.classList.toggle("disabled", !enabled);
    levelsWrap.querySelectorAll(".quality-booster-option").forEach((option) => {
      const input = option.querySelector('input[type="radio"]');
      const isActive = enabled && input?.value === level;
      option.classList.toggle("active", isActive);
      if (input) input.checked = isActive;
    });
  }
  if (warning) warning.classList.toggle("hidden", enabled);
  if (tip) {
    tip.textContent = state.model_id === "anima"
      ? "Рекомендуется оставлять на High для лучшего качества генерации у Anima."
      : "Score-теги применяются только при генерации для Anima.";
  }
}

function initQualityBoostersPanel() {
  renderChips(
    document.getElementById("quality-boosters-enabled-chips"),
    [
      { id: "on", label: "On" },
      { id: "off", label: "Off" },
    ],
    state.style.quality_boosters_enabled !== false ? "on" : "off",
    (value) => {
      state.style.quality_boosters_enabled = value === "on";
      if (state.style.quality_boosters_enabled && !state.style.quality_boosters_level) {
        state.style.quality_boosters_level = "high";
      }
      syncQualityBoostersPanel();
      notifyStateChange();
    },
    { showControls: false },
  );

  const levelsWrap = document.getElementById("quality-boosters-levels");
  if (!levelsWrap) return;
  levelsWrap.innerHTML = "";
  const groupName = "quality-boosters-level";

  for (const level of QUALITY_BOOSTER_LEVELS) {
    const label = document.createElement("label");
    label.className = "quality-booster-option";
    label.innerHTML = `
      <input type="radio" name="${groupName}" value="${level.id}" />
      <span class="quality-booster-option-body">
        <span class="quality-booster-option-title">
          <span>${level.label}</span>
          ${level.recommended ? '<span class="quality-booster-badge">recommended</span>' : ""}
        </span>
        <span class="quality-booster-option-tags">${level.tags}</span>
        <span class="quality-booster-option-tags">${level.description}</span>
      </span>
    `;
    label.querySelector('input[type="radio"]')?.addEventListener("change", () => {
      state.style.quality_boosters_level = level.id;
      syncQualityBoostersPanel();
      notifyStateChange();
    });
    levelsWrap.appendChild(label);
  }

  syncQualityBoostersPanel();
}

function syncStylePanelVisibility() {
  const content = document.getElementById("style-content");
  if (content) content.classList.toggle("hidden", !state.style.enabled);
}

function initStyleEnabledChips() {
  renderChips(
    document.getElementById("style-enabled-chips"),
    [
      { id: "on", label: "On" },
      { id: "off", label: "Off" },
    ],
    state.style.enabled ? "on" : "off",
    (v) => {
      state.style.enabled = v === "on";
      if (!state.style.enabled) {
        state.style.art_style = "";
        state.style.artist_style = "";
        state.style.quality = [];
        state.style.aesthetic = [];
        state.style.technique = [];
      } else if (!state.style.art_style) {
        state.style.art_style = "anime_style";
      }
      syncStylePanelVisibility();
      refreshStylePanel();
      refreshAllTreeCounts();
      notifyStateChange();
    },
    { showControls: false },
  );
  syncStylePanelVisibility();
}

function initStylePanel() {
  initStyleEnabledChips();
  initQualityBoostersPanel();
  const tree = getStyleTree();
  if (!tree.length) {
    const chips = document.getElementById("style-chips");
    if (chips) {
      chips.innerHTML = '<span style="color:#eb3b5a;font-size:12px">Style catalog not loaded (style-tree-data.js)</span>';
    }
    return;
  }

  const selectLeaf = (leaf) => {
    if (!leaf) return;
    if (leaf.presetPanel && leaf.presetScope) {
      activeStyleLeafId = leaf.id;
      const treeEl = document.getElementById("style-tree");
      treeEl.innerHTML = "";
      renderCategoryTree(tree, treeEl, activeStyleLeafId, selectLeaf);
      const container = document.getElementById("style-chips");
      showScopePresetLeaf(
        leaf.presetScope,
        leaf,
        container,
        document.getElementById("style-detail-title"),
        null,
      );
      return;
    }
    if (!state.style.enabled) return;
    activeStyleLeafId = leaf.id;
    const isMulti = Boolean(leaf.multi);
    const detailSelectionKey = "style-tree-detail";
    if (isMulti) {
      setDetailTitleWithSelectionCount(
        "style-detail-title",
        leaf.label,
        detailSelectionKey,
        () => {
          const values = state.style[leaf.field] || [];
          if (!leaf.subgroup) return values;
          const map = itemSubgroupMaps[leaf.categoryId] || {};
          return values.filter((id) => map[id] === leaf.subgroup);
        },
        nodeSelectionScopeKey(leaf),
        addTagContextFromLeaf(leaf),
      );
      updateSelectionCounts();
    } else {
      selectionCountEls.delete(detailSelectionKey);
      setDetailTitleWithSelectionCount(
        "style-detail-title",
        leaf.label,
        detailSelectionKey,
        () => {
          const value = state.style[leaf.field] || "";
          if (Array.isArray(value)) return value;
          return valueMatchesNodeSubgroup(leaf, value) ? value : "";
        },
        nodeSelectionScopeKey(leaf),
        addTagContextFromLeaf(leaf),
      );
      updateSelectionCounts();
    }
    const treeEl = document.getElementById("style-tree");
    treeEl.innerHTML = "";
    renderCategoryTree(tree, treeEl, activeStyleLeafId, selectLeaf);

    const container = document.getElementById("style-chips");
    container.className = "chip-panel";
    const opts = leaf.subgroup ? { subgroup: leaf.subgroup } : {};
    if (isMulti) {
      const multiOpts = STYLE_MULTI_LIMITS[leaf.field] || { max: 4, randomCount: 1 };
      loadCategoryMultiChips(
        container,
        leaf.categoryId,
        () => state.style[leaf.field] || [],
        (v) => {
          state.style[leaf.field] = v;
          clearActiveScopePreset("style");
          notifyStateChange();
        },
        { ...multiOpts, ...opts, selectionScope: nodeSelectionScopeKey(leaf), categoryId: leaf.categoryId },
      );
    } else {
      loadCategoryChips(
        container,
        leaf.categoryId,
        () => state.style[leaf.field] || "",
        (v) => {
          state.style[leaf.field] = v;
          clearActiveScopePreset("style");
          notifyStateChange();
        },
        { ...opts, selectionScope: nodeSelectionScopeKey(leaf), categoryId: leaf.categoryId },
      );
    }
  };

  refreshStylePanel = () => {
    initStyleEnabledChips();
    const styleTree = getStyleTree();
    const currentLeaf = findTreeLeaf(activeStyleLeafId, styleTree);
    if (currentLeaf?.presetPanel) {
      selectLeaf(currentLeaf);
      return;
    }
    if (!state.style.enabled) return;
    selectLeaf(currentLeaf || styleTree.find((n) => n.children)?.children?.[0] || styleTree[0]);
  };
  refreshStylePanel();
}

function findTreeLeaf(leafId, nodes) {
  for (const node of nodes) {
    if (node.children) {
      const found = findTreeLeaf(leafId, node.children);
      if (found) return found;
    } else if (node.id === leafId) {
      return node;
    }
  }
  return null;
}

function findOutfitLeaf(leafId, nodes = getOutfitTree()) {
  return findTreeLeaf(leafId, nodes);
}

function isPoseLeafDisabled(node) {
  return Boolean(node.requiresGroup) && !state.group_mode;
}

function addTagContextFromLeaf(leaf) {
  return leaf?.categoryId ? { categoryId: leaf.categoryId, subgroup: leaf.subgroup || null } : null;
}

function resolveTreeNodeCategoryId(node) {
  if (!node) return null;
  if (node.categoryId) return node.categoryId;
  if (!Array.isArray(node.children) || !node.children.length) return null;
  const ids = new Set();
  for (const child of node.children) {
    const id = resolveTreeNodeCategoryId(child);
    if (id) ids.add(id);
  }
  return ids.size === 1 ? [...ids][0] : null;
}

function buildAddTagButtonHtml(categoryId, subgroup = null) {
  if (!categoryId) return "";
  const subgroupAttr = subgroup ? ` data-add-tag-subgroup="${escapeHtml(subgroup)}"` : "";
  const title = subgroup
    ? `Добавить runtime-тег в ${categoryId} / ${subgroup}`
    : `Добавить runtime-тег в ${categoryId}`;
  return `<span class="btn-add-tag-inline" role="button" tabindex="0" data-open-add-tag-modal data-add-tag-category="${escapeHtml(categoryId)}"${subgroupAttr} title="${escapeHtml(title)}" aria-label="Добавить тег">+</span>`;
}

function appendAddTagButton(container, categoryId, subgroup = null) {
  if (!container || !categoryId) return;
  let btn = container.querySelector(".btn-add-tag-inline");
  if (!btn) {
    btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn-add-tag-inline";
    btn.setAttribute("data-open-add-tag-modal", "");
    btn.textContent = "+";
    btn.setAttribute("aria-label", "Добавить тег");
    container.appendChild(btn);
  }
  btn.dataset.addTagCategory = categoryId;
  if (subgroup) btn.dataset.addTagSubgroup = subgroup;
  else delete btn.dataset.addTagSubgroup;
  btn.title = subgroup
    ? `Добавить runtime-тег в ${categoryId} / ${subgroup}`
    : `Добавить runtime-тег в ${categoryId}`;
}

function setDetailTitle(titleElId, label, addTagContext = null) {
  const titleEl = document.getElementById(titleElId);
  if (!titleEl) return;
  titleEl.textContent = "";
  titleEl.append(document.createTextNode(label));
  if (addTagContext?.categoryId) appendAddTagButton(titleEl, addTagContext.categoryId, addTagContext.subgroup || null);
  else titleEl.querySelector(".btn-add-tag-inline")?.remove();
}

function renderCategoryTree(nodes, container, activeLeafId, onSelect, depth = 0, options = {}) {
  const { isDisabled = () => false } = options;
  for (const node of nodes) {
    if (node.children) {
      const group = document.createElement("div");
      group.className = "outfit-tree-group";
      const title = document.createElement("div");
      title.className = "outfit-tree-group-title";
      title.dataset.groupId = node.id;
      const groupCount = sumTreeNodeCount(node);
      const groupCategoryId = resolveTreeNodeCategoryId(node);
      title.innerHTML = `<span class="tree-label">${node.label}</span><span class="tree-row-trail"><span class="tree-count">${groupCount > 0 ? groupCount : ""}</span></span>`;
      group.appendChild(title);
      renderCategoryTree(node.children, group, activeLeafId, onSelect, depth + 1, options);
      container.appendChild(group);
      continue;
    }

    const disabled = isDisabled(node);
    const leafState = getTreeLeafSelectionState(node);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.dataset.nodeId = node.id;
    if (node.presetPanel) btn.dataset.presetLeaf = node.presetPanel;
    btn.className = "outfit-tree-item"
      + (depth > 0 ? " child" : "")
      + (node.id === activeLeafId ? " active" : "")
      + (disabled ? " disabled" : "");
    btn.innerHTML = `<span class="tree-label">${node.label}</span><span class="tree-row-trail"><span class="tree-count"></span></span>`;
    applyCountDisplay(btn.querySelector(".tree-count"), leafState);
    btn.disabled = disabled;
    btn.onclick = () => {
      if (disabled) {
        toast("Couple poses require Group mode (2girls)");
        return;
      }
      onSelect(node);
    };
    container.appendChild(btn);
  }
}

function renderOutfitTree(nodes, container, depth = 0) {
  renderCategoryTree(nodes, container, activeOutfitLeafId, selectOutfitLeaf, depth);
}

function handleOutfitFieldChange(leaf, value) {
  const conditionField = leaf.conditionField;
  if (conditionField) clearConditionForField(conditionField);

  state.outfit[leaf.field] = value;
  if (leaf.field === "dress" && value) {
    if (leaf.subgroup && DRESS_LAYER_SUBGROUPS.has(leaf.subgroup)) {
      state.outfit.bottom = "";
      clearConditionForField("bottom");
    } else {
      state.outfit.top = "";
      state.outfit.bottom = "";
      state.outfit.underwear_layer = "";
      state.outfit.legwear = "";
      clearConditionForField("top");
      clearConditionForField("bottom");
      clearConditionForField("underwear_layer");
      clearConditionForField("legwear");
    }
  }
  if (leaf.field === "bottom" && value) {
    const subgroup = leaf.subgroup;
    if (subgroup === "long_pants" || subgroup === "underwear") {
      state.outfit.underwear_layer = "";
      clearConditionForField("underwear_layer");
      if (subgroup === "long_pants") {
        state.outfit.legwear = "";
        clearConditionForField("legwear");
      }
    }
    if (subgroup !== "long_pants") clearConditionForField("bottom");
    if (subgroup !== "underwear") {
      const bottomMap = itemSubgroupMaps["outfit.bottom"] || {};
      if (bottomMap[value] !== "underwear") clearConditionForField("underwear_layer");
    }
  }
  if (!value && conditionField) clearConditionForField(conditionField);
}

function selectOutfitLeaf(leaf) {
  activeOutfitLeafId = leaf.id;
  const outfitTree = getOutfitTree();
  const outfitDetailKey = "outfit-tree-detail";
  setDetailTitleWithSelectionCount("outfit-detail-title", leaf.label, outfitDetailKey, () => {
    const value = state.outfit[leaf.field];
    if (Array.isArray(value)) {
      if (!leaf.subgroup) return value;
      const map = itemSubgroupMaps[leaf.categoryId] || {};
      return value.filter((id) => map[id] === leaf.subgroup);
    }
    return countScalarForTreeNode(leaf, value) ? value : "";
  }, nodeSelectionScopeKey(leaf), addTagContextFromLeaf(leaf));
  updateSelectionCounts();
  const tree = document.getElementById("outfit-tree");
  tree.innerHTML = "";
  renderOutfitTree(outfitTree, tree);

  if (leaf.presetPanel && leaf.presetScope) {
    showScopePresetLeaf(
      leaf.presetScope,
      leaf,
      document.getElementById("outfit-chips"),
      document.getElementById("outfit-detail-title"),
      null,
    );
    return;
  }

  const chipsEl = document.getElementById("outfit-chips");
  chipsEl.className = "chip-panel";
  loadCategoryChips(
    chipsEl,
    leaf.categoryId,
    () => state.outfit[leaf.field],
    async (v) => {
      handleOutfitFieldChange(leaf, v);
      clearActiveScopePreset("outfit");
      await renderClothingStatePanel(leaf);
    },
    {
      ...(leaf.subgroup ? { subgroup: leaf.subgroup } : {}),
      selectionScope: nodeSelectionScopeKey(leaf),
      categoryId: leaf.categoryId,
    },
  );
  renderClothingStatePanel(leaf);
}

function setDetailTitleWithSelectionCount(titleElId, label, selectionKey, getSubgroupValues, scopeKey = "", addTagContext = null) {
  const titleEl = document.getElementById(titleElId);
  titleEl.textContent = "";
  titleEl.append(document.createTextNode(label));
  let countEl = titleEl.querySelector(".selection-count");
  if (!countEl) {
    countEl = document.createElement("span");
    countEl.className = "selection-count";
    titleEl.appendChild(countEl);
  }
  selectionCountEls.set(selectionKey, { getVal: getSubgroupValues, el: countEl, scopeKey });
  if (addTagContext?.categoryId) appendAddTagButton(titleEl, addTagContext.categoryId, addTagContext.subgroup || null);
  else titleEl.querySelector(".btn-add-tag-inline")?.remove();
}

function initCategoryTreePanel({
  tree,
  treeElId,
  titleElId,
  hintElId = null,
  chipsElId,
  getActiveLeafId,
  setActiveLeafId,
  getFieldValue,
  setFieldValue,
  multiOpts = null,
  getMultiOpts = null,
  presetScope = null,
  defaultHint = "",
}) {
  const resolveTree = () => {
    const base = typeof tree === "function" ? tree() : tree;
    if (!presetScope) return base;
    const cfg = SCOPE_PRESET_REGISTRY[presetScope];
    return injectPresetsIntoTree(base, presetScope, cfg?.getBuiltinPresets);
  };

  const detailSelectionKey = `${treeElId}-detail`;
  const selectLeaf = (leaf) => {
    setActiveLeafId(leaf.id);
    const resolvedTree = resolveTree();
    const treeEl = document.getElementById(treeElId);
    treeEl.innerHTML = "";
    renderCategoryTree(resolvedTree, treeEl, getActiveLeafId(), selectLeaf);

    const container = document.getElementById(chipsElId);
    const titleEl = document.getElementById(titleElId);
    const hintEl = hintElId ? document.getElementById(hintElId) : null;

    if (leaf.presetPanel && leaf.presetScope) {
      if (titleEl) titleEl.textContent = leaf.label;
      showScopePresetLeaf(leaf.presetScope, leaf, container, titleEl, hintEl);
      return;
    }

    if (hintEl) hintEl.textContent = defaultHint;
    container.className = "chip-panel";

    const isMulti = Boolean(leaf.multi);
    const tagCtx = addTagContextFromLeaf(leaf);
    if (isMulti) {
      setDetailTitleWithSelectionCount(titleElId, leaf.label, detailSelectionKey, () => {
        const values = getFieldValue();
        if (!Array.isArray(values)) return values ? [values] : [];
        if (!leaf.subgroup) return values;
        const map = itemSubgroupMaps[leaf.categoryId] || {};
        return values.filter((id) => map[id] === leaf.subgroup);
      }, nodeSelectionScopeKey(leaf), tagCtx);
      updateSelectionCounts();
    } else {
      setDetailTitleWithSelectionCount(titleElId, leaf.label, detailSelectionKey, () => {
        const value = getFieldValue();
        if (Array.isArray(value)) return value;
        if (!leaf.subgroup) return value || "";
        return valueMatchesNodeSubgroup(leaf, value) ? value : "";
      }, nodeSelectionScopeKey(leaf), tagCtx);
      updateSelectionCounts();
    }

    const onFieldChange = (v) => {
      setFieldValue(v);
      if (presetScope) clearActiveScopePreset(presetScope);
    };
    const chipOpts = {
      ...(leaf.subgroup ? { subgroup: leaf.subgroup } : {}),
      selectionScope: nodeSelectionScopeKey(leaf),
    };
    if (leaf.multi) {
      const resolvedMultiOpts = typeof getMultiOpts === "function"
        ? (getMultiOpts(leaf) || multiOpts || {})
        : (multiOpts || {});
      loadCategoryMultiChips(
        container,
        leaf.categoryId,
        getFieldValue,
        onFieldChange,
        { ...resolvedMultiOpts, ...chipOpts },
      );
    } else {
      loadCategoryChips(container, leaf.categoryId, getFieldValue, onFieldChange, chipOpts);
    }
  };

  const resolvedTree = resolveTree();
  selectLeaf(findTreeLeaf(getActiveLeafId(), resolvedTree) || resolvedTree[0]?.children?.[0] || resolvedTree[0]);
}

function initOutfitPanel() {
  activeOutfitLeafId = "dress_micro_mini";
  selectOutfitLeaf(findOutfitLeaf(activeOutfitLeafId));
}

function resolveCharacterLeafAccess(leaf) {
  if (!leaf?.field) return null;
  if (leaf.categoryId?.startsWith("face.")) {
    return {
      get: () => state.face[leaf.field] || "",
      set: (v) => { state.face[leaf.field] = v; },
    };
  }
  if (leaf.field === "hair" || leaf.categoryId === "appearance.hair") {
    return {
      get: () => state.appearance.hair || "",
      set: (v) => { state.appearance.hair = v; },
    };
  }
  if (leaf.field === "hair_color" || leaf.categoryId === "appearance.hair_color") {
    return {
      get: () => state.appearance.hair_color || "",
      set: (v) => { state.appearance.hair_color = v; },
    };
  }
  if (leaf.field === "eye_color" || leaf.categoryId === "face.eye_color") {
    return {
      get: () => state.face.eye_color || "",
      set: (v) => { state.face.eye_color = v; },
    };
  }
  if (leaf.field === "body_details") {
    return {
      get: () => asStringArray(state.character.body_details),
      set: (v) => { state.character.body_details = asStringArray(v).slice(0, 6); },
    };
  }
  return {
    get: () => coerceCharacterScalar(state.character[leaf.field]),
    set: (v) => {
      state.character[leaf.field] = coerceCharacterScalar(v);
    },
  };
}

function initCharacterPanel() {
  const tree = getCharacterStructureTree();
  if (!tree.length) {
    const chips = document.getElementById("character-chips");
    if (chips) {
      chips.innerHTML = '<span style="color:#eb3b5a;font-size:12px">Character catalog not loaded (character-tree-data.js / face-tree-data.js)</span>';
    }
    return;
  }
  initCategoryTreePanel({
    tree: getCharacterStructureTree,
    presetScope: "character",
    treeElId: "character-tree",
    titleElId: "character-detail-title",
    chipsElId: "character-chips",
    getActiveLeafId: () => activeCharacterLeafId,
    setActiveLeafId: (id) => { activeCharacterLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeCharacterLeafId, getCharacterTree());
      return resolveCharacterLeafAccess(leaf)?.get() ?? "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeCharacterLeafId, getCharacterTree());
      resolveCharacterLeafAccess(leaf)?.set(v);
    },
    multiOpts: { max: 6, randomCount: 2 },
  });
}

function initFacePanel() {
  const tree = getFaceVibeTree();
  if (!tree.length) {
    const chips = document.getElementById("face-chips");
    if (chips) {
      chips.innerHTML = '<span style="color:#eb3b5a;font-size:12px">Face catalog not loaded (face-tree-data.js)</span>';
    }
    return;
  }
  initCategoryTreePanel({
    tree: getFaceVibeTree,
    presetScope: "face",
    treeElId: "face-tree",
    titleElId: "face-detail-title",
    chipsElId: "face-chips",
    getActiveLeafId: () => activeFaceLeafId,
    setActiveLeafId: (id) => { activeFaceLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeFaceLeafId, getFaceTree());
      return leaf?.field ? (state.face[leaf.field] || "") : "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeFaceLeafId, getFaceTree());
      if (leaf?.field) state.face[leaf.field] = v;
    },
  });
}

function initMakeupPanel() {
  initCategoryTreePanel({
    tree: MAKEUP_TREE,
    presetScope: "makeup",
    treeElId: "makeup-tree",
    titleElId: "makeup-detail-title",
    chipsElId: "makeup-chips",
    getActiveLeafId: () => activeMakeupLeafId,
    setActiveLeafId: (id) => { activeMakeupLeafId = id; },
    getFieldValue: () => state.appearance.makeup,
    setFieldValue: (v) => { state.appearance.makeup = v; },
    multiOpts: { max: 6, randomCount: 2 },
  });
}

function initAccessoriesPanel() {
  const clearAllBtn = document.getElementById("btn-accessories-clear-all");
  if (clearAllBtn && !clearAllBtn.dataset.bound) {
    clearAllBtn.dataset.bound = "1";
    clearAllBtn.onclick = () => {
      state.appearance.accessories = [];
      state.appearance.tattoos = [];
      clearGeneratedOutput();
      initAccessoriesPanel();
      notifyStateChange();
      toast("Все аксессуары и тату отключены");
    };
  }
  initCategoryTreePanel({
    tree: ACCESSORIES_TREE,
    presetScope: "accessories",
    treeElId: "accessories-tree",
    titleElId: "accessories-detail-title",
    chipsElId: "accessories-chips",
    getActiveLeafId: () => activeAccessoriesLeafId,
    setActiveLeafId: (id) => { activeAccessoriesLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeAccessoriesLeafId, getAccessoriesTree());
      const field = leaf?.field || "accessories";
      const values = state.appearance[field] || [];
      return Array.isArray(values) ? values : [];
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeAccessoriesLeafId, getAccessoriesTree());
      const field = leaf?.field || "accessories";
      const max = field === "tattoos" ? 6 : 4;
      state.appearance[field] = Array.isArray(v) ? v.slice(0, max) : [];
    },
    getMultiOpts: (leaf) => (
      leaf?.field === "tattoos"
        ? { max: 6, randomCount: 2 }
        : { max: 4, randomCount: 2 }
    ),
  });
}

function initPosePanel() {
  const poseTree = getPoseTree();
  const selectLeaf = (leaf) => {
    if (isPoseLeafDisabled(leaf)) {
      toast("Couple poses require Group mode (2girls)");
      return;
    }
    activePoseLeafId = leaf.id;
    const poseDetailKey = "pose-tree-detail";
    setDetailTitleWithSelectionCount("pose-detail-title", leaf.label, poseDetailKey, () => {
      const value = state.pose || "";
      return countScalarForTreeNode(leaf, value) ? value : "";
    }, nodeSelectionScopeKey(leaf), addTagContextFromLeaf(leaf));
    updateSelectionCounts();
    const treeEl = document.getElementById("pose-tree");
    treeEl.innerHTML = "";
    renderCategoryTree(poseTree, treeEl, activePoseLeafId, selectLeaf, 0, { isDisabled: isPoseLeafDisabled });

    if (leaf.presetPanel && leaf.presetScope) {
      showScopePresetLeaf(
        leaf.presetScope,
        leaf,
        document.getElementById("pose-chips"),
        document.getElementById("pose-detail-title"),
        document.getElementById("pose-detail-hint"),
      );
      return;
    }

    const chipsEl = document.getElementById("pose-chips");
    chipsEl.className = "chip-panel";
    loadCategoryChips(
      chipsEl,
      leaf.categoryId,
      () => state.pose,
      (v) => {
        state.pose = v;
        clearActiveScopePreset("pose");
      },
      {
        ...(leaf.subgroup ? { subgroup: leaf.subgroup } : {}),
        selectionScope: nodeSelectionScopeKey(leaf),
        categoryId: leaf.categoryId,
      },
    );
  };

  const leaf = findTreeLeaf(activePoseLeafId, poseTree);
  if (!leaf || isPoseLeafDisabled(leaf)) {
    if (leaf?.categoryId === "pose.couple") state.pose = "";
    activePoseLeafId = "pose_standing_seductive";
  }
  selectLeaf(findTreeLeaf(activePoseLeafId, poseTree));
}

function onGroupModeChanged() {
  state.group_mode = document.getElementById("opt-group-mode").checked;
  const activeLeaf = findTreeLeaf(activePoseLeafId, getPoseTree());
  if (activeLeaf?.categoryId === "pose.couple" && !state.group_mode) {
    state.pose = "";
    activePoseLeafId = "pose_standing_seductive";
  }
  initPosePanel();
  notifyStateChange();
}

let activeCameraLeafId = "camera_angle_standard_angles";

const activeScopePresetIds = {};

const CAMERA_PRESET_FIELDS = ["angle", "framing", "lens", "focus", "composition", "nsfw_shot"];
const LIGHTING_PRESET_FIELDS = ["light_type", "direction", "quality", "color_mood", "nsfw"];
const OUTFIT_PRESET_FIELDS = ["dress", "top", "bottom", "underwear_layer", "legwear", "jacket", "footwear", "gloves", "cape"];
const STYLE_PRESET_FIELDS = ["art_style", "artist_style", "quality", "aesthetic", "technique"];

function getActiveScopePresetId(scope) {
  return activeScopePresetIds[scope] || "";
}

function setActiveScopePresetId(scope, key) {
  if (key) activeScopePresetIds[scope] = key;
  else delete activeScopePresetIds[scope];
}

function injectPresetsIntoTree(baseTree, scopeKey, getBuiltinPresets) {
  const builtins = typeof getBuiltinPresets === "function" ? getBuiltinPresets() : (getBuiltinPresets || []);
  const hasBuiltin = Array.isArray(builtins) && builtins.length > 0;
  const children = [];
  if (hasBuiltin) {
    children.push({
      id: `${scopeKey}_presets_builtin`,
      label: "Built-in presets",
      presetScope: scopeKey,
      presetPanel: "builtin",
    });
  }
  children.push({
    id: `${scopeKey}_presets_custom`,
    label: "Custom presets",
    presetScope: scopeKey,
    presetPanel: "custom",
  });
  return [{ id: `${scopeKey}_presets`, label: "Presets", children }, ...injectWildcardLeaves(baseTree || [])];
}

function collectCategoryIdsFromTree(nodes, ids = new Set()) {
  for (const node of nodes || []) {
    if (node.categoryId) ids.add(node.categoryId);
    if (node.children) collectCategoryIdsFromTree(node.children, ids);
  }
  return ids;
}

function collectPayloadTagIds(payload) {
  const ids = [];
  function walk(value) {
    if (!value) return;
    if (typeof value === "string") {
      if (value) ids.push(value);
      return;
    }
    if (Array.isArray(value)) {
      value.forEach(walk);
      return;
    }
    if (typeof value === "object") Object.values(value).forEach(walk);
  }
  walk(payload);
  return ids;
}

function scopePresetPayloadCount(payload) {
  let count = 0;
  function walk(value) {
    if (!value) return;
    if (typeof value === "string") {
      if (value) count += 1;
      return;
    }
    if (Array.isArray(value)) {
      count += value.filter(Boolean).length;
      return;
    }
    if (typeof value === "object") Object.values(value).forEach(walk);
  }
  walk(payload);
  return count;
}

function buildScopePresetHint(scope, payload) {
  const categoryIds = resolveScopeCategoryIds(scope);
  const ids = collectPayloadTagIds(payload);
  const labels = ids.map((id) => {
    for (const categoryId of categoryIds) {
      if (itemLabelCache[categoryId]?.[id]) return itemLabelCache[categoryId][id];
    }
    return id;
  });
  return labels.join(" + ");
}

async function ensureScopePresetItemLabels(scope) {
  await Promise.all(
    resolveScopeCategoryIds(scope).map(async (categoryId) => {
      if (itemLabelCache[categoryId] && Object.keys(itemLabelCache[categoryId]).length > 0) return;
      const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
      registerCategoryItems(categoryId, data.items);
    }),
  );
}

function clearActiveScopePreset(scope) {
  if (!getActiveScopePresetId(scope)) return;
  setActiveScopePresetId(scope, "");
  const cfg = SCOPE_PRESET_REGISTRY[scope];
  if (cfg?.getTree && cfg.treeElId) {
    updateTreeCountsInContainer(cfg.getTree(), document.getElementById(cfg.treeElId));
  }
  const leafId = cfg?.getActiveLeafId?.();
  const leaf = leafId && cfg?.getTree ? findTreeLeaf(leafId, cfg.getTree()) : null;
  if (leaf?.presetPanel && cfg?.chipsElId) {
    renderScopePresetPanel(scope, leaf.presetPanel, document.getElementById(cfg.chipsElId));
  }
}

function normalizeScopePresetPayload(scope, payload) {
  if (!payload || typeof payload !== "object") return {};
  if (scope === "face") {
    const face = {};
    const src = (payload.face && typeof payload.face === "object") ? payload.face : payload;
    for (const field of FACE_VIBE_FIELDS) {
      const val = src[field] ?? payload[field];
      if (val) face[field] = val;
    }
    return { face };
  }
  if (scope === "makeup" && Array.isArray(payload.makeup)) return { makeup: payload.makeup };
  if (scope === "accessories" && Array.isArray(payload.accessories)) return { accessories: payload.accessories };
  if (scope === "pose" && payload.pose) return { pose: payload.pose };
  if (scope === "fetish" && Array.isArray(payload.elements)) return { elements: payload.elements };
  if (scope === "outfit" && payload.outfit) return { outfit: payload.outfit };
  if (scope === "environment") return payload;
  if (scope === "style") return payload;
  if (scope === "camera") return payload.camera ? payload.camera : payload;
  if (scope === "lighting") return payload;
  if (scope === "character") return payload;
  return payload;
}

async function applyScopePreset(scope, presetKey, label, payload) {
  setActiveScopePresetId(scope, presetKey);
  resetFieldSelectionModes();
  const normalized = normalizeScopePresetPayload(scope, payload || {});
  SCOPE_PRESET_REGISTRY[scope].applyPayload(normalized);
  await preloadSubgroupMaps();
  SCOPE_PRESET_REGISTRY[scope].refreshPanel();
  notifyStateChange();
  toast(`Preset: ${label}`);
}

function renderScopePresetListItem(scope, { key, name, hint, onApply, onRename, onDelete }) {
  const row = document.createElement("div");
  row.className = "scope-preset-item" + (getActiveScopePresetId(scope) === key ? " active" : "");
  row.innerHTML = `
    <div class="scope-preset-meta">
      <div class="scope-preset-name">${escapeHtml(name)}</div>
      ${hint ? `<div class="scope-preset-hint">${escapeHtml(hint)}</div>` : ""}
    </div>
    <div class="scope-preset-actions"></div>`;
  row.onclick = (e) => {
    if (e.target.closest("button")) return;
    onApply();
  };
  const actions = row.querySelector(".scope-preset-actions");
  const applyBtn = document.createElement("button");
  applyBtn.type = "button";
  applyBtn.className = "scope-preset-apply";
  applyBtn.textContent = "Применить";
  applyBtn.onclick = (e) => {
    e.stopPropagation();
    onApply();
  };
  actions.appendChild(applyBtn);
  if (onRename) {
    const renameBtn = document.createElement("button");
    renameBtn.type = "button";
    renameBtn.className = "scope-preset-rename";
    renameBtn.textContent = "✎";
    renameBtn.title = "Переименовать";
    renameBtn.onclick = (e) => {
      e.stopPropagation();
      onRename();
    };
    actions.appendChild(renameBtn);
  }
  if (onDelete) {
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "scope-preset-delete";
    deleteBtn.textContent = "✕";
    deleteBtn.title = "Удалить";
    deleteBtn.onclick = (e) => {
      e.stopPropagation();
      onDelete();
    };
    actions.appendChild(deleteBtn);
  }
  return row;
}

async function saveUserScopePresetFromState(scope) {
  const cfg = SCOPE_PRESET_REGISTRY[scope];
  const payload = cfg.snapshotPayload();
  if (!scopePresetPayloadCount(payload)) {
    toast(cfg.emptySaveMessage || "Выберите хотя бы один параметр");
    return;
  }
  try {
    await ensureScopePresetItemLabels(scope);
    const hint = buildScopePresetHint(scope, payload);
    const defaultName = hint.slice(0, 80) || cfg.defaultSaveName || "Preset";
    const name = window.prompt("Название пресета", defaultName);
    if (!name?.trim()) return;
    await api("/user-presets", {
      method: "POST",
      body: JSON.stringify({ scope, name: name.trim(), payload, hint }),
    });
    toast("Пресет сохранён");
    const leaf = findTreeLeaf(cfg.getActiveLeafId(), cfg.getTree());
    if (leaf?.presetPanel === "custom" && cfg.chipsElId) {
      renderScopePresetPanel(scope, "custom", document.getElementById(cfg.chipsElId));
    }
  } catch (err) {
    toast("Ошибка: " + err.message);
  }
}

async function renderScopePresetPanel(scope, kind, container) {
  if (!container) return;
  const cfg = SCOPE_PRESET_REGISTRY[scope];
  container.innerHTML = "";
  container.className = "scope-preset-panel";

  if (kind === "custom") {
    const toolbar = document.createElement("div");
    toolbar.className = "scope-preset-toolbar";
    const saveBtn = document.createElement("button");
    saveBtn.type = "button";
    saveBtn.className = "btn btn-secondary btn-sm btn-preset-save";
    saveBtn.textContent = "+ Сохранить текущие настройки";
    saveBtn.onclick = () => saveUserScopePresetFromState(scope);
    toolbar.appendChild(saveBtn);
    container.appendChild(toolbar);
  }

  const list = document.createElement("div");
  list.className = "scope-preset-list";
  container.appendChild(list);

  if (kind === "builtin") {
    const presets = cfg.getBuiltinPresets();
    if (!presets.length) {
      list.innerHTML = '<p class="scope-preset-empty">Built-in presets not loaded.</p>';
      return;
    }
    for (const preset of presets) {
      list.appendChild(
        renderScopePresetListItem(scope, {
          key: `builtin:${preset.id}`,
          name: preset.label,
          hint: preset.hint || "",
          onApply: () => applyScopePreset(scope, `builtin:${preset.id}`, preset.label, preset.payload),
        }),
      );
    }
    return;
  }

  list.innerHTML = '<p class="scope-preset-empty">Загрузка…</p>';
  try {
    const rows = await api(`/user-presets?scope=${encodeURIComponent(scope)}&limit=100`);
    list.innerHTML = "";
    if (!rows.length) {
      list.innerHTML = `
        <p class="scope-preset-empty">Пока пусто.</p>
        <p class="scope-preset-empty">${escapeHtml(cfg.customEmptyHint || "")}</p>`;
      return;
    }
    for (const preset of rows) {
      list.appendChild(
        renderScopePresetListItem(scope, {
          key: `user:${preset.id}`,
          name: preset.name,
          hint: preset.hint || buildScopePresetHint(scope, preset.payload || {}),
          onApply: () => applyScopePreset(scope, `user:${preset.id}`, preset.name, preset.payload || {}),
          onRename: async () => {
            const nextName = window.prompt("Новое название", preset.name);
            if (!nextName?.trim() || nextName.trim() === preset.name) return;
            try {
              await api(`/user-presets/${preset.id}`, {
                method: "PUT",
                body: JSON.stringify({ name: nextName.trim() }),
              });
              toast("Переименовано");
              renderScopePresetPanel(scope, "custom", container);
            } catch (err) {
              toast("Ошибка: " + err.message);
            }
          },
          onDelete: async () => {
            if (!window.confirm(`Удалить «${preset.name}»?`)) return;
            try {
              await api(`/user-presets/${preset.id}`, { method: "DELETE" });
              if (getActiveScopePresetId(scope) === `user:${preset.id}`) setActiveScopePresetId(scope, "");
              toast("Удалено");
              renderScopePresetPanel(scope, "custom", container);
            } catch (err) {
              toast("Ошибка: " + err.message);
            }
          },
        }),
      );
    }
  } catch (err) {
    list.innerHTML = `<p class="scope-preset-empty" style="color:#eb3b5a">${escapeHtml(err.message)}</p>`;
  }
}

function showScopePresetLeaf(scope, leaf, container, titleEl, hintEl) {
  const cfg = SCOPE_PRESET_REGISTRY[scope];
  if (titleEl) titleEl.textContent = leaf.label;
  if (hintEl) {
    hintEl.textContent = leaf.presetPanel === "builtin" ? cfg.builtinHint : cfg.customHint;
  }
  renderScopePresetPanel(scope, leaf.presetPanel, container);
}

const SCOPE_PRESET_REGISTRY = {
  style: {
    scope: "style",
    treeElId: "style-tree",
    chipsElId: "style-chips",
    getActiveLeafId: () => activeStyleLeafId,
    getTree: () => getStyleTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(window.STYLE_TREE || [])],
    snapshotPayload: () => {
      if (!state.style.enabled) return {};
      const payload = {};
      for (const field of STYLE_PRESET_FIELDS) {
        const value = state.style[field];
        if (Array.isArray(value) ? value.length : value) {
          payload[field] = Array.isArray(value) ? [...value] : value;
        }
      }
      return payload;
    },
    applyPayload: (payload) => {
      state.style.enabled = true;
      for (const field of STYLE_PRESET_FIELDS) {
        if (field in payload) {
          state.style[field] = Array.isArray(state.style[field])
            ? (Array.isArray(payload[field]) ? payload[field] : [])
            : (payload[field] || "");
        }
      }
    },
    refreshPanel: () => initStylePanel(),
    emptySaveMessage: "Выберите хотя бы один параметр стиля",
    defaultSaveName: "Style preset",
    builtinHint: "",
    customHint: "Сохранение текущих тегов стиля · переименование и удаление",
    customEmptyHint: "Настройте стиль в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  character: {
    scope: "character",
    treeElId: "character-tree",
    chipsElId: "character-chips",
    getActiveLeafId: () => activeCharacterLeafId,
    getTree: () => getCharacterTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(getCharacterStructureTree())],
    snapshotPayload: () => buildCharacterLibraryPayload(),
    applyPayload: (payload) => applyCharacterLibraryPayload(payload),
    refreshPanel: () => initCharacterPanel(),
    emptySaveMessage: "Выберите параметры персонажа",
    defaultSaveName: "Character preset",
    customHint: "Сохранение Character + Face + Hair · переименование и удаление",
    customEmptyHint: "Настройте персонажа в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  face: {
    scope: "face",
    treeElId: "face-tree",
    chipsElId: "face-chips",
    getActiveLeafId: () => activeFaceLeafId,
    getTree: () => getFaceTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(getFaceVibeTree())],
    snapshotPayload: () => {
      const face = {};
      for (const field of FACE_VIBE_FIELDS) {
        if (state.face[field]) face[field] = state.face[field];
      }
      return Object.keys(face).length ? { face } : {};
    },
    applyPayload: (payload) => {
      const face = payload.face || {};
      for (const field of FACE_VIBE_FIELDS) {
        if (Object.prototype.hasOwnProperty.call(face, field)) {
          state.face[field] = face[field] || "";
        }
      }
    },
    refreshPanel: () => initFacePanel(),
    emptySaveMessage: "Выберите хотя бы один параметр лица",
    defaultSaveName: "Face preset",
    customHint: "Сохранение текущих тегов лица · переименование и удаление",
    customEmptyHint: "Настройте лицо в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  makeup: {
    scope: "makeup",
    treeElId: "makeup-tree",
    chipsElId: "makeup-chips",
    getActiveLeafId: () => activeMakeupLeafId,
    getTree: () => getMakeupTree(),
    getBuiltinPresets: () => [],
    categoryIds: ["appearance.makeup"],
    snapshotPayload: () => (state.appearance.makeup.length ? { makeup: [...state.appearance.makeup] } : {}),
    applyPayload: (payload) => {
      state.appearance.makeup = Array.isArray(payload.makeup) ? payload.makeup.slice(0, 6) : [];
    },
    refreshPanel: () => initMakeupPanel(),
    emptySaveMessage: "Выберите хотя бы один тег макияжа",
    defaultSaveName: "Makeup preset",
    customHint: "Сохранение текущего макияжа · переименование и удаление",
    customEmptyHint: "Выберите макияж в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  outfit: {
    scope: "outfit",
    treeElId: "outfit-tree",
    chipsElId: "outfit-chips",
    getActiveLeafId: () => activeOutfitLeafId,
    getTree: () => getOutfitTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(OUTFIT_TREE)],
    snapshotPayload: () => {
      const outfit = JSON.parse(JSON.stringify(state.outfit));
      const hasField = OUTFIT_PRESET_FIELDS.some((f) => outfit[f])
        || Object.values(outfit.conditions || {}).some((slot) => countSlotConditions(slot) > 0);
      return hasField ? { outfit } : {};
    },
    applyPayload: (payload) => {
      if (!payload.outfit) return;
      const o = payload.outfit;
      for (const field of OUTFIT_PRESET_FIELDS) state.outfit[field] = o[field] || "";
      state.outfit.conditions = sanitizeOutfitConditions(o.conditions);
    },
    refreshPanel: () => initOutfitPanel(),
    emptySaveMessage: "Выберите хотя бы один элемент одежды",
    defaultSaveName: "Outfit preset",
    customHint: "Сохранение текущего outfit · переименование и удаление",
    customEmptyHint: "Настройте одежду в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  accessories: {
    scope: "accessories",
    treeElId: "accessories-tree",
    chipsElId: "accessories-chips",
    getActiveLeafId: () => activeAccessoriesLeafId,
    getTree: () => getAccessoriesTree(),
    getBuiltinPresets: () => [],
    categoryIds: ["appearance.accessories"],
    snapshotPayload: () => (
      state.appearance.accessories.length ? { accessories: [...state.appearance.accessories] } : {}
    ),
    applyPayload: (payload) => {
      state.appearance.accessories = Array.isArray(payload.accessories) ? payload.accessories.slice(0, 4) : [];
    },
    refreshPanel: () => initAccessoriesPanel(),
    emptySaveMessage: "Выберите хотя бы один аксессуар",
    defaultSaveName: "Accessories preset",
    customHint: "Сохранение текущих аксессуаров · переименование и удаление",
    customEmptyHint: "Выберите аксессуары в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  pose: {
    scope: "pose",
    treeElId: "pose-tree",
    chipsElId: "pose-chips",
    getActiveLeafId: () => activePoseLeafId,
    getTree: () => getPoseTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(POSE_TREE)],
    snapshotPayload: () => (state.pose ? { pose: state.pose } : {}),
    applyPayload: (payload) => {
      state.pose = payload.pose || "";
    },
    refreshPanel: () => initPosePanel(),
    emptySaveMessage: "Выберите позу",
    defaultSaveName: "Pose preset",
    customHint: "Сохранение текущей позы · переименование и удаление",
    customEmptyHint: "Выберите позу в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  camera: {
    scope: "camera",
    treeElId: "camera-tree",
    chipsElId: "camera-chips",
    getActiveLeafId: () => activeCameraLeafId,
    getTree: () => getCameraTree(),
    getBuiltinPresets: () => (window.CAMERA_PRESETS || []).map((p) => ({
      id: p.id,
      label: p.label,
      hint: p.hint || "",
      payload: p.camera || {},
    })),
    categoryIds: ["camera.angle", "camera.framing", "camera.lens", "camera.focus", "camera.composition", "camera.nsfw_shot"],
    snapshotPayload: () => {
      const payload = {};
      for (const field of CAMERA_PRESET_FIELDS) {
        if (state.camera[field]) payload[field] = state.camera[field];
      }
      return payload;
    },
    applyPayload: (payload) => {
      for (const field of CAMERA_PRESET_FIELDS) {
        state.camera[field] = payload[field] || "";
      }
    },
    refreshPanel: () => initCameraPanel(),
    emptySaveMessage: "Выберите хотя бы один параметр камеры",
    defaultSaveName: "Camera preset",
    builtinHint: "30 готовых комбинаций · один активный пресет · клик по строке или «Применить»",
    customHint: "Сохранение текущих тегов камеры · переименование и удаление",
    customEmptyHint: "Настройте камеру в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  lighting: {
    scope: "lighting",
    treeElId: "lighting-tree",
    chipsElId: "lighting-chips",
    getActiveLeafId: () => activeLightingLeafId,
    getTree: () => getLightingTree(),
    getBuiltinPresets: () => (window.LIGHTING_PRESETS || []).map((p) => ({
      id: p.id,
      label: p.label,
      hint: p.hint || "",
      payload: { lighting: p.lighting || {}, camera: p.camera || {} },
    })),
    categoryIds: ["lighting.light_type", "lighting.direction", "lighting.quality", "lighting.color_mood", "lighting.nsfw", "camera.angle", "camera.framing"],
    snapshotPayload: () => {
      const payload = { lighting: {} };
      for (const field of LIGHTING_PRESET_FIELDS) {
        if (state.lighting[field]) payload.lighting[field] = state.lighting[field];
      }
      return scopePresetPayloadCount(payload.lighting) ? payload : {};
    },
    applyPayload: (payload) => {
      for (const field of LIGHTING_PRESET_FIELDS) {
        state.lighting[field] = payload.lighting?.[field] || "";
      }
      if (payload.camera) {
        for (const field of CAMERA_PRESET_FIELDS) {
          if (payload.camera[field]) state.camera[field] = payload.camera[field];
        }
        clearActiveScopePreset("camera");
        initCameraPanel();
      }
    },
    refreshPanel: () => initLightingPanel(),
    emptySaveMessage: "Выберите хотя бы один параметр освещения",
    defaultSaveName: "Lighting preset",
    builtinHint: "Готовые комбинации освещения (+ камера) · один активный пресет",
    customHint: "Сохранение текущих тегов освещения · переименование и удаление",
    customEmptyHint: "Настройте освещение в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  environment: {
    scope: "environment",
    treeElId: "environment-tree",
    chipsElId: "environment-chips",
    getActiveLeafId: () => activeEnvironmentLeafId,
    getTree: () => getEnvironmentTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(window.ENVIRONMENT_TREE || [])],
    snapshotPayload: () => {
      const payload = {};
      const scene = {};
      for (const field of ["time", "weather", "season"]) {
        if (state.scene[field]) scene[field] = state.scene[field];
      }
      if (Object.keys(scene).length) payload.scene = scene;
      const environment = {};
      if (state.environment.location) environment.location = state.environment.location;
      if (state.environment.situation) environment.situation = state.environment.situation;
      if (state.environment.modifiers?.length) environment.modifiers = [...state.environment.modifiers];
      if (Object.keys(environment).length) payload.environment = environment;
      return payload;
    },
    applyPayload: (payload) => {
      for (const field of ["time", "weather", "season"]) {
        state.scene[field] = payload.scene?.[field] || "";
      }
      state.environment.location = payload.environment?.location || "";
      state.environment.situation = payload.environment?.situation || "";
      state.environment.modifiers = Array.isArray(payload.environment?.modifiers)
        ? payload.environment.modifiers.slice(0, 2)
        : [];
    },
    refreshPanel: () => initEnvironmentPanel(),
    emptySaveMessage: "Выберите хотя бы один параметр окружения",
    defaultSaveName: "Environment preset",
    customHint: "Сохранение текущего окружения · переименование и удаление",
    customEmptyHint: "Настройте окружение в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
  fetish: {
    scope: "fetish",
    treeElId: "fetish-tree",
    chipsElId: "fetish-chips",
    getActiveLeafId: () => activeFetishLeafId,
    getTree: () => getFetishTree(),
    getBuiltinPresets: () => [],
    categoryIds: () => [...collectCategoryIdsFromTree(window.FETISH_TREE || [])],
    snapshotPayload: () => (
      state.fetish.elements.length ? { elements: [...state.fetish.elements] } : {}
    ),
    applyPayload: (payload) => {
      state.fetish.elements = Array.isArray(payload.elements) ? payload.elements.slice(0, 5) : [];
    },
    refreshPanel: () => initFetishPanel(),
    emptySaveMessage: "Выберите хотя бы один элемент фетиша",
    defaultSaveName: "Fetish preset",
    customHint: "Сохранение текущих элементов · переименование и удаление",
    customEmptyHint: "Выберите элементы в подгруппах ниже и нажмите «+ Сохранить текущие настройки».",
  },
};

function resolveScopeCategoryIds(scope) {
  const cfg = SCOPE_PRESET_REGISTRY[scope];
  const ids = cfg.categoryIds;
  return typeof ids === "function" ? ids() : (ids || []);
}

function getStyleTree() {
  return injectPresetsIntoTree(window.STYLE_TREE || [], "style", []);
}

function getCharacterTree() {
  return injectPresetsIntoTree(getCharacterStructureTree(), "character", []);
}

function getFaceTree() {
  return injectPresetsIntoTree(getFaceVibeTree(), "face", []);
}

function getMakeupTree() {
  return injectPresetsIntoTree(MAKEUP_TREE, "makeup", []);
}

function getOutfitTree() {
  return injectPresetsIntoTree(OUTFIT_TREE, "outfit", []);
}

function getAccessoriesTree() {
  return injectPresetsIntoTree(ACCESSORIES_TREE, "accessories", []);
}

function getPoseTree() {
  return injectPresetsIntoTree(POSE_TREE, "pose", []);
}

function getCameraTree() {
  return injectPresetsIntoTree(window.CAMERA_TREE || [], "camera", SCOPE_PRESET_REGISTRY.camera.getBuiltinPresets);
}

function getLightingTree() {
  return injectPresetsIntoTree(window.LIGHTING_TREE || [], "lighting", SCOPE_PRESET_REGISTRY.lighting.getBuiltinPresets);
}

function getEnvironmentTree() {
  return injectPresetsIntoTree(window.ENVIRONMENT_TREE || [], "environment", []);
}

function getFetishTree() {
  return injectPresetsIntoTree(window.FETISH_TREE || [], "fetish", []);
}

let activeLightingLeafId = "lighting_light_type_natural";
let activeFetishLeafId = "fetish_bdsm_restraints_items";

function initLightingPanel() {
  initCategoryTreePanel({
    tree: () => window.LIGHTING_TREE || [],
    presetScope: "lighting",
    treeElId: "lighting-tree",
    titleElId: "lighting-detail-title",
    hintElId: "lighting-detail-hint",
    chipsElId: "lighting-chips",
    getActiveLeafId: () => activeLightingLeafId,
    setActiveLeafId: (id) => { activeLightingLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeLightingLeafId, getLightingTree());
      return leaf?.field ? state.lighting[leaf.field] : "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeLightingLeafId, getLightingTree());
      if (leaf?.field) state.lighting[leaf.field] = v;
    },
    defaultHint: "Одна опция на категорию · Off / Random / single-select",
  });
}

function initCameraPanel() {
  initCategoryTreePanel({
    tree: () => window.CAMERA_TREE || [],
    presetScope: "camera",
    treeElId: "camera-tree",
    titleElId: "camera-detail-title",
    hintElId: "camera-detail-hint",
    chipsElId: "camera-chips",
    getActiveLeafId: () => activeCameraLeafId,
    setActiveLeafId: (id) => { activeCameraLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeCameraLeafId, getCameraTree());
      return leaf?.field ? state.camera[leaf.field] : "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeCameraLeafId, getCameraTree());
      if (leaf?.field) state.camera[leaf.field] = v;
    },
    defaultHint: "Одна опция на категорию · Off / Random / single-select",
  });
}

function initFetishPanel() {
  initCategoryTreePanel({
    tree: () => window.FETISH_TREE || [],
    presetScope: "fetish",
    treeElId: "fetish-tree",
    titleElId: "fetish-detail-title",
    chipsElId: "fetish-chips",
    getActiveLeafId: () => activeFetishLeafId,
    setActiveLeafId: (id) => { activeFetishLeafId = id; },
    getFieldValue: () => state.fetish.elements,
    setFieldValue: (v) => {
      if (v.length > 5) {
        state.fetish.elements = v.slice(0, 5);
        toast("Max 5 fetish elements total");
      } else {
        state.fetish.elements = v;
      }
    },
    multiOpts: { max: 6, randomCount: 2 },
  });
}

function initStaticChips() {
  const modelItems = [
    { id: "illustrious", label: "Illustrious" },
    { id: "anima", label: "Anima" },
    { id: "zimage_turbo", label: "Z-Image Turbo" },
  ];
  renderChips(
    document.getElementById("model-chips"),
    modelItems,
    state.model_id,
    (v) => {
      state.model_id = v || "illustrious";
      document.getElementById("negative-card").style.display =
        state.model_id === "zimage_turbo" ? "none" : "";
      syncQualityBoostersPanel();
      notifyStateChange();
    },
    { offValue: "illustrious", showControls: false },
  );
}

function normalizeActiveTab(tab) {
  if (tab === "scene") return "environment";
  if (tab === "hair") return "character";
  return tab;
}

function switchTab(tab) {
  tab = normalizeActiveTab(tab);
  if (!TAB_META[tab]) return;
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === tab));
  const meta = TAB_META[tab];
  document.getElementById("panel-title").textContent = meta.title;
  document.getElementById("panel-desc").textContent = meta.desc;
  pendingActiveTab = tab;
  scheduleSessionPersist();
  if (tab === "environment") refreshEnvironmentPanel();
  if (tab === "style") refreshStylePanel();
  if (tab === "character") loadCharacterLibrary();
  if (tab === "prompting") initPromptingPanel();
  if (tab === "tagstudio") {
    initTagStudioLister().catch((e) => toast("Ошибка: " + e.message));
    loadTagStudioPanel().catch((e) => toast("Ошибка: " + e.message));
  }
  if (tab === "wildcards") {
    initWildcardsPanel().catch((e) => toast("Ошибка: " + e.message));
  }
  if (tab === "favorites") loadFavorites();
  if (tab === "llm") loadLlmPanel();
  if (tab === "advanced") {
    loadAdvancedMeta();
    loadHistoryPanel().catch(() => {});
  }
}


// ─────────────────────────────────────────────────────────────────────────────
// Wildcards panel
// ─────────────────────────────────────────────────────────────────────────────

let wildcardsCategoriesCache = null;
let wildcardsExpanded = new Set();

async function initWildcardsPanel() {
  await loadWildcardsCategoryOptions();
  bindWildcardsEvents();
  await loadWildcardsSubgroupOptions(document.getElementById("wildcards-target-category")?.value || "");
  await loadWildcardsList();
}

async function loadWildcardsSubgroupOptions(categoryId) {
  const datalist = document.getElementById("wildcards-subgroup-options");
  if (!datalist) return;
  if (!categoryId) {
    datalist.innerHTML = "";
    return;
  }
  try {
    const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
    const subs = (data.subcategories || []).filter((s) => s && s !== "none");
    datalist.innerHTML = subs.map((s) => `<option value="${escapeHtml(s)}"></option>`).join("");
  } catch {
    datalist.innerHTML = "";
  }
}

async function loadWildcardsCategoryOptions() {
  const select = document.getElementById("wildcards-target-category");
  if (!select) return;
  if (!wildcardsCategoriesCache) {
    try {
      const data = await api("/categories");
      wildcardsCategoriesCache = (data.categories || []).sort((a, b) => a.id.localeCompare(b.id));
    } catch {
      wildcardsCategoriesCache = [];
    }
  }
  const current = select.value;
  select.innerHTML = wildcardsCategoriesCache
    .map((c) => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.id)} — ${escapeHtml(c.title)}</option>`)
    .join("");
  if (current && wildcardsCategoriesCache.some((c) => c.id === current)) select.value = current;
}

let wildcardsEventsBound = false;

function bindWildcardsEvents() {
  if (wildcardsEventsBound) return;
  wildcardsEventsBound = true;

  document.getElementById("btn-wildcards-refresh")?.addEventListener("click", () => {
    loadWildcardsList();
    toast("Wildcards refreshed");
  });

  document.getElementById("wildcards-target-category")?.addEventListener("change", (e) => {
    loadWildcardsSubgroupOptions(e.target.value || "");
  });

  document.getElementById("btn-wildcards-preview")?.addEventListener("click", wildcardsDoPreview);
  document.getElementById("btn-wildcards-upload")?.addEventListener("click", wildcardsDoUpload);

  document.getElementById("wildcards-file-input")?.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    document.getElementById("wildcards-raw-text").value = text;
    const filenameEl = document.getElementById("wildcards-filename");
    if (filenameEl && !filenameEl.value.trim()) filenameEl.value = file.name;
  });
}

async function wildcardsDoPreview() {
  const rawText = document.getElementById("wildcards-raw-text")?.value || "";
  const subgroup = document.getElementById("wildcards-target-subgroup")?.value?.trim() || "";
  const previewEl = document.getElementById("wildcards-preview");
  if (!rawText.trim()) {
    previewEl.textContent = "Введите содержимое файла для предпросмотра.";
    return;
  }
  try {
    const data = await api("/wildcards/preview", {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText, target_subgroup: subgroup }),
    });
    const sample = data.items.slice(0, 5).map((i) => `${escapeHtml(i.label)} → <code>${escapeHtml(i.item_id)}</code>`).join("<br>");
    const more = data.count > 5 ? `<br>…и ещё ${data.count - 5}` : "";
    previewEl.innerHTML = `<strong>${data.count}</strong> строк будет добавлено:<br>${sample}${more}`;
  } catch (e) {
    previewEl.textContent = "Ошибка: " + e.message;
  }
}

async function wildcardsDoUpload() {
  const targetCategory = document.getElementById("wildcards-target-category")?.value || "";
  const targetSubgroup = document.getElementById("wildcards-target-subgroup")?.value?.trim() || "";
  const filename = document.getElementById("wildcards-filename")?.value?.trim() || "";
  const rawText = document.getElementById("wildcards-raw-text")?.value || "";

  if (!targetCategory) return toast("Выберите Category");
  if (!targetSubgroup) return toast("Укажите Subgroup");
  if (!filename) return toast("Укажите File name / label");
  if (!rawText.trim()) return toast("Содержимое файла пустое");

  const btn = document.getElementById("btn-wildcards-upload");
  btn.disabled = true;
  btn.textContent = "Uploading…";
  try {
    const data = await api("/wildcards", {
      method: "POST",
      body: JSON.stringify({
        filename,
        target_category: targetCategory,
        target_subgroup: targetSubgroup,
        raw_text: rawText,
      }),
    });
    toast(`Загружено ${data.item_count} тегов в ${data.target_category} / ${data.target_subgroup}`);
    document.getElementById("wildcards-raw-text").value = "";
    document.getElementById("wildcards-filename").value = "";
    document.getElementById("wildcards-preview").textContent = "—";
    document.getElementById("wildcards-file-input").value = "";
    invalidateWildcardsByCategoryCache();
    await loadWildcardsList();
  } catch (e) {
    toast("Ошибка: " + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Upload";
  }
}

async function loadWildcardsList() {
  const container = document.getElementById("wildcards-list");
  if (!container) return;
  try {
    const data = await api("/wildcards");
    const rows = data.wildcards || [];
    if (!rows.length) {
      container.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Пока нет загруженных wildcards.</span>';
      return;
    }
    container.innerHTML = rows.map((w) => wildcardCardHtml(w)).join("");
    bindWildcardCardEvents();
    // Восстанавливаем развёрнутые карточки
    for (const id of wildcardsExpanded) {
      const body = document.getElementById(`wildcard-items-${id}`);
      if (body) await wildcardsLoadItems(id, body);
    }
  } catch (e) {
    container.innerHTML = `<span style="font-size:12px;color:var(--text-muted)">Ошибка: ${escapeHtml(e.message)}</span>`;
  }
}

function wildcardCardHtml(w) {
  const disabledCls = w.enabled ? "" : " disabled";
  const expandLabel = wildcardsExpanded.has(w.id) ? "▾ Свернуть" : "▸ Показать строки";
  return `
    <div class="wildcard-card${disabledCls}" data-wildcard-id="${w.id}">
      <div class="wildcard-card-header">
        <input type="checkbox" class="wildcard-toggle" data-wildcard-id="${w.id}" ${w.enabled ? "checked" : ""} title="Включить/выключить весь файл" />
        <div class="wildcard-card-title">
          <div class="wildcard-card-filename">${escapeHtml(w.label || w.filename)}</div>
          <div class="wildcard-card-meta">${escapeHtml(w.target_category)} / ${escapeHtml(w.target_subgroup)} · ${w.item_count} строк</div>
        </div>
        <div class="wildcard-card-actions">
          <button type="button" class="wildcard-card-expand" data-wildcard-id="${w.id}">${expandLabel}</button>
          <button type="button" class="wildcard-card-delete" data-wildcard-id="${w.id}">Delete</button>
        </div>
      </div>
      <div class="wildcard-items" id="wildcard-items-${w.id}" style="${wildcardsExpanded.has(w.id) ? "" : "display:none"}">Загрузка…</div>
    </div>`;
}

function bindWildcardCardEvents() {
  document.querySelectorAll(".wildcard-toggle").forEach((cb) => {
    cb.onchange = async () => {
      const id = Number(cb.dataset.wildcardId);
      try {
        await api(`/wildcards/${id}/toggle`, {
          method: "POST",
          body: JSON.stringify({ enabled: cb.checked }),
        });
        toast(cb.checked ? "Wildcard включён" : "Wildcard отключён");
        invalidateWildcardsByCategoryCache();
        const card = cb.closest(".wildcard-card");
        card?.classList.toggle("disabled", !cb.checked);
      } catch (e) {
        toast("Ошибка: " + e.message);
        cb.checked = !cb.checked;
      }
    };
  });

  document.querySelectorAll(".wildcard-card-expand").forEach((btn) => {
    btn.onclick = async () => {
      const id = Number(btn.dataset.wildcardId);
      const body = document.getElementById(`wildcard-items-${id}`);
      if (!body) return;
      const isOpen = body.style.display !== "none";
      if (isOpen) {
        body.style.display = "none";
        wildcardsExpanded.delete(id);
        btn.textContent = "▸ Показать строки";
      } else {
        body.style.display = "";
        wildcardsExpanded.add(id);
        btn.textContent = "▾ Свернуть";
        await wildcardsLoadItems(id, body);
      }
    };
  });

  document.querySelectorAll(".wildcard-card-delete").forEach((btn) => {
    btn.onclick = async () => {
      const id = Number(btn.dataset.wildcardId);
      if (!confirm("Удалить этот wildcard вместе со всеми тегами?")) return;
      try {
        await api(`/wildcards/${id}`, { method: "DELETE" });
        toast("Wildcard удалён");
        invalidateWildcardsByCategoryCache();
        wildcardsExpanded.delete(id);
        await loadWildcardsList();
      } catch (e) {
        toast("Ошибка: " + e.message);
      }
    };
  });
}

async function wildcardsLoadItems(wildcardId, container) {
  try {
    const data = await api(`/wildcards/${wildcardId}`);
    const items = data.items || [];
    container.innerHTML = items.map((item) => `
      <div class="wildcard-item-row${item.enabled ? "" : " disabled"}">
        <input type="checkbox" data-wildcard-id="${wildcardId}" data-item-id="${escapeHtml(item.item_id)}" ${item.enabled ? "checked" : ""} />
        <span class="wildcard-item-label">${escapeHtml(item.label)}</span>
        <span class="wildcard-item-id">${escapeHtml(item.item_id)}</span>
      </div>`).join("");
    container.querySelectorAll("input[type=checkbox]").forEach((cb) => {
      cb.onchange = async () => {
        const wid = cb.dataset.wildcardId;
        const itemId = cb.dataset.itemId;
        try {
          await api(`/wildcards/${wid}/items/${encodeURIComponent(itemId)}/toggle`, {
            method: "POST",
            body: JSON.stringify({ enabled: cb.checked }),
          });
          invalidateWildcardsByCategoryCache();
          cb.closest(".wildcard-item-row")?.classList.toggle("disabled", !cb.checked);
        } catch (e) {
          toast("Ошибка: " + e.message);
          cb.checked = !cb.checked;
        }
      };
    });
  } catch (e) {
    container.innerHTML = `<span style="font-size:12px;color:var(--text-muted)">Ошибка: ${escapeHtml(e.message)}</span>`;
  }
}

async function loadTagStudioPanel() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const q = document.getElementById("tagstudio-search")?.value?.trim() || "";
  const categoryId = document.getElementById("tagstudio-category")?.value?.trim() || "";
  const subcategoryId = document.getElementById("tagstudio-subcategory")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (categoryId) params.set("category_id", categoryId);
  if (subcategoryId) params.set("subcategory_id", subcategoryId);
  params.set("limit", "200");
  const data = await api(`/tag-studio/items?${params.toString()}`);
  const items = Array.isArray(data?.items) ? data.items : [];
  tagStudioListerItems = items;
  const previousKey = tagStudioSelectedTagRow ? tagStudioRowKey(tagStudioSelectedTagRow) : "";
  tagStudioSelectedTagRow = items.find((row) => tagStudioRowKey(row) === previousKey) || null;
  const summary = document.getElementById("tagstudio-lister-summary");
  if (summary) {
    const parts = [
      q ? `Search: ${q}` : "",
      categoryId ? `Category: ${categoryId}` : "",
      subcategoryId ? `Subcategory: ${subcategoryId}` : "",
    ].filter(Boolean);
    summary.textContent = `Найдено: ${items.length}${parts.length ? ` · ${parts.join(" · ")}` : ""}`;
  }
  renderTagStudioItemsOutput(output, data, { q, categoryId, subcategoryId });
  renderTagStudioListerList(tagStudioListerItems);
  renderTagStudioSelectionState();
}

function renderTagStudioMessage(output, message) {
  output.innerHTML = `<div class="tagstudio-output-empty">${escapeHtml(message)}</div>`;
}

function formatTagStudioPath(label, categoryId, subcategoryId) {
  const subgroup = subcategoryId || "none";
  return `<span class="tagstudio-main">${escapeHtml(label || "—")}</span> — <span class="tagstudio-meta">${escapeHtml(categoryId || "—")} — ${escapeHtml(subgroup)}</span>`;
}

function buildTagStudioItemButtonHtml(row, activeClass = "") {
  const item = row.item || {};
  const subgroup = getTagStudioRowSubcategory(row) || "none";
  const overlayClass = row.overlay ? "tagstudio-lister-overlay" : "tagstudio-lister-core";
  const overlayText = row.overlay ? "runtime" : "core";
  const inactive = item.meta?.is_active === false;
  const key = tagStudioRowKey(row);
  return `
    <button type="button" class="tagstudio-lister-item tagstudio-selectable-item${activeClass}" data-key="${escapeHtml(key)}">
      <div class="tagstudio-lister-title">${escapeHtml(item.label || item.id || "—")}${inactive ? ' <span class="tagstudio-badge-inactive">deactivated</span>' : ""}</div>
      <div class="tagstudio-lister-subline">${escapeHtml(row.category_id || "—")} — ${escapeHtml(subgroup)} · <span class="${overlayClass}">${overlayText}</span></div>
    </button>
  `;
}

function bindTagStudioItemButtons(root, items) {
  if (!root) return;
  root.querySelectorAll(".tagstudio-selectable-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.key || "";
      const row = items.find((entry) => tagStudioRowKey(entry) === key);
      if (row) selectTagStudioListerRow(row);
    });
  });
}

function refreshTagStudioSearchOutputSelection() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  output.querySelectorAll(".tagstudio-selectable-item").forEach((btn) => {
    const active = Boolean(
      tagStudioSelectedTagRow && tagStudioRowKey(tagStudioSelectedTagRow) === (btn.dataset.key || ""),
    );
    btn.classList.toggle("active", active);
  });
}

function renderTagStudioItemsOutput(output, data, filters = {}) {
  const items = Array.isArray(data?.items) ? data.items : [];
  if (!items.length) {
    const hint = filters.q ? "Ничего не найдено. Попробуйте alias или измените запрос Search." : "Ничего не найдено. Измените фильтр или запрос Search.";
    renderTagStudioMessage(output, hint);
    return;
  }
  const categoryCount = new Map();
  const subgroupCount = new Map();
  let aliasesTotal = 0;
  for (const row of items) {
    const item = row?.item || {};
    const meta = item.meta || {};
    const categoryId = row?.category_id || "—";
    const subgroup = row?.subcategory_id || meta.subcategory_id || meta.subgroup || "none";
    categoryCount.set(categoryId, (categoryCount.get(categoryId) || 0) + 1);
    subgroupCount.set(subgroup, (subgroupCount.get(subgroup) || 0) + 1);
    aliasesTotal += Array.isArray(meta.aliases) ? meta.aliases.length : 0;
  }
  const topCategories = Array.from(categoryCount.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([categoryId, count]) => `<span class="tagstudio-badge">${escapeHtml(categoryId)}: ${count}</span>`)
    .join("");
  const rows = items.map((row) => {
    const key = tagStudioRowKey(row);
    const activeClass = tagStudioSelectedTagRow && tagStudioRowKey(tagStudioSelectedTagRow) === key ? " active" : "";
    return buildTagStudioItemButtonHtml(row, activeClass);
  });
  const activeFilters = [
    filters.q ? `Search: ${escapeHtml(filters.q)}` : "",
    filters.categoryId ? `Category: ${escapeHtml(filters.categoryId)}` : "",
    filters.subcategoryId ? `Subcategory: ${escapeHtml(filters.subcategoryId)}` : "",
  ].filter(Boolean).join(" · ");
  output.innerHTML = `
    <div class="tagstudio-summary">
      <span class="tagstudio-badge">Найдено тегов: ${items.length}</span>
      <span class="tagstudio-badge">Категорий: ${categoryCount.size}</span>
      <span class="tagstudio-badge">Подгрупп: ${subgroupCount.size}</span>
      <span class="tagstudio-badge">Всего aliases: ${aliasesTotal}</span>
    </div>
    ${activeFilters ? `<div class="tagstudio-meta">${activeFilters}</div>` : ""}
    <div class="tagstudio-section-title">Топ категорий</div>
    <div class="tagstudio-summary">${topCategories || '<span class="tagstudio-badge">—</span>'}</div>
    <div class="tagstudio-section-title">Результаты — кликните тег для выбора и Edit</div>
    <div class="tagstudio-search-list">${rows.join("")}</div>
  `;
  bindTagStudioItemButtons(output, items);
}

async function runTagStudioDedupe() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const categoryId = document.getElementById("tagstudio-category")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (categoryId) params.set("category_id", categoryId);
  params.set("fuzzy_threshold", "0.9");
  const data = await api(`/tag-studio/deduplicate?${params.toString()}`);
  renderTagStudioDedupeOutput(output, data, categoryId);
}

function renderTagStudioDedupeOutput(output, data, categoryId = "") {
  const findings = Array.isArray(data?.findings) ? data.findings : [];
  if (!findings.length) {
    renderTagStudioMessage(output, "Дубликатов не найдено.");
    return;
  }
  const typeCount = new Map();
  const uniqueSource = new Set();
  for (const row of findings) {
    const type = row?.match?.match_type || "unknown";
    typeCount.set(type, (typeCount.get(type) || 0) + 1);
    uniqueSource.add(`${row?.category_id || ""}|${row?.source_item_id || ""}`);
  }
  const typeBadges = Array.from(typeCount.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([type, count]) => `<span class="tagstudio-badge">${escapeHtml(type)}: ${count}</span>`)
    .join("");
  const rows = findings.map((row) => {
    const sourceSub = row?.source_subcategory || "none";
    const matchSub = row?.match_subcategory || "none";
    const score = Number.isFinite(row?.match?.score) ? Number(row.match.score).toFixed(3) : "—";
    const sourcePath = formatTagStudioPath(row?.source_label, row?.category_id, sourceSub);
    const matchPath = formatTagStudioPath(row?.match?.label, row?.category_id, matchSub);
    return `<li>${sourcePath}<br><span class="tagstudio-meta">↔ ${matchPath} · ${escapeHtml(row?.match?.match_type || "unknown")} · score: ${score}</span></li>`;
  });
  output.innerHTML = `
    <div class="tagstudio-summary">
      <span class="tagstudio-badge">Найдено совпадений: ${findings.length}</span>
      <span class="tagstudio-badge">Уникальных исходных тегов: ${uniqueSource.size}</span>
      ${categoryId ? `<span class="tagstudio-badge">Category: ${escapeHtml(categoryId)}</span>` : ""}
    </div>
    <div class="tagstudio-section-title">Типы совпадений</div>
    <div class="tagstudio-summary">${typeBadges}</div>
    <div class="tagstudio-section-title">Потенциальные дубли</div>
    <ol class="tagstudio-list">${rows.join("")}</ol>
  `;
}

async function runTagStudioMigration() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const data = await api("/tag-studio/migrate/runtime-subcategory", {
    method: "POST",
    body: JSON.stringify({ status: "active" }),
  });
  renderTagStudioOperationOutput(output, "Migration", data, ["migrated", "updated", "skipped", "errors"]);
  toast(`Migration done: ${data.migrated || 0}`);
}

async function runTagStudioRollback() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const data = await api("/tag-studio/rollback/runtime-subcategory", {
    method: "POST",
    body: JSON.stringify({ status: "active" }),
  });
  renderTagStudioOperationOutput(output, "Rollback", data, ["rolled_back", "updated", "skipped", "errors"]);
  toast(`Rollback done: ${data.rolled_back || 0}`);
}

function renderTagStudioOperationOutput(output, title, data, keys = []) {
  const badges = keys
    .filter((key) => key in (data || {}))
    .map((key) => `<span class="tagstudio-badge">${escapeHtml(key)}: ${escapeHtml(String(data[key]))}</span>`)
    .join("");
  output.innerHTML = `
    <div class="tagstudio-summary">
      <span class="tagstudio-badge">${escapeHtml(title)}</span>
      ${badges}
    </div>
    <div class="tagstudio-section-title">Подробности</div>
    <pre class="tagstudio-raw-json">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
  `;
}

function tagStudioRowKey(row) {
  return `${row?.category_id || ""}::${row?.item?.id || ""}`;
}

function getTagStudioRowSubcategory(row) {
  return row?.subcategory_id || row?.item?.meta?.subcategory_id || row?.item?.meta?.subgroup || "";
}

function setSelectOptions(selectEl, options, selected = "") {
  if (!selectEl) return;
  selectEl.innerHTML = "";
  for (const row of options) {
    const opt = document.createElement("option");
    opt.value = row.value;
    opt.textContent = row.label;
    selectEl.appendChild(opt);
  }
  if (selected && options.some((row) => row.value === selected)) {
    selectEl.value = selected;
  } else if (options.length) {
    selectEl.value = options[0].value;
  }
}

async function loadTagStudioCategorySelects() {
  const categories = await loadAddTagCategories();
  const listerCategory = document.getElementById("tagstudio-lister-category");
  const moveCategory = document.getElementById("tagstudio-move-category");
  const options = categories.map((row) => ({
    value: row.id,
    label: `${row.title} (${row.id})`,
  }));
  setSelectOptions(listerCategory, options);
  setSelectOptions(moveCategory, options);
  return categories;
}

async function loadTagStudioSubcategorySelect(categoryId, selectEl, opts = {}) {
  const { anyLabel = "Все подгруппы", noneLabel = "none", includeAny = true } = opts;
  if (!selectEl) return [];
  if (!categoryId) {
    setSelectOptions(selectEl, [{ value: "", label: anyLabel }]);
    selectEl.dataset.hasSubcategories = "0";
    return [];
  }
  const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
  const values = Array.isArray(data?.subcategories) ? data.subcategories.filter(Boolean) : [];
  const options = [];
  if (includeAny) options.push({ value: "", label: anyLabel });
  if (!values.length) {
    options.push({ value: "", label: noneLabel });
    setSelectOptions(selectEl, options);
    selectEl.dataset.hasSubcategories = "0";
    return [];
  }
  for (const sub of values) options.push({ value: sub, label: sub });
  setSelectOptions(selectEl, options);
  selectEl.dataset.hasSubcategories = "1";
  return values;
}

function renderTagStudioListerList(items) {
  const root = document.getElementById("tagstudio-lister-list");
  if (!root) return;
  if (!items.length) {
    root.innerHTML = '<div class="tagstudio-output-empty">Теги не найдены для выбранного фильтра.</div>';
    return;
  }
  root.innerHTML = items.map((row) => {
    const key = tagStudioRowKey(row);
    const activeClass = tagStudioSelectedTagRow && tagStudioRowKey(tagStudioSelectedTagRow) === key ? " active" : "";
    return buildTagStudioItemButtonHtml(row, activeClass);
  }).join("");
  bindTagStudioItemButtons(root, items);
}

function renderTagStudioSelectionState() {
  const metaEl = document.getElementById("tagstudio-selected-meta");
  const descInput = document.getElementById("tagstudio-edit-description");
  const saveBtn = document.getElementById("btn-tagstudio-save-description");
  const editBtn = document.getElementById("btn-tagstudio-edit-tag");
  const moveBtn = document.getElementById("btn-tagstudio-move-tag");
  const deleteBtn = document.getElementById("btn-tagstudio-delete-tag");
  const reactivateBtn = document.getElementById("btn-tagstudio-reactivate-tag");
  if (!metaEl || !descInput || !saveBtn || !editBtn || !moveBtn || !deleteBtn) return;
  if (!tagStudioSelectedTagRow) {
    metaEl.textContent = "Выберите тег в результатах Search или в листере ниже.";
    descInput.value = "";
    saveBtn.disabled = true;
    editBtn.disabled = true;
    moveBtn.disabled = true;
    deleteBtn.disabled = true;
    reactivateBtn?.classList.add("hidden");
    return;
  }
  const row = tagStudioSelectedTagRow;
  const subgroup = getTagStudioRowSubcategory(row) || "none";
  const inactive = row.item?.meta?.is_active === false;
  const mode = row.overlay ? "runtime (можно менять)" : "core (редактирование → runtime-копия)";
  metaEl.textContent = `${row.item.label} — ${row.category_id} — ${subgroup} · ${mode}${inactive ? " · deactivated" : ""}`;
  descInput.value = row.item.meta?.description || "";
  const editable = !inactive;
  saveBtn.disabled = !editable;
  editBtn.disabled = inactive;
  moveBtn.disabled = !row.overlay || inactive;
  deleteBtn.disabled = !row.overlay || inactive;
  if (reactivateBtn) {
    const showReactivate = Boolean(row.overlay) && inactive;
    reactivateBtn.classList.toggle("hidden", !showReactivate);
    reactivateBtn.disabled = !showReactivate;
  }
}

async function loadTagStudioMoveSubcategoryOptions(categoryId) {
  const input = document.getElementById("tagstudio-move-subcategory");
  const datalist = document.getElementById("tagstudio-move-subcategory-options");
  if (!input) return [];
  if (!categoryId) {
    if (datalist) datalist.innerHTML = "";
    input.dataset.hasSubcategories = "0";
    return [];
  }
  try {
    const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
    const values = (data.subcategories || []).filter((s) => s && s !== "none");
    if (datalist) datalist.innerHTML = values.map((s) => `<option value="${escapeHtml(s)}"></option>`).join("");
    input.dataset.hasSubcategories = values.length ? "1" : "0";
    return values;
  } catch {
    if (datalist) datalist.innerHTML = "";
    input.dataset.hasSubcategories = "0";
    return [];
  }
}

async function syncTagStudioMoveSubcategory(categoryId, selected = "") {
  const moveSubcategory = document.getElementById("tagstudio-move-subcategory");
  if (!moveSubcategory) return;
  // Free-text field with a datalist of existing subgroups as suggestions —
  // unlike the Lister filter select, this one must also accept a brand-new
  // subgroup name that has no tags in it yet (the backend's move endpoint
  // already supports this; the closed <select> it used to be just never
  // offered that as an option, so "move to subcategory" silently couldn't
  // target any subgroup that didn't already contain at least one tag).
  await loadTagStudioMoveSubcategoryOptions(categoryId);
  moveSubcategory.value = selected || "";
}

async function selectTagStudioListerRow(row) {
  tagStudioSelectedTagRow = row;
  renderTagStudioListerList(tagStudioListerItems);
  refreshTagStudioSearchOutputSelection();
  const moveCategory = document.getElementById("tagstudio-move-category");
  if (moveCategory) {
    moveCategory.value = row.category_id || "";
    await syncTagStudioMoveSubcategory(moveCategory.value, getTagStudioRowSubcategory(row));
  }
  renderTagStudioSelectionState();
  document.querySelector(".tagstudio-selected")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadTagStudioLister() {
  const categoryId = document.getElementById("tagstudio-lister-category")?.value || "";
  const subcategoryId = document.getElementById("tagstudio-lister-subcategory")?.value || "";
  const activeOnly = Boolean(document.getElementById("tagstudio-lister-active-only")?.checked);
  const summary = document.getElementById("tagstudio-lister-summary");
  const params = new URLSearchParams();
  if (categoryId) params.set("category_id", categoryId);
  if (subcategoryId) params.set("subcategory_id", subcategoryId);
  params.set("active_only", activeOnly ? "true" : "false");
  params.set("limit", "500");
  const data = await api(`/tag-studio/items?${params.toString()}`);
  tagStudioListerItems = Array.isArray(data?.items) ? data.items : [];
  const previousKey = tagStudioSelectedTagRow ? tagStudioRowKey(tagStudioSelectedTagRow) : "";
  const stillExists = tagStudioListerItems.find((row) => tagStudioRowKey(row) === previousKey);
  tagStudioSelectedTagRow = stillExists || null;
  if (summary) {
    summary.textContent = `Найдено: ${tagStudioListerItems.length} · Category: ${categoryId || "all"} · Subcategory: ${subcategoryId || "all"} · ${activeOnly ? "active only" : "active + inactive"}`;
  }
  renderTagStudioListerList(tagStudioListerItems);
  renderTagStudioSelectionState();
}

async function handleTagStudioSaveDescription() {
  if (!tagStudioSelectedTagRow) return toast("Сначала выберите тег");
  if (tagStudioSelectedTagRow.item?.meta?.is_active === false) {
    return toast("Сначала восстановите тег (Reactivate)");
  }
  const description = document.getElementById("tagstudio-edit-description")?.value.trim() || "";
  const categoryId = tagStudioSelectedTagRow.category_id;
  const itemId = tagStudioSelectedTagRow.item.id;
  await api(`/categories/${encodeURIComponent(categoryId)}/items/${encodeURIComponent(itemId)}`, {
    method: "PUT",
    body: JSON.stringify({
      description: description || null,
      persist: true,
      source: "user",
    }),
  });
  toast("Описание обновлено");
  await Promise.all([loadTagStudioLister(), loadTagStudioPanel()]);
}

async function handleTagStudioMoveTag() {
  if (!tagStudioSelectedTagRow) return toast("Сначала выберите тег");
  if (!tagStudioSelectedTagRow.overlay) return toast("Core-теги нельзя перемещать в Tag Studio");
  const toCategoryId = document.getElementById("tagstudio-move-category")?.value || "";
  const toSubcategoryId = document.getElementById("tagstudio-move-subcategory")?.value || "";
  const moveSubcategory = document.getElementById("tagstudio-move-subcategory");
  if (!toCategoryId) return toast("Выберите category назначения");
  if (moveSubcategory?.dataset.hasSubcategories === "1" && !toSubcategoryId) {
    return toast("Выберите подгруппу назначения");
  }
  const fromCategoryId = tagStudioSelectedTagRow.category_id;
  const itemId = tagStudioSelectedTagRow.item.id;
  await api(`/categories/${encodeURIComponent(fromCategoryId)}/items/${encodeURIComponent(itemId)}/move`, {
    method: "POST",
    body: JSON.stringify({
      to_category_id: toCategoryId,
      to_subcategory_id: toSubcategoryId || null,
      persist: true,
      source: "user",
    }),
  });
  toast("Тег перенесен");
  await Promise.all([loadTagStudioLister(), loadTagStudioPanel()]);
}

async function handleTagStudioReactivateTag() {
  if (!tagStudioSelectedTagRow) return toast("Сначала выберите тег");
  if (!tagStudioSelectedTagRow.overlay) return toast("Core-теги нельзя восстанавливать в Tag Studio");
  const row = tagStudioSelectedTagRow;
  const subgroup = getTagStudioRowSubcategory(row) || "none";
  const path = `${row.category_id} — ${subgroup}`;
  const ok = window.confirm(`Восстановить тег "${row.item.label}" в ${path}?`);
  if (!ok) return;
  await api(`/categories/${encodeURIComponent(row.category_id)}/items/${encodeURIComponent(row.item.id)}`, {
    method: "PUT",
    body: JSON.stringify({ is_active: true, persist: true, source: "user" }),
  });
  toast(`Тег восстановлен в ${path}`);
  await Promise.all([loadTagStudioLister(), loadTagStudioPanel()]);
}

function closeEditTagModal() {
  const modal = document.getElementById("edit-tag-modal");
  modal?.classList.add("hidden");
  setEditTagModalReadOnly(false);
}

const EDIT_TAG_FIELD_IDS = [
  "edit-tag-label",
  "edit-tag-aliases",
  "edit-tag-description",
  "edit-tag-default-weight",
  "edit-tag-illustrious",
  "edit-tag-anima",
  "edit-tag-zimage",
  "edit-tag-subgroup",
];

async function fillEditTagSubgroups(categoryId) {
  const subgroupInput = document.getElementById("edit-tag-subgroup");
  const datalist = document.getElementById("edit-tag-subgroup-options");
  if (!subgroupInput) return [];
  const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
  const subgroups = collectKnownSubgroups(categoryId, data);
  if (datalist) datalist.innerHTML = subgroups.map((s) => `<option value="${escapeHtml(s)}"></option>`).join("");
  return subgroups;
}

function setEditTagModalReadOnly(readOnly, showCoreHint = false) {
  const saveBtn = document.getElementById("edit-tag-save");
  const hint = document.getElementById("edit-tag-readonly-hint");
  for (const id of EDIT_TAG_FIELD_IDS) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.readOnly = readOnly;
    el.disabled = readOnly;
  }
  saveBtn?.classList.toggle("hidden", readOnly);
  hint?.classList.toggle("hidden", !showCoreHint);
}

async function openEditTagModal() {
  if (!tagStudioSelectedTagRow) return toast("Сначала выберите тег");
  const row = tagStudioSelectedTagRow;
  if (row.item?.meta?.is_active === false) {
    return toast("Сначала восстановите тег (Reactivate)");
  }
  const item = row.item;
  const isCore = !row.overlay;
  document.getElementById("edit-tag-label").value = item.label || "";
  document.getElementById("edit-tag-aliases").value = Array.isArray(item.meta?.aliases) ? item.meta.aliases.join(", ") : "";
  document.getElementById("edit-tag-description").value = item.meta?.description || "";
  document.getElementById("edit-tag-default-weight").value = String(item.default_weight ?? 1.0);
  document.getElementById("edit-tag-illustrious").value = item.tags?.illustrious || "";
  document.getElementById("edit-tag-anima").value = item.tags?.anima || "";
  document.getElementById("edit-tag-zimage").value = item.tags?.zimage_turbo || item.tags?.zimage || "";

  const categorySelect = document.getElementById("edit-tag-category");
  const subgroupInput = document.getElementById("edit-tag-subgroup");
  const coreHint = document.getElementById("edit-tag-core-category-hint");
  const categories = await loadAddTagCategories();
  if (categorySelect) {
    categorySelect.innerHTML = "";
    for (const category of categories) {
      const option = document.createElement("option");
      option.value = category.id;
      option.textContent = `${category.title} (${category.id})`;
      categorySelect.appendChild(option);
    }
    categorySelect.value = row.category_id;
    // Moving between categories is only meaningful for runtime (overlay)
    // tags — same restriction as the standalone "Move tag" button. Core
    // tags can still have their subgroup changed (it forks to a runtime
    // copy on save, same as editing any other field on a core tag).
    categorySelect.disabled = isCore;
  }
  coreHint?.classList.toggle("hidden", !isCore);
  await fillEditTagSubgroups(row.category_id);
  if (subgroupInput) subgroupInput.value = getTagStudioRowSubcategory(row);

  const title = document.getElementById("edit-tag-modal-title");
  if (title) title.textContent = isCore ? "Edit tag (core → runtime)" : "Edit tag";
  setEditTagModalReadOnly(false, isCore);
  document.getElementById("edit-tag-modal")?.classList.remove("hidden");
}

async function saveEditTagFromModal(event) {
  event?.preventDefault();
  if (!tagStudioSelectedTagRow) return;
  const row = tagStudioSelectedTagRow;
  const wasCore = !row.overlay;
  const label = document.getElementById("edit-tag-label")?.value.trim() || "";
  const aliasesRaw = document.getElementById("edit-tag-aliases")?.value || "";
  const aliases = aliasesRaw.split(",").map((x) => x.trim()).filter(Boolean);
  const description = document.getElementById("edit-tag-description")?.value.trim() || null;
  const defaultWeight = Number.parseFloat(document.getElementById("edit-tag-default-weight")?.value || "1.0");
  const tags = {
    illustrious: document.getElementById("edit-tag-illustrious")?.value.trim() || "",
    anima: document.getElementById("edit-tag-anima")?.value.trim() || "",
    zimage_turbo: document.getElementById("edit-tag-zimage")?.value.trim() || "",
  };
  const newCategoryId = document.getElementById("edit-tag-category")?.value || row.category_id;
  const newSubgroup = document.getElementById("edit-tag-subgroup")?.value.trim() || "";
  // Category change is only offered (the select is enabled) for runtime
  // tags — same restriction as the standalone Move tag button. wasCore is
  // double-checked here too in case the field somehow ends up enabled.
  const categoryChanging = !wasCore && newCategoryId && newCategoryId !== row.category_id;
  if (!label) return toast("Введите label");
  if (Number.isNaN(defaultWeight) || defaultWeight <= 0) return toast("Укажите корректный default weight");

  const putBody = {
    label,
    aliases,
    description,
    default_weight: defaultWeight,
    tags,
    persist: true,
    source: "user",
  };
  if (!categoryChanging) {
    // Subgroup change within the same category — the PUT endpoint already
    // supports this directly (and forks core tags to a runtime copy first).
    putBody.subcategory_id = newSubgroup;
    putBody.allow_new_subcategory = true;
  }
  await api(`/categories/${encodeURIComponent(row.category_id)}/items/${encodeURIComponent(row.item.id)}`, {
    method: "PUT",
    body: JSON.stringify(putBody),
  });

  if (categoryChanging) {
    // Cross-category move has to go through the dedicated move endpoint
    // (the PUT above only ever touches the item within its current
    // category) — call it after the PUT so we're moving the exact item
    // id the PUT just confirmed exists, with the same single Save click
    // also carrying the new subgroup along.
    await api(`/categories/${encodeURIComponent(row.category_id)}/items/${encodeURIComponent(row.item.id)}/move`, {
      method: "POST",
      body: JSON.stringify({
        to_category_id: newCategoryId,
        to_subcategory_id: newSubgroup || null,
        persist: true,
        source: "user",
      }),
    });
  }

  closeEditTagModal();
  if (categoryChanging) {
    toast("Тег обновлён и перенесён в новую категорию/подгруппу");
  } else {
    toast(wasCore ? "Сохранено как runtime-копия поверх core-тега" : "Тег обновлён");
  }
  await Promise.all([loadTagStudioLister(), loadTagStudioPanel()]);
}

async function handleTagStudioDeleteTag() {
  if (!tagStudioSelectedTagRow) return toast("Сначала выберите тег");
  if (!tagStudioSelectedTagRow.overlay) return toast("Core-теги нельзя удалять в Tag Studio");
  const row = tagStudioSelectedTagRow;
  const subgroup = getTagStudioRowSubcategory(row) || "none";
  const ok = window.confirm(`Удалить тег "${row.item.label}" из ${row.category_id} — ${subgroup}?`);
  if (!ok) return;
  await api(`/categories/${encodeURIComponent(row.category_id)}/items/${encodeURIComponent(row.item.id)}/deactivate?persist=true`, {
    method: "POST",
  });
  toast("Тег удален (deactivate)");
  tagStudioSelectedTagRow = null;
  await Promise.all([loadTagStudioLister(), loadTagStudioPanel()]);
}

async function initTagStudioLister() {
  if (tagStudioListerInitialized) return;
  tagStudioListerInitialized = true;
  await loadTagStudioCategorySelects();
  const listerCategory = document.getElementById("tagstudio-lister-category");
  const listerSubcategory = document.getElementById("tagstudio-lister-subcategory");
  const moveCategory = document.getElementById("tagstudio-move-category");
  const loadBtn = document.getElementById("btn-tagstudio-lister-load");
  await loadTagStudioSubcategorySelect(listerCategory?.value || "", listerSubcategory, {
    anyLabel: "Все подгруппы",
    noneLabel: "none",
    includeAny: true,
  });
  await syncTagStudioMoveSubcategory(moveCategory?.value || "", "");
  listerCategory?.addEventListener("change", async () => {
    await loadTagStudioSubcategorySelect(listerCategory.value, listerSubcategory, {
      anyLabel: "Все подгруппы",
      noneLabel: "none",
      includeAny: true,
    });
    await loadTagStudioLister();
  });
  listerSubcategory?.addEventListener("change", () => {
    loadTagStudioLister().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("tagstudio-lister-active-only")?.addEventListener("change", () => {
    loadTagStudioLister().catch((e) => toast("Ошибка: " + e.message));
  });
  moveCategory?.addEventListener("change", () => {
    syncTagStudioMoveSubcategory(moveCategory.value, "").catch((e) => toast("Ошибка: " + e.message));
  });
  loadBtn?.addEventListener("click", () => {
    loadTagStudioLister().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-save-description")?.addEventListener("click", () => {
    handleTagStudioSaveDescription().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-move-tag")?.addEventListener("click", () => {
    if (document.getElementById("btn-tagstudio-move-tag")?.disabled) {
      return toast(tagStudioSelectedTagRow?.overlay
        ? "Сначала восстановите тег (Reactivate)"
        : "Core-теги нельзя перемещать в Tag Studio");
    }
    handleTagStudioMoveTag().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-delete-tag")?.addEventListener("click", () => {
    if (document.getElementById("btn-tagstudio-delete-tag")?.disabled) {
      return toast("Core-теги нельзя удалять в Tag Studio");
    }
    handleTagStudioDeleteTag().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-reactivate-tag")?.addEventListener("click", () => {
    handleTagStudioReactivateTag().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-edit-tag")?.addEventListener("click", () => {
    openEditTagModal().catch((e) => toast("Ошибка: " + e.message));
  });
  await loadTagStudioLister();
}

function initPromptingTree() {
  const treeEl = document.getElementById("prompting-tree");
  if (!treeEl) return;
  treeEl.innerHTML = "";
  for (const node of PROMPTING_TREE) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "outfit-tree-item" + (node.id === activePromptingLeafId ? " active" : "");
    btn.textContent = node.label;
    btn.onclick = () => {
      activePromptingLeafId = node.id;
      initPromptingTree();
      showPromptingSubpanel(node);
    };
    treeEl.appendChild(btn);
  }
}

function showPromptingSubpanel(node) {
  document.getElementById("prompting-detail-title").textContent = node.label;
  document.getElementById("prompting-detail-hint").textContent = node.hint;
  for (const id of ["analyze", "import", "nsfw"]) {
    const el = document.getElementById(`prompting-panel-${id}`);
    if (el) el.classList.toggle("hidden", node.panel !== id);
  }
  if (node.panel === "import") refreshPromptingOverlayStats();
  if (node.panel === "nsfw") {
    initPromptingNsfwIntensity();
    bindNsfwUserRewriteUi();
  }
}

function bindNsfwUserRewriteUi() {
  const toggle = document.getElementById("prompt-nsfw-user-rewrite");
  if (!toggle || toggle.dataset.bound) return;
  toggle.dataset.bound = "1";
  toggle.addEventListener("change", syncNsfwUserRewriteUi);
  syncNsfwUserRewriteUi();
}

function syncNsfwUserRewriteUi() {
  const useUser = Boolean(document.getElementById("prompt-nsfw-user-rewrite")?.checked);
  const wrap = document.getElementById("prompt-nsfw-user-wrap");
  const keepLocked = document.getElementById("prompt-nsfw-keep-locked")?.closest(".check-row");
  const identityHint = document.getElementById("prompt-nsfw-identity-hint");
  if (wrap) wrap.classList.toggle("hidden", !useUser);
  if (keepLocked) keepLocked.classList.toggle("hidden", useUser);
  if (identityHint) identityHint.classList.toggle("hidden", useUser);
}

function initPromptingNsfwIntensity() {
  const row = document.getElementById("prompting-intensity-chips");
  if (!row || row.dataset.bound) return;
  row.dataset.bound = "1";
  const items = [
    { id: "low", label: "Low" },
    { id: "medium", label: "Medium" },
    { id: "high", label: "High" },
    { id: "extreme", label: "Extreme" },
  ];
  renderChips(row, items, activeNsfwIntensity, (v) => {
    activeNsfwIntensity = v || "medium";
  });
}

function initPromptingPanel() {
  initPromptingTree();
  const node = PROMPTING_TREE.find((n) => n.id === activePromptingLeafId) || PROMPTING_TREE[0];
  showPromptingSubpanel(node);
  const src = document.getElementById("prompting-source-model");
  const tgt = document.getElementById("prompting-target-model");
  if (src && !src.dataset.bound) {
    src.dataset.bound = "1";
    src.value = state.model_id;
    tgt.value = state.model_id;
    tgt.addEventListener("change", syncPromptZitLlmVisibility);
  }
  syncPromptZitLlmVisibility();
  applyLlmAvailabilityToPrompting();
}

function syncPromptZitLlmVisibility() {
  const target = document.getElementById("prompting-target-model")?.value;
  const wrap = document.getElementById("prompt-zit-llm-wrap");
  if (!wrap) return;
  wrap.classList.toggle("hidden", target !== "zimage_turbo");
}

function applyLlmAvailabilityToPrompting() {
  const nsfw = document.getElementById("prompt-nsfw-llm");
  const rewrite = document.getElementById("prompt-nsfw-rewrite");
  const userRewrite = document.getElementById("prompt-nsfw-user-rewrite");
  const imp = document.getElementById("prompt-import-use-llm");
  const zit = document.getElementById("prompt-zit-use-llm");
  const status = llmSettingsCache?.health || {};
  const enabled = Boolean(llmSettingsCache?.settings?.enabled);
  const healthy = Boolean(status.ok);
  const reason = !enabled
    ? "LLM disabled in Advanced settings"
    : healthy
      ? ""
      : (status.error || "LLM health check failed");
  for (const el of [nsfw, rewrite, userRewrite, imp, zit]) {
    if (!el) continue;
    el.disabled = !(enabled && healthy);
    el.title = reason;
    if (el.disabled) el.checked = false;
  }
  syncPromptZitLlmVisibility();
}

function renderNsfwStylerReport(data) {
  const badge = document.getElementById("prompting-nsfw-llm-badge");
  const unknownEl = document.getElementById("prompting-nsfw-unknown");
  if (badge) {
    let statusText = "Rules only";
    if (data.used_llm) {
      if (data.llm_mode === "user") statusText = "User prompt rewrite applied";
      else if (data.llm_mode === "rewrite") statusText = "LLM full rewrite applied";
      else statusText = "LLM refine applied";
    } else if (data.use_llm || data.llm_mode === "rewrite" || data.llm_mode === "user") {
      statusText = "Rules only";
    }
    if (data.llm_error) statusText += ` · ${data.llm_error}`;
    else if (!data.used_llm && (document.getElementById("prompt-nsfw-llm")?.checked || document.getElementById("prompt-nsfw-rewrite")?.checked || document.getElementById("prompt-nsfw-user-rewrite")?.checked)) {
      const err = data.llm_status?.last_error;
      if (err) statusText += ` · ${err}`;
    }
    badge.textContent = statusText;
  }
  if (unknownEl) {
    const unknown = data.unknown_phrases || [];
    if (unknown.length) {
      unknownEl.classList.remove("hidden");
      unknownEl.textContent = `Не в каталоге (${unknown.length}): ${unknown.slice(0, 8).join(" · ")}${unknown.length > 8 ? " …" : ""}`;
    } else {
      unknownEl.classList.add("hidden");
      unknownEl.textContent = "";
    }
  }
}

function readLlmFormSettings() {
  const modelSelect = document.getElementById("llm-model-select");
  const modelCustom = document.getElementById("llm-model-custom");
  return {
    enabled: Boolean(document.getElementById("llm-enabled")?.checked),
    base_url: (document.getElementById("llm-base-url")?.value || "").trim() || "http://127.0.0.1:11434",
    model: (modelCustom?.value || "").trim() || modelSelect?.value || "llama3",
    temperature: Number(document.getElementById("llm-temperature")?.value || 0.3),
    top_p: Number(document.getElementById("llm-top-p")?.value || 0.9),
    timeout: Number(document.getElementById("llm-timeout")?.value || 30),
    max_retries: Number(document.getElementById("llm-retries")?.value || 1),
    health_ttl_seconds: 45,
  };
}

function renderLlmStatus(health, warning = "") {
  const badge = document.getElementById("llm-status-badge");
  if (!badge) return;
  if (!health) {
    badge.textContent = "—";
    return;
  }
  const statusText = health.ok
    ? `Online · ${health.latency_ms ?? "?"}ms`
    : `Offline · ${health.error || "Unknown error"}`;
  badge.textContent = warning ? `${statusText} · ${warning}` : statusText;
}

function fillLlmSettingsForm(settings, models = []) {
  document.getElementById("llm-enabled").checked = Boolean(settings?.enabled);
  document.getElementById("llm-base-url").value = settings?.base_url || "http://127.0.0.1:11434";
  document.getElementById("llm-temperature").value = settings?.temperature ?? 0.3;
  document.getElementById("llm-top-p").value = settings?.top_p ?? 0.9;
  document.getElementById("llm-timeout").value = settings?.timeout ?? 30;
  document.getElementById("llm-retries").value = settings?.max_retries ?? 1;
  const modelSelect = document.getElementById("llm-model-select");
  if (modelSelect) {
    modelSelect.innerHTML = "";
    const source = models.length ? models : [settings?.model || "llama3"];
    for (const model of source) {
      const opt = document.createElement("option");
      opt.value = model;
      opt.textContent = model;
      modelSelect.appendChild(opt);
    }
    modelSelect.value = settings?.model || source[0] || "llama3";
  }
  document.getElementById("llm-model-custom").value = "";
}

async function refreshLlmModels() {
  const baseUrl = (document.getElementById("llm-base-url")?.value || "").trim();
  const query = baseUrl ? `?base_url=${encodeURIComponent(baseUrl)}` : "";
  const data = await api(`/llm/models${query}`);
  const models = data.models || [];
  const modelSelect = document.getElementById("llm-model-select");
  if (!modelSelect) return;
  const current = modelSelect.value;
  modelSelect.innerHTML = "";
  if (!models.length) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = "No models";
    modelSelect.appendChild(opt);
    return;
  }
  for (const model of models) {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    modelSelect.appendChild(opt);
  }
  modelSelect.value = models.includes(current) ? current : models[0];
}

async function loadLlmSettingsCard() {
  try {
    const data = await api("/llm/settings");
    llmSettingsCache = data;
    fillLlmSettingsForm(data.settings || {}, data.health?.models_available || []);
    renderLlmStatus(data.health);
    applyLlmAvailabilityToPrompting();
  } catch (e) {
    renderLlmStatus({ ok: false, error: e.message });
  }
}

async function refreshPromptingOverlayStats() {
  const el = document.getElementById("prompting-overlay-stats");
  if (!el) return;
  try {
    const data = await api("/prompt/import/runtime-items?limit=50");
    el.textContent = JSON.stringify(data.overlay || {}, null, 2);
  } catch (_) {
    el.textContent = "—";
  }
}

function renderPromptingImportReport(data) {
  const stats = document.getElementById("prompting-import-stats");
  const list = document.getElementById("prompting-import-list");
  if (!stats || !list) return;
  const report = data.report || {};
  const merge = data.merge_report || {};
  stats.textContent = `Matched: ${report.matched_count ?? 0} · Unknown: ${report.unknown_count ?? 0} · Added: ${merge.added?.length ?? 0} · Deduped: ${data.deduped?.length ?? 0}`;
  const lines = [];
  for (const m of report.matched || []) {
    lines.push(`<li><span class="import-tag">${escapeHtml(m.label)}</span> <span class="import-meta">${escapeHtml(m.field_path)}</span></li>`);
  }
  for (const u of report.unknown || []) {
    lines.push(`<li class="import-report-unknown">${escapeHtml(u)}</li>`);
  }
  list.innerHTML = lines.length ? lines.join("") : "<li class='import-empty'>—</li>";
}

let advancedMetaLoaded = false;
let activeRulesSlot = "general";
let activeRulesProfileId = "default";
let currentRulesProfiles = [];

const RULES_SLOTS = [
  { id: "general", label: "General" },
  { id: "model:illustrious", label: "Illustrious Gen" },
  { id: "model:anima", label: "Anima Gen" },
  { id: "model:zimage_turbo", label: "ZIT Gen" },
];

function rulesSlotLabel(slotId) {
  return RULES_SLOTS.find((s) => s.id === slotId)?.label || slotId;
}

function renderRulesSlotChips() {
  const row = document.getElementById("rules-slot-chips");
  if (!row) return;
  row.innerHTML = "";
  for (const slot of RULES_SLOTS) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip" + (slot.id === activeRulesSlot ? " active" : "");
    chip.textContent = slot.label;
    chip.onclick = () => selectRulesSlot(slot.id);
    row.appendChild(chip);
  }
}

function renderRulesProfileChips(profiles = []) {
  currentRulesProfiles = profiles;
  const row = document.getElementById("rules-profile-chips");
  if (!row) return;
  row.innerHTML = "";
  if (!profiles.length) return;
  for (const profile of profiles) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip" + (profile.id === activeRulesProfileId ? " active" : "");
    chip.textContent = profile.label || profile.id;
    chip.onclick = () => selectRulesProfile(profile.id);
    row.appendChild(chip);
  }
  updateRulesProfileDeleteButton();
}

function updateRulesProfileDeleteButton() {
  const btn = document.getElementById("btn-rules-delete-profile");
  const nameInput = document.getElementById("rules-profile-name");
  if (!btn) return;
  const selected = currentRulesProfiles.find((p) => p.id === activeRulesProfileId);
  const canDelete = Boolean(selected && selected.deletable);
  btn.disabled = !canDelete;
  btn.title = canDelete ? "" : "Можно удалить только пользовательский профиль";
  if (nameInput) {
    const isDefault = activeRulesProfileId === "default";
    nameInput.placeholder = isDefault ? "Name for new rule" : "Rule name";
    nameInput.disabled = false;
    if (!isDefault && selected?.label) {
      nameInput.value = selected.label;
    } else if (isDefault && nameInput.dataset.keepName !== "1") {
      nameInput.value = "";
    }
    delete nameInput.dataset.keepName;
  }
}

function activeRulesProfileLabel() {
  const selected = currentRulesProfiles.find((p) => p.id === activeRulesProfileId);
  if (selected?.label) return selected.label;
  return activeRulesProfileId === "default" ? "Use default" : activeRulesProfileId;
}

function renderRulesMeta(summary) {
  const el = document.getElementById("rules-meta");
  if (!el) return;
  if (!summary) {
    el.innerHTML = "";
    return;
  }
  const title = summary.meta?.title || rulesSlotLabel(summary.slot);
  const sourceKind = summary.source_kind || "default";
  const sourceLabel =
    sourceKind === "user" ? "Custom rule" : sourceKind === "legacy" ? "Legacy default" : "Built-in default";
  const profileLabel = summary.profile_name || activeRulesProfileLabel();
  const counts = [];
  if (summary.penalty_count) counts.push(`${summary.penalty_count} penalties`);
  if (summary.bonus_count) counts.push(`${summary.bonus_count} bonuses`);
  if (summary.has_format) counts.push("format rules");
  el.innerHTML = `
    <span class="rules-meta-badge ${sourceKind === "user" ? "user" : ""}">${sourceLabel}</span>
    <span class="rules-meta-badge">${profileLabel}</span>
    <span class="rules-meta-badge">${title}</span>
    ${counts.length ? `<span class="rules-meta-badge">${counts.join(" · ")}</span>` : ""}
  `;
}

async function loadRulesSlot(slotId) {
  const textarea = document.getElementById("rules-yaml");
  if (!textarea) return;
  textarea.placeholder = "Loading…";
  try {
    const data = await api(`/rules/${encodeURIComponent(slotId)}`);
    activeRulesProfileId = data.active_profile_id || data.source_profile_id || "default";
    renderRulesProfileChips(data.profiles || []);
    renderRulesMeta(data);
    textarea.value = data.yaml || "";
    textarea.placeholder = "";
  } catch (e) {
    activeRulesProfileId = "default";
    currentRulesProfiles = [];
    renderRulesProfileChips([]);
    renderRulesMeta(null);
    textarea.value = "";
    textarea.placeholder = `Failed to load: ${e.message}`;
  }
}

async function loadRulesPanel() {
  renderRulesSlotChips();
  await loadRulesSlot(activeRulesSlot);
}

function selectRulesSlot(slotId) {
  activeRulesSlot = slotId;
  activeRulesProfileId = "default";
  renderRulesSlotChips();
  loadRulesSlot(slotId);
}

async function selectRulesProfile(profileId) {
  try {
    const summary = await api("/rules/select", {
      method: "POST",
      body: JSON.stringify({ slot: activeRulesSlot, profile_id: profileId }),
    });
    activeRulesProfileId = summary.source_profile_id || profileId;
    await loadRulesSlot(activeRulesSlot);
    renderRulesMeta(summary);
    toast(`Rules: ${activeRulesProfileLabel()}`);
    refreshConflictWarnings();
    refreshQualityScore();
  } catch (e) {
    toast(`Rules error: ${e.message}`);
  }
}

async function deleteRulesProfile() {
  if (activeRulesProfileId === "default") {
    toast("Built-in default cannot be deleted");
    return;
  }
  const profileLabel = activeRulesProfileLabel();
  if (!window.confirm(`Delete rule profile «${profileLabel}»?`)) return;
  try {
    const summary = await api("/rules/delete", {
      method: "POST",
      body: JSON.stringify({ slot: activeRulesSlot, profile_id: activeRulesProfileId }),
    });
    activeRulesProfileId = "default";
    await loadRulesSlot(activeRulesSlot);
    renderRulesMeta(summary);
    toast(`Deleted: ${profileLabel}`);
    refreshConflictWarnings();
    refreshQualityScore();
  } catch (e) {
    toast(`Rules error: ${e.message}`);
  }
}

async function saveRulesYaml() {
  const yamlText = document.getElementById("rules-yaml")?.value || "";
  const nameInput = document.getElementById("rules-profile-name");
  const ruleName = (nameInput?.value || "").trim();
  if (!yamlText.trim()) return toast("YAML is empty");
  const creatingNew = activeRulesProfileId === "default";
  if (creatingNew && !ruleName) return toast("Enter a name for the new rule");
  try {
    const summary = await api("/rules/upload", {
      method: "POST",
      body: JSON.stringify({
        slot: activeRulesSlot,
        yaml: yamlText,
        profile_id: activeRulesProfileId,
        name: ruleName || null,
      }),
    });
    activeRulesProfileId = summary.source_profile_id || activeRulesProfileId;
    await loadRulesSlot(activeRulesSlot);
    renderRulesMeta(summary);
    toast(creatingNew ? `Created: ${ruleName}` : `Saved: ${activeRulesProfileLabel()}`);
    refreshConflictWarnings();
    refreshQualityScore();
  } catch (e) {
    toast(`Rules error: ${e.message}`);
  }
}

async function useDefaultRules() {
  if (activeRulesProfileId === "default") return;
  await selectRulesProfile("default");
}

function loadRulesFromFile() {
  document.getElementById("rules-file-input")?.click();
}

function handleRulesFileSelected(event) {
  const input = event.target;
  const file = input.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    const textarea = document.getElementById("rules-yaml");
    if (textarea) textarea.value = String(reader.result || "");
    const nameInput = document.getElementById("rules-profile-name");
    if (nameInput && activeRulesProfileId === "default" && !nameInput.value.trim()) {
      const stem = file.name.replace(/\.(ya?ml|txt)$/i, "").replace(/[_-]+/g, " ").trim();
      if (stem) {
        nameInput.value = stem;
        nameInput.dataset.keepName = "1";
      }
    }
    toast(`Loaded: ${file.name}`);
    input.value = "";
  };
  reader.readAsText(file, "utf-8");
}

function downloadRulesYaml() {
  const yamlText = document.getElementById("rules-yaml")?.value || "";
  if (!yamlText.trim()) return toast("Nothing to download");
  const safeName = activeRulesSlot.replace(":", "_");
  const blob = new Blob([yamlText], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `egodary-rules-${safeName}.yaml`;
  link.click();
  URL.revokeObjectURL(url);
  toast("YAML downloaded");
}

async function loadPluginsPanel() {
  const el = document.getElementById("plugins-list");
  if (!el) return;
  el.innerHTML = "Loading…";
  try {
    const data = await api("/plugins");
    const plugins = data.plugins || [];
    if (!plugins.length) {
      el.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Нет drop-in плагинов в plugins_user/.</span>';
      return;
    }
    el.innerHTML = plugins.map(pluginRowHtml).join("");
    bindPluginsEvents();
  } catch (e) {
    el.innerHTML = `<span style="color:#eb3b5a;font-size:12px">Failed to load plugins: ${escapeHtml(e.message)}</span>`;
  }
}

function pluginRowHtml(p) {
  const disabledCls = p.enabled ? "" : " disabled";
  const errorHtml = p.error ? `<div class="plugin-row-error">⚠ ${escapeHtml(p.error)}</div>` : "";
  return `
    <div class="plugin-row${disabledCls}" data-plugin-id="${escapeHtml(p.id)}">
      <input type="checkbox" class="plugin-toggle" data-plugin-id="${escapeHtml(p.id)}" ${p.enabled ? "checked" : ""} title="Включить/выключить плагин" />
      <div class="plugin-row-info">
        <div class="plugin-row-name">${escapeHtml(p.name)} <span class="plugin-row-version">v${escapeHtml(p.version)}</span></div>
        <div class="plugin-row-meta">${escapeHtml(p.id)} · ${escapeHtml(p.kind)}${p.has_ui ? " · UI" : ""}</div>
        ${errorHtml}
      </div>
    </div>`;
}

function bindPluginsEvents() {
  document.querySelectorAll(".plugin-toggle").forEach((cb) => {
    cb.onchange = async () => {
      const id = cb.dataset.pluginId;
      const enabled = cb.checked;
      cb.disabled = true;
      try {
        await api(`/plugins/${encodeURIComponent(id)}/${enabled ? "enable" : "disable"}`, { method: "POST" });
        toast(`${enabled ? "Включён" : "Отключён"}: ${id}. Требуется перезапуск сервера (см. кнопку слева).`);
        cb.closest(".plugin-row")?.classList.toggle("disabled", !enabled);
      } catch (e) {
        toast("Ошибка: " + e.message);
        cb.checked = !enabled;
      } finally {
        cb.disabled = false;
      }
    };
  });
}

async function loadDebugPanel() {
  const el = document.getElementById("debug-output");
  if (!el) return;
  try {
    const data = await api("/debug");
    el.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    el.textContent = `Failed to load debug snapshot: ${e.message}`;
  }
}

async function loadChangelogPanel() {
  const el = document.getElementById("changelog-output");
  if (!el) return;
  try {
    const data = await api("/changelog");
    el.textContent = data.markdown || "";
  } catch (e) {
    el.textContent = `Failed to load changelog: ${e.message}`;
  }
}

async function waitForServerHealth(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${API}/health`, { cache: "no-store" });
      if (response.ok) return true;
    } catch {
      // expected while the worker is restarting
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  return false;
}

async function restartServer() {
  if (!window.confirm("Перезапустить сервер? Текущие запросы могут прерваться.")) return;
  const button = document.getElementById("btn-restart-server");
  if (button) button.disabled = true;
  try {
    try {
      await api("/server/restart", { method: "POST" });
    } catch {
      // connection may drop as the worker exits
    }
    toast("Restarting server…");
    const ok = await waitForServerHealth();
    advancedMetaLoaded = false;
    if (ok) {
      toast("Server is back");
      await loadAdvancedMeta();
    } else {
      toast("Server did not respond — use restart.bat");
    }
  } catch (e) {
    toast(`Restart failed: ${e.message}`);
  } finally {
    if (button) button.disabled = false;
  }
}

async function loadLlmPanel() {
  await loadLlmSettingsCard();
}

async function loadAdvancedMeta() {
  if (!advancedMetaLoaded) {
    advancedMetaLoaded = true;
    await Promise.all([loadPluginsPanel(), loadDebugPanel(), loadChangelogPanel()]);
  }
  await Promise.all([loadRulesPanel(), loadAdvancedTodoPanel()]);
}

function scheduleAdvancedTodoSave() {
  clearTimeout(advancedTodoSaveTimer);
  advancedTodoSaveTimer = setTimeout(async () => {
    try {
      await api("/advanced/todo", {
        method: "PUT",
        body: JSON.stringify({ items: advancedTodoItems }),
      });
    } catch (e) {
      toast("Todo save error: " + e.message);
    }
  }, 400);
}

function createTodoId() {
  return `todo_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function syncAdvancedTodoDueControls() {
  const noDue = document.getElementById("advanced-todo-no-due")?.checked ?? true;
  const dueInput = document.getElementById("advanced-todo-due");
  const calBtn = document.getElementById("btn-advanced-todo-open-calendar");
  if (dueInput) {
    dueInput.disabled = noDue;
    if (noDue) dueInput.value = "";
  }
  if (calBtn) calBtn.disabled = noDue;
}

function openAdvancedTodoCalendar(dueInput) {
  if (!dueInput || dueInput.disabled) return;
  if (typeof dueInput.showPicker === "function") {
    try {
      dueInput.showPicker();
      return;
    } catch (_) {
      /* showPicker may require user gesture */
    }
  }
  dueInput.focus();
  dueInput.click();
}

function resetAdvancedTodoComposeForm() {
  const input = document.getElementById("advanced-todo-input");
  if (input) input.value = "";
  const noDue = document.getElementById("advanced-todo-no-due");
  if (noDue) noDue.checked = true;
  syncAdvancedTodoDueControls();
}

function isTodoOverdue(item) {
  if (!item?.due_date || item.done) return false;
  const today = new Date().toISOString().slice(0, 10);
  return item.due_date < today;
}

function normalizeTodoSortOrder() {
  advancedTodoItems.forEach((item, idx) => {
    item.sort_order = idx;
  });
}

function sortTodoItems(items) {
  return [...items].sort((a, b) => {
    const doneDiff = Number(Boolean(a.done)) - Number(Boolean(b.done));
    if (doneDiff !== 0) return doneDiff;
    const orderDiff = (a.sort_order ?? 0) - (b.sort_order ?? 0);
    if (orderDiff !== 0) return orderDiff;
    return String(a.created_at || "").localeCompare(String(b.created_at || ""));
  });
}

function markTodoItemComplete(itemId) {
  const idx = advancedTodoItems.findIndex((row) => row.id === itemId);
  if (idx < 0) return;
  const item = advancedTodoItems[idx];
  if (item.done) return;
  item.done = true;
  advancedTodoItems.splice(idx, 1);
  const firstDoneIdx = advancedTodoItems.findIndex((row) => row.done);
  if (firstDoneIdx < 0) {
    advancedTodoItems.push(item);
  } else {
    advancedTodoItems.splice(firstDoneIdx, 0, item);
  }
  normalizeTodoSortOrder();
}

function markTodoItemReopen(itemId) {
  const idx = advancedTodoItems.findIndex((row) => row.id === itemId);
  if (idx < 0) return;
  const item = advancedTodoItems[idx];
  if (!item.done) return;
  item.done = false;
  advancedTodoItems.splice(idx, 1);
  const firstDoneIdx = advancedTodoItems.findIndex((row) => row.done);
  const insertAt = firstDoneIdx < 0 ? advancedTodoItems.length : firstDoneIdx;
  advancedTodoItems.splice(insertAt, 0, item);
  normalizeTodoSortOrder();
}

function renderAdvancedTodoList() {
  const root = document.getElementById("advanced-todo-list");
  if (!root) return;
  const sorted = sortTodoItems(advancedTodoItems);
  if (!sorted.length) {
    root.innerHTML = '<div class="tagstudio-output-empty">Список пуст.</div>';
    return;
  }
  root.innerHTML = sorted.map((item, index) => {
    const priority = item.priority || "medium";
    const noDue = !item.due_date;
    const overdueClass = !noDue && isTodoOverdue(item) ? " todo-overdue" : "";
    const doneClass = item.done ? " is-done" : "";
    const actionButtons = item.done
      ? `<button type="button" class="btn-ghost btn-sm todo-reopen" data-id="${escapeHtml(item.id)}" title="Вернуть в активные" aria-label="Вернуть в активные">↩</button>`
      : `<button type="button" class="btn-ghost btn-sm todo-complete" data-id="${escapeHtml(item.id)}" title="Выполнено" aria-label="Выполнено">✓</button>`;
    return `
      <div class="todo-item${doneClass}" draggable="true" data-id="${escapeHtml(item.id)}" data-index="${index}">
        <span class="todo-drag-handle" title="Drag to reorder">⋮⋮</span>
        <span class="todo-text${item.done ? " is-done" : ""}">${escapeHtml(item.text)}</span>
        <span class="todo-priority todo-priority-${priority}">${priority}</span>
        <div class="todo-due-controls${overdueClass}">
          <input type="date" class="todo-due-input" data-id="${escapeHtml(item.id)}" value="${escapeHtml(item.due_date || "")}" ${noDue ? "disabled" : ""} />
          <button type="button" class="btn-ghost btn-sm todo-due-calendar" data-id="${escapeHtml(item.id)}" title="Календарь" aria-label="Календарь" ${noDue ? "disabled" : ""}>📅</button>
          <label class="todo-no-due-inline" title="Без срока">
            <input type="checkbox" class="todo-no-due-check" data-id="${escapeHtml(item.id)}" ${noDue ? "checked" : ""} />
            <span class="todo-no-due-label">Без срока</span>
          </label>
        </div>
        <div class="todo-actions">
          ${actionButtons}
          <button type="button" class="btn-ghost btn-sm todo-delete" data-id="${escapeHtml(item.id)}" title="Удалить" aria-label="Удалить">✕</button>
        </div>
      </div>
    `;
  }).join("");

  let dragId = null;
  root.querySelectorAll(".todo-item").forEach((row) => {
    row.addEventListener("dragstart", () => {
      dragId = row.dataset.id || null;
      row.classList.add("is-dragging");
    });
    row.addEventListener("dragend", () => {
      row.classList.remove("is-dragging");
      dragId = null;
    });
    row.addEventListener("dragover", (event) => {
      event.preventDefault();
      row.classList.add("is-drag-over");
    });
    row.addEventListener("dragleave", () => row.classList.remove("is-drag-over"));
    row.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("is-drag-over");
      const targetId = row.dataset.id;
      if (!dragId || !targetId || dragId === targetId) return;
      const fromIndex = advancedTodoItems.findIndex((item) => item.id === dragId);
      const toIndex = advancedTodoItems.findIndex((item) => item.id === targetId);
      if (fromIndex < 0 || toIndex < 0) return;
      const [moved] = advancedTodoItems.splice(fromIndex, 1);
      advancedTodoItems.splice(toIndex, 0, moved);
      normalizeTodoSortOrder();
      renderAdvancedTodoList();
      scheduleAdvancedTodoSave();
    });
  });

  root.querySelectorAll(".todo-complete").forEach((btn) => {
    btn.onclick = () => {
      markTodoItemComplete(btn.dataset.id || "");
      renderAdvancedTodoList();
      scheduleAdvancedTodoSave();
    };
  });
  root.querySelectorAll(".todo-reopen").forEach((btn) => {
    btn.onclick = () => {
      markTodoItemReopen(btn.dataset.id || "");
      renderAdvancedTodoList();
      scheduleAdvancedTodoSave();
    };
  });
  root.querySelectorAll(".todo-delete").forEach((btn) => {
    btn.onclick = () => {
      const item = advancedTodoItems.find((row) => row.id === btn.dataset.id);
      if (!item) return;
      const ok = window.confirm(`Удалить задачу «${item.text}»?`);
      if (!ok) return;
      advancedTodoItems = advancedTodoItems.filter((row) => row.id !== btn.dataset.id);
      normalizeTodoSortOrder();
      renderAdvancedTodoList();
      scheduleAdvancedTodoSave();
    };
  });

  root.querySelectorAll(".todo-no-due-check").forEach((input) => {
    input.onchange = () => {
      const item = advancedTodoItems.find((row) => row.id === input.dataset.id);
      if (!item) return;
      const row = input.closest(".todo-item");
      const dueInput = row?.querySelector(".todo-due-input");
      const calBtn = row?.querySelector(".todo-due-calendar");
      if (input.checked) {
        item.due_date = null;
        if (dueInput) {
          dueInput.value = "";
          dueInput.disabled = true;
        }
        if (calBtn) calBtn.disabled = true;
      } else {
        if (dueInput) {
          dueInput.disabled = false;
          if (!dueInput.value) dueInput.value = new Date().toISOString().slice(0, 10);
          item.due_date = dueInput.value || null;
        }
        if (calBtn) calBtn.disabled = false;
      }
      renderAdvancedTodoList();
      scheduleAdvancedTodoSave();
    };
  });

  root.querySelectorAll(".todo-due-input").forEach((input) => {
    input.onchange = () => {
      const item = advancedTodoItems.find((row) => row.id === input.dataset.id);
      if (!item) return;
      item.due_date = input.value || null;
      renderAdvancedTodoList();
      scheduleAdvancedTodoSave();
    };
  });

  root.querySelectorAll(".todo-due-calendar").forEach((btn) => {
    btn.onclick = () => {
      const row = btn.closest(".todo-item");
      const dueInput = row?.querySelector(".todo-due-input");
      openAdvancedTodoCalendar(dueInput);
    };
  });
}

async function loadAdvancedTodoPanel() {
  try {
    const data = await api("/advanced/todo");
    advancedTodoItems = Array.isArray(data?.items) ? data.items.map((row, index) => ({
      id: row.id || createTodoId(),
      text: String(row.text || ""),
      done: Boolean(row.done),
      priority: row.priority || "medium",
      due_date: row.due_date || null,
      sort_order: Number.isFinite(row.sort_order) ? row.sort_order : index,
      created_at: row.created_at || new Date().toISOString(),
    })) : [];
    renderAdvancedTodoList();
    syncAdvancedTodoDueControls();
  } catch (e) {
    const root = document.getElementById("advanced-todo-list");
    if (root) root.textContent = "Ошибка загрузки: " + e.message;
  }
}

function addAdvancedTodoFromForm() {
  const text = document.getElementById("advanced-todo-input")?.value.trim() || "";
  if (!text) return toast("Введите текст задачи");
  const priority = document.getElementById("advanced-todo-priority")?.value || "medium";
  const noDue = document.getElementById("advanced-todo-no-due")?.checked ?? true;
  const dueRaw = noDue ? "" : (document.getElementById("advanced-todo-due")?.value || "");
  if (!noDue && !dueRaw) return toast("Выберите дату или отметьте «Без срока»");
  advancedTodoItems.push({
    id: createTodoId(),
    text,
    done: false,
    priority,
    due_date: dueRaw || null,
    sort_order: advancedTodoItems.filter((row) => !row.done).length,
    created_at: new Date().toISOString(),
  });
  normalizeTodoSortOrder();
  resetAdvancedTodoComposeForm();
  renderAdvancedTodoList();
  scheduleAdvancedTodoSave();
}

async function doGenerate(random = false) {
  state.group_mode = document.getElementById("opt-group-mode").checked;

  try {
    const path = random ? "/generate/random" : "/generate";
    const result = await api(path, { method: "POST", body: JSON.stringify(buildPayload()) });
    document.getElementById("output-positive").value = result.positive;
    document.getElementById("output-negative").value = result.negative || "";
    document.getElementById("output-buckets").textContent = JSON.stringify(result.buckets, null, 2);
    if (result.warnings?.length) renderConflictWarnings(result.warnings);
    if (result.quality_score) renderQualityScore(result.quality_score);
    toast("Prompt generated");
  } catch (e) {
    toast("Error: " + e.message);
  }
}

async function loadFavoritesGenDefaults() {
  if (favoritesGenDefaults) return favoritesGenDefaults;
  favoritesGenDefaults = await api("/models/generation-defaults");
  return favoritesGenDefaults;
}

function downloadBlob(filename, content, mime = "text/plain;charset=utf-8") {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function modelLabel(modelId) {
  return MODEL_LABELS[modelId] || modelId || "—";
}

function defaultHiresSettings() {
  return { enabled: false, scale: 2.0, steps: 20, denoising: 0.35, upscaler: "4x-UltraSharp" };
}

function mergeGenerationSettings(modelId, existing) {
  const base = favoritesGenDefaults?.[modelId]?.defaults || {};
  const hiresBase = favoritesGenDefaults?.[modelId]?.hires || defaultHiresSettings();
  const gen = existing && typeof existing === "object" ? existing : {};
  const hires = gen.hires && typeof gen.hires === "object" ? gen.hires : {};
  return {
    sampler: gen.sampler ?? base.sampler ?? "",
    schedule: gen.schedule ?? base.schedule ?? "",
    steps: gen.steps ?? base.steps ?? "",
    cfg: gen.cfg ?? base.cfg ?? "",
    seed: gen.seed ?? "",
    width: gen.width ?? base.width ?? "",
    height: gen.height ?? base.height ?? "",
    hires: {
      enabled: Boolean(hires.enabled ?? hiresBase.enabled),
      scale: hires.scale ?? hiresBase.scale ?? 2.0,
      steps: hires.steps ?? hiresBase.steps ?? 20,
      denoising: hires.denoising ?? hiresBase.denoising ?? 0.35,
      upscaler: hires.upscaler ?? hiresBase.upscaler ?? "4x-UltraSharp",
    },
  };
}

function readFavGenerationSettingsFromForm() {
  const settings = {
    sampler: document.getElementById("fav-sampler")?.value.trim() || null,
    schedule: document.getElementById("fav-schedule")?.value.trim() || null,
    steps: Number(document.getElementById("fav-steps")?.value),
    cfg: Number(document.getElementById("fav-cfg")?.value),
    seed: Number(document.getElementById("fav-seed")?.value),
    width: Number(document.getElementById("fav-width")?.value),
    height: Number(document.getElementById("fav-height")?.value),
    hires: {
      enabled: Boolean(document.getElementById("fav-hires-enabled")?.checked),
      scale: Number(document.getElementById("fav-hr-scale")?.value),
      steps: Number(document.getElementById("fav-hr-steps")?.value),
      denoising: Number(document.getElementById("fav-hr-denoising")?.value),
      upscaler: document.getElementById("fav-hr-upscaler")?.value.trim() || null,
    },
  };
  const hasGen = [settings.sampler, settings.schedule].some(Boolean)
    || [settings.steps, settings.cfg, settings.seed, settings.width, settings.height].some((n) => Number.isFinite(n));
  const hasHires = settings.hires.enabled
    || [settings.hires.scale, settings.hires.steps, settings.hires.denoising].some((n) => Number.isFinite(n))
    || settings.hires.upscaler;
  if (!hasGen && !hasHires) return null;
  return settings;
}

function writeFavGenerationSettingsToForm(modelId, generationSettings) {
  const merged = mergeGenerationSettings(modelId, generationSettings);
  const setNum = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val === "" || val == null ? "" : String(val);
  };
  document.getElementById("fav-sampler").value = merged.sampler || "";
  document.getElementById("fav-schedule").value = merged.schedule || "";
  setNum("fav-steps", merged.steps);
  setNum("fav-cfg", merged.cfg);
  setNum("fav-seed", merged.seed);
  setNum("fav-width", merged.width);
  setNum("fav-height", merged.height);
  document.getElementById("fav-hires-enabled").checked = Boolean(merged.hires.enabled);
  setNum("fav-hr-scale", merged.hires.scale);
  setNum("fav-hr-steps", merged.hires.steps);
  setNum("fav-hr-denoising", merged.hires.denoising);
  document.getElementById("fav-hr-upscaler").value = merged.hires.upscaler || "";
  updateFavModelUi(modelId);
}

function updateFavModelUi(modelId) {
  const meta = favoritesGenDefaults?.[modelId];
  const negWrap = document.getElementById("fav-negative-wrap");
  const cfgLabel = document.getElementById("fav-cfg-label");
  if (negWrap) negWrap.style.display = meta?.supports_negative === false ? "none" : "";
  if (cfgLabel) cfgLabel.textContent = modelId === "zimage_turbo" ? "Guidance" : "CFG";
}

function openFavModal(prefill = {}) {
  const modal = document.getElementById("fav-modal");
  if (!modal) return;
  editingFavoriteId = Number.isFinite(prefill.id) ? prefill.id : null;
  const titleEl = document.getElementById("fav-modal-title");
  const saveEl = document.getElementById("fav-save");
  if (titleEl) titleEl.textContent = editingFavoriteId ? "Редактирование избранного" : "Избранный промпт";
  if (saveEl) saveEl.textContent = editingFavoriteId ? "Сохранить изменения" : "Сохранить";
  const modelId = prefill.model_id || state.model_id || "illustrious";
  document.getElementById("fav-name").value = prefill.name || `prompt_${Date.now()}`;
  document.getElementById("fav-model").value = modelId;
  document.getElementById("fav-positive").value = prefill.positive || "";
  document.getElementById("fav-negative").value = prefill.negative || "";
  document.getElementById("fav-result-url").value = prefill.result_url || "";
  writeFavGenerationSettingsToForm(modelId, prefill.generation_settings);
  modal.classList.remove("hidden");
  document.getElementById("fav-name")?.focus();
}

function closeFavModal() {
  editingFavoriteId = null;
  document.getElementById("fav-modal")?.classList.add("hidden");
}

function closeAddTagModal() {
  document.getElementById("add-tag-modal")?.classList.add("hidden");
}

function getCategoryTitleById(categoryId) {
  const hit = addTagCategoriesCache.find((row) => row.id === categoryId);
  return hit?.title || categoryId;
}

function collectTreeSubgroupsForCategory(nodes, categoryId, subgroupSet) {
  for (const node of nodes || []) {
    if (Array.isArray(node.children) && node.children.length) {
      collectTreeSubgroupsForCategory(node.children, categoryId, subgroupSet);
      continue;
    }
    if (node?.categoryId !== categoryId) continue;
    const subgroup = typeof node.subgroup === "string" ? node.subgroup.trim() : "";
    if (subgroup) subgroupSet.add(subgroup);
  }
}

function collectKnownSubgroups(categoryId, categoryData) {
  const subgroupSet = new Set();
  for (const subgroup of categoryData?.subcategories || []) {
    const value = String(subgroup || "").trim();
    if (value) subgroupSet.add(value);
  }
  for (const item of categoryData?.items || []) {
    const subgroup = String(item.meta?.subcategory_id || item.meta?.subgroup || "").trim();
    if (subgroup) subgroupSet.add(subgroup);
  }
  const trees = [
    OUTFIT_TREE,
    getCharacterStructureTree(),
    getFaceVibeTree(),
    MAKEUP_TREE,
    ACCESSORIES_TREE,
    POSE_TREE,
    getCameraTree(),
    window.LIGHTING_TREE || [],
    window.ENVIRONMENT_TREE || [],
    window.STYLE_TREE || [],
    window.FETISH_TREE || [],
  ];
  for (const tree of trees) {
    collectTreeSubgroupsForCategory(tree, categoryId, subgroupSet);
  }
  return Array.from(subgroupSet).sort((a, b) => String(a).localeCompare(String(b)));
}

async function loadAddTagCategories() {
  const data = await api("/categories");
  const categories = Array.isArray(data.categories) ? data.categories : [];
  addTagCategoriesCache = categories
    .filter((row) => typeof row.id === "string" && row.id.trim())
    .sort((a, b) => (a.title || a.id).localeCompare(b.title || b.id));
  return addTagCategoriesCache;
}

async function fillAddTagSubgroups(categoryId) {
  const subgroupInput = document.getElementById("add-tag-subgroup");
  const datalist = document.getElementById("add-tag-subgroup-options");
  if (!subgroupInput) return [];
  const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
  const subgroups = collectKnownSubgroups(categoryId, data);
  if (datalist) datalist.innerHTML = subgroups.map((s) => `<option value="${escapeHtml(s)}"></option>`).join("");
  subgroupInput.dataset.hasSubgroups = subgroups.length ? "1" : "0";
  return subgroups;
}

async function openAddTagModalWithContext(prefillCategoryId = null, prefillSubgroup = null) {
  const modal = document.getElementById("add-tag-modal");
  if (!modal) return;
  const categorySelect = document.getElementById("add-tag-category");
  const subgroupSelect = document.getElementById("add-tag-subgroup");
  const labelInput = document.getElementById("add-tag-label");
  const itemIdInput = document.getElementById("add-tag-item-id");
  const aliasesInput = document.getElementById("add-tag-aliases");
  const descriptionInput = document.getElementById("add-tag-description");
  const defaultWeightInput = document.getElementById("add-tag-default-weight");
  const titleEl = document.getElementById("add-tag-category-title");
  if (!categorySelect || !subgroupSelect || !labelInput || !itemIdInput || !aliasesInput || !descriptionInput || !defaultWeightInput || !titleEl) return;

  const categories = await loadAddTagCategories();
  categorySelect.innerHTML = "";
  for (const category of categories) {
    const option = document.createElement("option");
    option.value = category.id;
    option.textContent = `${category.title} (${category.id})`;
    categorySelect.appendChild(option);
  }
  const categoryIds = new Set(categories.map((row) => row.id));
  if (prefillCategoryId && categoryIds.has(prefillCategoryId)) {
    categorySelect.value = prefillCategoryId;
  } else {
    const activeLeaf = findTreeLeaf(activeOutfitLeafId, getOutfitTree())
      || findTreeLeaf(activeCharacterLeafId, getCharacterTree())
      || findTreeLeaf(activeFaceLeafId, getFaceTree())
      || findTreeLeaf(activeMakeupLeafId, getMakeupTree())
      || findTreeLeaf(activeAccessoriesLeafId, getAccessoriesTree())
      || findTreeLeaf(activePoseLeafId, getPoseTree())
      || findTreeLeaf(activeCameraLeafId, getCameraTree())
      || findTreeLeaf(activeLightingLeafId, getLightingTree())
      || findTreeLeaf(activeEnvironmentLeafId, getEnvironmentTree())
      || findTreeLeaf(activeStyleLeafId, getStyleTree())
      || findTreeLeaf(activeFetishLeafId, getFetishTree());
    if (activeLeaf?.categoryId && categoryIds.has(activeLeaf.categoryId)) {
      categorySelect.value = activeLeaf.categoryId;
    } else if (categories[0]?.id) {
      categorySelect.value = categories[0].id;
    }
    if (!prefillSubgroup && activeLeaf?.subgroup) prefillSubgroup = activeLeaf.subgroup;
  }
  await fillAddTagSubgroups(categorySelect.value);
  subgroupSelect.value = prefillSubgroup || "";
  titleEl.textContent = getCategoryTitleById(categorySelect.value);
  document.getElementById("add-tag-persist").checked = true;
  labelInput.value = "";
  itemIdInput.value = "";
  aliasesInput.value = "";
  descriptionInput.value = "";
  defaultWeightInput.value = "1.0";
  modal.classList.remove("hidden");
  labelInput.focus();
}

async function openAddTagModal() {
  await openAddTagModalWithContext();
}

async function createTagFromModal(event) {
  event?.preventDefault();
  const label = document.getElementById("add-tag-label")?.value.trim() || "";
  const itemId = document.getElementById("add-tag-item-id")?.value.trim() || "";
  const categoryId = document.getElementById("add-tag-category")?.value || "";
  const subgroupSelect = document.getElementById("add-tag-subgroup");
  const subgroup = subgroupSelect?.value || "";
  const aliasesRaw = document.getElementById("add-tag-aliases")?.value || "";
  const aliases = aliasesRaw.split(",").map((x) => x.trim()).filter(Boolean);
  const description = document.getElementById("add-tag-description")?.value.trim() || null;
  const defaultWeight = Number.parseFloat(document.getElementById("add-tag-default-weight")?.value || "1.0");
  const persist = Boolean(document.getElementById("add-tag-persist")?.checked);
  if (!label) return toast("Введите значение тега");
  if (!categoryId) return toast("Выберите категорию");
  if (subgroupSelect?.dataset.hasSubgroups === "1" && !subgroup) {
    return toast("Выберите подкатегорию (Subcategory)");
  }
  if (Number.isNaN(defaultWeight) || defaultWeight <= 0) return toast("Укажите корректный default weight");
  try {
    const data = await api(`/categories/${encodeURIComponent(categoryId)}/items`, {
      method: "POST",
      body: JSON.stringify({
        label,
        item_id: itemId || null,
        subgroup,
        subcategory_id: subgroup,
        allow_new_subcategory: true,
        aliases,
        description,
        default_weight: defaultWeight,
        persist,
      }),
    });
    await preloadSubgroupMaps();
    clothingStateCatalog = null;
    clothingStateLoadingPromise = null;
    await ensureClothingStateCatalog();
    refreshAllPanels();
    syncFormControlsFromState();
    notifyStateChange();
    closeAddTagModal();
    const actionLabel = data.action === "renamed" ? ` (id: ${data.item?.id})` : "";
    toast(`Тег добавлен${actionLabel}`);
  } catch (e) {
    if (String(e.message || "").includes("duplicates existing item")) {
      toast("Найден дубликат в категории. Откройте Tag Studio dedupe и выберите действие.");
    } else {
      toast("Ошибка: " + e.message);
    }
  }
}

async function openFavFromResult() {
  const positive = document.getElementById("output-positive")?.value.trim();
  if (!positive) return toast("Сначала сгенерируйте промпт");
  await loadFavoritesGenDefaults();
  openFavModal({
    name: `prompt_${Date.now()}`,
    positive,
    negative: document.getElementById("output-negative")?.value || "",
    model_id: state.model_id,
    generation_settings: mergeGenerationSettings(state.model_id, null),
  });
}

function readPromptingOutputText(outputId) {
  const el = document.getElementById(outputId);
  if (!el) return "";
  const text = (el.textContent || "").trim();
  return text === "—" ? "" : text;
}

function copyPromptingOutput(outputId, label = "результат") {
  const text = readPromptingOutputText(outputId);
  if (!text) return toast("Нет результата для копирования");
  navigator.clipboard.writeText(text);
  toast(`Скопировано: ${label}`);
}

function resolvePromptingAnalyzeModelId() {
  const target = document.getElementById("prompting-target-model")?.value;
  if (target && target !== "json") return target;
  return document.getElementById("prompting-source-model")?.value || state.model_id;
}

async function openFavFromPromptingOutput({ outputId, modelId, negative = "" }) {
  const positive = readPromptingOutputText(outputId);
  if (!positive) return toast("Нет результата для сохранения");
  await loadFavoritesGenDefaults();
  const resolvedModel = modelId || state.model_id;
  openFavModal({
    name: `prompt_${Date.now()}`,
    positive,
    negative: negative || "",
    model_id: resolvedModel,
    generation_settings: mergeGenerationSettings(resolvedModel, null),
  });
}

async function openFavManual() {
  await loadFavoritesGenDefaults();
  openFavModal({
    name: `prompt_${Date.now()}`,
    model_id: state.model_id,
    generation_settings: mergeGenerationSettings(state.model_id, null),
  });
}

async function saveFavoriteFromForm(ev) {
  ev?.preventDefault();
  const name = document.getElementById("fav-name")?.value.trim();
  const positive = document.getElementById("fav-positive")?.value.trim();
  const modelId = document.getElementById("fav-model")?.value || "illustrious";
  if (!name) return toast("Укажите название");
  if (!positive) return toast("Укажите positive промпт");
  const resultUrl = document.getElementById("fav-result-url")?.value.trim() || null;
  const negativeRaw = document.getElementById("fav-negative")?.value.trim();
  const supportsNeg = favoritesGenDefaults?.[modelId]?.supports_negative !== false;
  try {
    const payload = {
      name,
      positive,
      negative: supportsNeg ? negativeRaw || null : null,
      model_id: modelId,
      result_url: resultUrl,
      generation_settings: readFavGenerationSettingsFromForm(),
    };
    await api(editingFavoriteId ? `/favorites/${editingFavoriteId}` : "/favorites", {
      method: editingFavoriteId ? "PUT" : "POST",
      body: JSON.stringify({
        ...payload,
      }),
    });
    toast(editingFavoriteId ? "Избранное обновлено" : "Сохранено в избранное");
    editingFavoriteId = null;
    closeFavModal();
    loadFavorites();
  } catch (e) {
    toast("Ошибка: " + e.message);
  }
}

function loadFavoriteIntoOutput(row) {
  document.getElementById("output-positive").value = row.positive || "";
  document.getElementById("output-negative").value = row.negative || "";
  if (row.model_id && row.model_id !== state.model_id) {
    state.model_id = row.model_id;
    document.getElementById("negative-card").style.display =
      state.model_id === "zimage_turbo" ? "none" : "";
    initStaticChips();
    syncQualityBoostersPanel();
    notifyStateChange();
  }
  toast(`Загружено: ${row.name}`);
}

function formatFavoriteTxt(row) {
  const lines = [
    `=== ${row.name} ===`,
    `Model: ${modelLabel(row.model_id)} (${row.model_id})`,
    `Created: ${row.created_at || "—"}`,
    "",
    "Positive:",
    row.positive || "",
  ];
  if (row.negative) {
    lines.push("", "Negative:", row.negative);
  }
  if (row.result_url) {
    lines.push("", "Result URL:", row.result_url);
  }
  const gen = row.generation_settings;
  if (gen && typeof gen === "object") {
    lines.push("", "Generation settings:");
    if (gen.sampler) lines.push(`  Sampler: ${gen.sampler}`);
    if (gen.schedule) lines.push(`  Schedule: ${gen.schedule}`);
    if (gen.steps != null) lines.push(`  Steps: ${gen.steps}`);
    if (gen.cfg != null) lines.push(`  CFG/Guidance: ${gen.cfg}`);
    if (gen.seed != null && Number.isFinite(gen.seed)) lines.push(`  Seed: ${gen.seed}`);
    if (gen.width != null) lines.push(`  Width: ${gen.width}`);
    if (gen.height != null) lines.push(`  Height: ${gen.height}`);
    const hires = gen.hires;
    if (hires && typeof hires === "object") {
      lines.push("", "Hires fix:");
      lines.push(`  Enabled: ${hires.enabled ? "yes" : "no"}`);
      if (hires.scale != null) lines.push(`  Scale: ${hires.scale}`);
      if (hires.steps != null) lines.push(`  Hires steps: ${hires.steps}`);
      if (hires.denoising != null) lines.push(`  Denoising: ${hires.denoising}`);
      if (hires.upscaler) lines.push(`  Upscaler: ${hires.upscaler}`);
    }
  }
  return lines.join("\n");
}

async function exportAllFavoritesTxt() {
  try {
    const rows = await api("/favorites?limit=500");
    if (!rows.length) return toast("Нет избранных промптов");
    const body = rows.map((r) => formatFavoriteTxt(r)).join("\n\n" + "-".repeat(48) + "\n\n");
    downloadBlob(`egodary-favorites-${Date.now()}.txt`, body);
    toast("Экспорт TXT");
  } catch (e) {
    toast("Ошибка: " + e.message);
  }
}

async function exportAllFavoritesJson() {
  try {
    const rows = await api("/favorites?limit=500");
    if (!rows.length) return toast("Нет избранных промптов");
    const payload = {
      exported_at: new Date().toISOString(),
      version: 1,
      favorites: rows,
    };
    downloadBlob(
      `egodary-favorites-${Date.now()}.json`,
      JSON.stringify(payload, null, 2),
      "application/json;charset=utf-8",
    );
    toast("Экспорт JSON");
  } catch (e) {
    toast("Ошибка: " + e.message);
  }
}

function exportSingleFavorite(row, format) {
  if (format === "json") {
    downloadBlob(
      `favorite-${row.id}-${Date.now()}.json`,
      JSON.stringify(row, null, 2),
      "application/json;charset=utf-8",
    );
  } else {
    downloadBlob(`favorite-${row.id}-${Date.now()}.txt`, formatFavoriteTxt(row));
  }
  toast("Экспортировано");
}

function favoriteSubline(row) {
  const parts = [modelLabel(row.model_id)];
  const gen = row.generation_settings;
  if (gen?.steps) parts.push(`${gen.steps} steps`);
  if (Number.isFinite(gen?.seed)) parts.push(`seed ${gen.seed}`);
  if (gen?.hires?.enabled) parts.push("hires");
  if (row.result_url) parts.push("ссылка");
  return parts.join(" · ");
}

function stringifyFavoriteSettings(row) {
  const gen = row.generation_settings;
  if (!gen || typeof gen !== "object") return "Настройки генерации не сохранены.";
  const lines = [];
  if (gen.sampler) lines.push(`Sampler: ${gen.sampler}`);
  if (gen.schedule) lines.push(`Schedule: ${gen.schedule}`);
  if (gen.steps != null) lines.push(`Steps: ${gen.steps}`);
  if (gen.cfg != null) lines.push(`CFG/Guidance: ${gen.cfg}`);
  if (gen.seed != null && Number.isFinite(gen.seed)) lines.push(`Seed: ${gen.seed}`);
  if (gen.width != null) lines.push(`Width: ${gen.width}`);
  if (gen.height != null) lines.push(`Height: ${gen.height}`);
  if (gen.hires && typeof gen.hires === "object") {
    lines.push(`Hires: ${gen.hires.enabled ? "on" : "off"}`);
    if (gen.hires.scale != null) lines.push(`HR scale: ${gen.hires.scale}`);
    if (gen.hires.steps != null) lines.push(`HR steps: ${gen.hires.steps}`);
    if (gen.hires.denoising != null) lines.push(`HR denoising: ${gen.hires.denoising}`);
    if (gen.hires.upscaler) lines.push(`Upscaler: ${gen.hires.upscaler}`);
  }
  return lines.join(" · ");
}

function clearFavoritePreview() {
  const empty = document.getElementById("favorite-preview-empty");
  const view = document.getElementById("favorite-preview");
  const openBtn = document.getElementById("btn-fav-open-link");
  const analyzeBtn = document.getElementById("btn-fav-preview-to-analyze");
  if (empty) empty.classList.remove("hidden");
  if (view) view.classList.add("hidden");
  if (openBtn) {
    openBtn.disabled = true;
    openBtn.dataset.href = "";
  }
  if (analyzeBtn) analyzeBtn.disabled = true;
}

function renderFavoritePreview(row) {
  const empty = document.getElementById("favorite-preview-empty");
  const view = document.getElementById("favorite-preview");
  if (!empty || !view) return;
  empty.classList.add("hidden");
  view.classList.remove("hidden");
  const meta = document.getElementById("fav-preview-meta");
  const pos = document.getElementById("fav-preview-positive");
  const neg = document.getElementById("fav-preview-negative");
  const negWrap = document.getElementById("fav-preview-negative-wrap");
  const settings = document.getElementById("fav-preview-settings");
  const openBtn = document.getElementById("btn-fav-open-link");
  const analyzeBtn = document.getElementById("btn-fav-preview-to-analyze");
  if (meta) meta.textContent = `${row.name} · ${favoriteSubline(row)}`;
  if (pos) pos.value = row.positive || "";
  if (neg) neg.value = row.negative || "";
  if (negWrap) negWrap.style.display = row.negative ? "" : "none";
  if (settings) settings.textContent = stringifyFavoriteSettings(row);
  if (openBtn) {
    openBtn.disabled = !row.result_url;
    openBtn.dataset.href = row.result_url || "";
  }
  if (analyzeBtn) analyzeBtn.disabled = !row.positive?.trim();
}

async function loadFavoriteIntoPromptAnalyze(rowOrId) {
  try {
    let row = rowOrId;
    if (!row || typeof row !== "object") {
      const id = rowOrId || activeFavoriteId;
      if (!id) return toast("Выберите избранный промпт");
      row = await api(`/favorites/${id}`);
    }
    if (!row.positive?.trim()) return toast("Пустой промпт");
    activePromptingLeafId = "prompt_analyze";
    switchTab("prompting");
    const input = document.getElementById("prompting-analyze-input");
    if (input) input.value = row.positive;
    const src = document.getElementById("prompting-source-model");
    const tgt = document.getElementById("prompting-target-model");
    if (row.model_id) {
      if (src) src.value = row.model_id;
      if (tgt) tgt.value = row.model_id;
    }
    toast(`В Analyze: ${row.name}`);
  } catch (err) {
    toast("Ошибка: " + err.message);
  }
}

async function showFavoriteById(favoriteId) {
  try {
    const row = await api(`/favorites/${favoriteId}`);
    activeFavoriteId = row.id;
    renderFavoritePreview(row);
    return row;
  } catch (err) {
    toast("Ошибка: " + err.message);
    return null;
  }
}

async function loadFavorites() {
  const root = document.getElementById("favorites-list");
  if (!root) return;
  try {
    const rows = await api("/favorites?limit=50");
    if (!rows.length) {
      root.innerHTML = '<p class="fav-empty">Пока пусто. Сохраните промпт из результата или добавьте вручную.</p>';
      return;
    }
    root.innerHTML = rows
      .map(
        (r) => `
        <div class="fav-item" data-id="${r.id}">
          <div class="fav-meta">
            <div class="fav-name" title="${escapeHtml(r.name)}">${escapeHtml(r.name)}</div>
            <div class="fav-sub">${escapeHtml(favoriteSubline(r))}</div>
          </div>
          <div class="fav-actions">
            <button type="button" class="fav-analyze" title="В Prompt Analyze">✎</button>
            <button type="button" class="fav-view">Просмотр</button>
            <button type="button" class="fav-load">Загрузить</button>
            <button type="button" class="fav-edit">Редакт.</button>
            <button type="button" class="fav-export-txt" title="Экспорт TXT">TXT</button>
            <button type="button" class="fav-export-json" title="Экспорт JSON">JSON</button>
            <button type="button" class="fav-delete">Удалить</button>
          </div>
        </div>`,
      )
      .join("");
    root.querySelectorAll(".fav-analyze").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.closest(".fav-item")?.dataset.id;
        if (!id) return;
        try {
          const row = await api(`/favorites/${id}`);
          await loadFavoriteIntoPromptAnalyze(row);
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".fav-view").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.closest(".fav-item")?.dataset.id;
        if (!id) return;
        await showFavoriteById(id);
      };
    });
    root.querySelectorAll(".fav-load").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.closest(".fav-item")?.dataset.id;
        if (!id) return;
        try {
          const row = await api(`/favorites/${id}`);
          loadFavoriteIntoOutput(row);
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".fav-edit").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.closest(".fav-item")?.dataset.id;
        if (!id) return;
        try {
          const row = await api(`/favorites/${id}`);
          await loadFavoritesGenDefaults();
          openFavModal(row);
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".fav-export-txt").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.closest(".fav-item")?.dataset.id;
        if (!id) return;
        try {
          const row = await api(`/favorites/${id}`);
          exportSingleFavorite(row, "txt");
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".fav-export-json").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const id = btn.closest(".fav-item")?.dataset.id;
        if (!id) return;
        try {
          const row = await api(`/favorites/${id}`);
          exportSingleFavorite(row, "json");
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".fav-delete").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const item = btn.closest(".fav-item");
        const id = item?.dataset.id;
        if (!id) return;
        const name = item.querySelector(".fav-name")?.textContent || "промпт";
        if (!window.confirm(`Удалить «${name}»?`)) return;
        try {
          await api(`/favorites/${id}`, { method: "DELETE" });
          toast("Удалено");
          loadFavorites();
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    if (activeFavoriteId) {
      const matched = rows.find((r) => Number(r.id) === Number(activeFavoriteId));
      if (matched) {
        await showFavoriteById(matched.id);
      } else {
        activeFavoriteId = null;
        clearFavoritePreview();
      }
    } else {
      clearFavoritePreview();
    }
  } catch (_) {
    root.innerHTML = "<p class=\"fav-empty\">Не удалось загрузить избранное.</p>";
    clearFavoritePreview();
  }
}

function bindFavoritesUi() {
  document.getElementById("btn-fav-from-result")?.addEventListener("click", openFavFromResult);
  document.getElementById("btn-fav-manual")?.addEventListener("click", openFavManual);
  document.getElementById("btn-fav-export-txt")?.addEventListener("click", exportAllFavoritesTxt);
  document.getElementById("btn-fav-export-json")?.addEventListener("click", exportAllFavoritesJson);
  document.getElementById("fav-modal-close")?.addEventListener("click", closeFavModal);
  document.getElementById("fav-modal-backdrop")?.addEventListener("click", closeFavModal);
  document.getElementById("fav-cancel")?.addEventListener("click", closeFavModal);
  document.getElementById("fav-form")?.addEventListener("submit", saveFavoriteFromForm);
  document.getElementById("btn-fav-open-link")?.addEventListener("click", () => {
    const href = document.getElementById("btn-fav-open-link")?.dataset.href;
    if (!href) return;
    window.open(href, "_blank", "noopener,noreferrer");
  });
  document.getElementById("btn-fav-preview-to-analyze")?.addEventListener("click", () => {
    if (!activeFavoriteId) return toast("Выберите избранный промпт");
    loadFavoriteIntoPromptAnalyze(activeFavoriteId);
  });
  document.getElementById("btn-fav-to-analyze")?.addEventListener("click", () => {
    loadFavoriteIntoPromptAnalyze(activeFavoriteId);
  });
  document.getElementById("btn-prompt-analyze-copy")?.addEventListener("click", () => {
    copyPromptingOutput("prompting-analyze-output", "Prompt Analyze");
  });
  document.getElementById("btn-prompt-analyze-fav")?.addEventListener("click", () => {
    openFavFromPromptingOutput({
      outputId: "prompting-analyze-output",
      modelId: resolvePromptingAnalyzeModelId(),
      negative: document.getElementById("output-negative")?.value || "",
    });
  });
  document.getElementById("btn-prompt-nsfw-copy")?.addEventListener("click", () => {
    copyPromptingOutput("prompting-nsfw-output", "NSFW styler");
  });
  document.getElementById("btn-prompt-nsfw-fav")?.addEventListener("click", () => {
    openFavFromPromptingOutput({
      outputId: "prompting-nsfw-output",
      modelId: state.model_id,
    });
  });
  document.getElementById("fav-model")?.addEventListener("change", async (e) => {
    await loadFavoritesGenDefaults();
    const modelId = e.target.value || "illustrious";
    writeFavGenerationSettingsToForm(modelId, null);
  });
}

function buildCharacterLibraryPayload() {
  syncStateFromFormControls();
  const character = sanitizeCharacter(state.character);
  state.character = character;
  return {
    character,
    face: { ...state.face },
    appearance: {
      hair: state.appearance.hair || "",
      hair_color: state.appearance.hair_color || "",
    },
  };
}

function applyCharacterLibraryPayload(payload) {
  if (!payload || typeof payload !== "object") return;
  const normalized = sanitizePromptPayload({
    ...createDefaultState(),
    character: payload.character,
    face: payload.face,
    appearance: {
      hair: payload.appearance?.hair,
      hair_color: payload.appearance?.hair_color,
    },
  });
  state.character = normalized.character;
  state.face = normalized.face;
  state.appearance.hair = normalized.appearance.hair;
  state.appearance.hair_color = normalized.appearance.hair_color;
  clearGeneratedOutput();
  initCharacterPanel();
  initFacePanel();
  notifyStateChange();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function scrollCharacterLibraryIntoView(highlight = false) {
  const card = document.getElementById("character-library-card");
  if (!card) return;
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  if (highlight) {
    card.classList.remove("char-lib-highlight");
    void card.offsetWidth;
    card.classList.add("char-lib-highlight");
    setTimeout(() => card.classList.remove("char-lib-highlight"), 1300);
  }
}

async function loadCharacterLibrary() {
  const root = document.getElementById("character-library-list");
  if (!root) return;
  try {
    const rows = await api("/character-library?limit=20");
    if (!rows.length) {
      root.innerHTML = `
        <p class="char-lib-empty">Пока пусто.</p>
        <span class="char-lib-empty-hint">Настройте персонажа ниже и нажмите «+ Сохранить текущего» — пресет появится в этом списке.</span>`;
      return;
    }
    root.innerHTML = rows
      .map(
        (r) => `
        <div class="char-lib-item" data-id="${r.id}">
          <div class="char-lib-meta">
            <div class="char-lib-name">${escapeHtml(r.name)}</div>
            <div class="char-lib-count">${r.field_count || 0} полей · Character + Face + Hair</div>
          </div>
          <div class="char-lib-actions">
            <button type="button" class="char-lib-load">Загрузить</button>
            <button type="button" class="char-lib-rename">Переименовать</button>
            <button type="button" class="char-lib-delete">Удалить</button>
          </div>
        </div>`
      )
      .join("");
    root.querySelectorAll(".char-lib-load").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const item = btn.closest(".char-lib-item");
        const id = item?.dataset.id;
        if (!id) return;
        try {
          const row = await api(`/character-library/${id}`);
          applyCharacterLibraryPayload(row.payload);
          toast(`Загружен: ${row.name}`);
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".char-lib-rename").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const item = btn.closest(".char-lib-item");
        const id = item?.dataset.id;
        if (!id) return;
        const currentName = item.querySelector(".char-lib-name")?.textContent || "";
        const nextName = prompt("Новое имя персонажа:", currentName);
        if (!nextName?.trim() || nextName.trim() === currentName) return;
        try {
          await api(`/character-library/${id}`, {
            method: "PATCH",
            body: JSON.stringify({ name: nextName.trim() }),
          });
          toast("Имя обновлено");
          loadCharacterLibrary();
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
    root.querySelectorAll(".char-lib-delete").forEach((btn) => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const item = btn.closest(".char-lib-item");
        const id = item?.dataset.id;
        if (!id) return;
        const name = item.querySelector(".char-lib-name")?.textContent || "персонаж";
        if (!window.confirm(`Удалить «${name}»?`)) return;
        try {
          await api(`/character-library/${id}`, { method: "DELETE" });
          toast("Удалено");
          loadCharacterLibrary();
        } catch (err) {
          toast("Ошибка: " + err.message);
        }
      };
    });
  } catch (err) {
    root.innerHTML = `<p class="char-lib-empty">Не удалось загрузить библиотеку.</p><span class="char-lib-empty-hint">${escapeHtml(err.message || "ошибка API")}</span>`;
  }
}

async function saveCharacterLibraryPreset() {
  const payload = buildCharacterLibraryPayload();
  const fieldCount =
    Object.values(payload.character).filter((v) => (Array.isArray(v) ? v.length : v)).length +
    Object.values(payload.face).filter(Boolean).length +
    (payload.appearance.hair ? 1 : 0) +
    (payload.appearance.hair_color ? 1 : 0);
  if (!fieldCount) return toast("Выберите параметры Character / Face / Hair");
  const name = prompt("Имя персонажа:", `character_${Date.now()}`);
  if (!name?.trim()) return;
  try {
    await api("/character-library", {
      method: "POST",
      body: JSON.stringify({ name: name.trim(), payload }),
    });
    toast("Персонаж сохранён — см. список выше");
    await loadCharacterLibrary();
    scrollCharacterLibraryIntoView(true);
  } catch (e) {
    toast("Ошибка: " + e.message);
  }
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.onclick = () => switchTab(btn.dataset.tab);
  });
  document.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-open-add-tag-modal]");
    if (!btn) return;
    event.preventDefault();
    event.stopPropagation();
    try {
      await openAddTagModalWithContext(
        btn.dataset.addTagCategory || null,
        btn.dataset.addTagSubgroup || null,
      );
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const btn = event.target.closest(".btn-add-tag-inline[data-open-add-tag-modal]");
    if (!btn) return;
    event.preventDefault();
    event.stopPropagation();
    btn.click();
  });
  document.getElementById("add-tag-modal-close")?.addEventListener("click", closeAddTagModal);
  document.getElementById("add-tag-modal-backdrop")?.addEventListener("click", closeAddTagModal);
  document.getElementById("add-tag-cancel")?.addEventListener("click", closeAddTagModal);
  document.getElementById("add-tag-form")?.addEventListener("submit", createTagFromModal);
  document.getElementById("edit-tag-modal-close")?.addEventListener("click", closeEditTagModal);
  document.getElementById("edit-tag-modal-backdrop")?.addEventListener("click", closeEditTagModal);
  document.getElementById("edit-tag-cancel")?.addEventListener("click", closeEditTagModal);
  document.getElementById("edit-tag-category")?.addEventListener("change", (event) => {
    const categoryId = event.target?.value || "";
    if (!categoryId) return;
    fillEditTagSubgroups(categoryId).catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("edit-tag-form")?.addEventListener("submit", (event) => {
    saveEditTagFromModal(event).catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-advanced-todo-add")?.addEventListener("click", addAdvancedTodoFromForm);
  document.getElementById("advanced-todo-no-due")?.addEventListener("change", syncAdvancedTodoDueControls);
  document.getElementById("btn-advanced-todo-open-calendar")?.addEventListener("click", () => {
    const noDue = document.getElementById("advanced-todo-no-due");
    if (noDue?.checked) {
      noDue.checked = false;
      syncAdvancedTodoDueControls();
    }
    openAdvancedTodoCalendar(document.getElementById("advanced-todo-due"));
  });
  syncAdvancedTodoDueControls();
  document.getElementById("btn-advanced-todo-refresh")?.addEventListener("click", () => {
    loadAdvancedTodoPanel().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("advanced-todo-input")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addAdvancedTodoFromForm();
    }
  });
  document.getElementById("add-tag-category")?.addEventListener("change", async (event) => {
    const categoryId = event.target?.value || "";
    if (!categoryId) return;
    try {
      await fillAddTagSubgroups(categoryId);
      const titleEl = document.getElementById("add-tag-category-title");
      if (titleEl) titleEl.textContent = getCategoryTitleById(categoryId);
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });
  document.getElementById("btn-tagstudio-refresh")?.addEventListener("click", () => {
    Promise.all([loadTagStudioPanel(), loadTagStudioLister()]).catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-search")?.addEventListener("click", () => {
    loadTagStudioPanel().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("tagstudio-search")?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loadTagStudioPanel().catch((e) => toast("Ошибка: " + e.message));
    }
  });
  document.getElementById("btn-tagstudio-dedupe")?.addEventListener("click", () => {
    runTagStudioDedupe().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-migrate")?.addEventListener("click", () => {
    runTagStudioMigration().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-rollback")?.addEventListener("click", () => {
    runTagStudioRollback().catch((e) => toast("Ошибка: " + e.message));
  });

  document.getElementById("btn-generate").onclick = () => {
    doGenerate(false);
  };
  document.getElementById("btn-random").onclick = () => doGenerate(true);

  document.getElementById("btn-copy-pos").onclick = () => {
    navigator.clipboard.writeText(document.getElementById("output-positive").value);
    toast("Copied positive");
  };
  document.getElementById("btn-copy-neg").onclick = () => {
    navigator.clipboard.writeText(document.getElementById("output-negative").value);
    toast("Copied negative");
  };

  bindFavoritesUi();

  document.getElementById("btn-character-library-save")?.addEventListener("click", saveCharacterLibraryPreset);

  document.getElementById("btn-prompt-extract")?.addEventListener("click", async () => {
    const promptText = document.getElementById("prompting-analyze-input")?.value.trim();
    if (!promptText) return toast("Вставьте промпт");
    const modelId = document.getElementById("prompting-source-model")?.value || state.model_id;
    try {
      const data = await api("/prompt/analyze/extract", {
        method: "POST",
        body: JSON.stringify({ prompt: promptText, model_id: modelId }),
      });
      document.getElementById("prompting-analyze-output").textContent = JSON.stringify(data, null, 2);
      toast("Core extracted");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-convert")?.addEventListener("click", async () => {
    const promptText = document.getElementById("prompting-analyze-input")?.value.trim();
    if (!promptText) return toast("Вставьте промпт");
    const source = document.getElementById("prompting-source-model")?.value || state.model_id;
    const target = document.getElementById("prompting-target-model")?.value || state.model_id;
    const useLlm = Boolean(document.getElementById("prompt-zit-use-llm")?.checked);
    try {
      const data = await withLlmProgress(useLlm, "LLM refine (convert)", () =>
        api("/prompt/analyze/convert", {
          method: "POST",
          body: JSON.stringify({
            prompt: promptText,
            model_id: source,
            source_model: source,
            target_model: target,
            use_llm: useLlm,
          }),
        }),
      );
      if (data.format === "json" && data.prompt_json) {
        document.getElementById("prompting-analyze-output").textContent = JSON.stringify(data.prompt_json, null, 2);
        toast(`JSON prompt (${data.detected_format})`);
        return;
      }
      let output = data.positive || "—";
      if (data.zit_paragraphs?.length) {
        output = data.positive || "—";
      }
      document.getElementById("prompting-analyze-output").textContent = output;
      document.getElementById("output-positive").value = data.positive || "";
      if (data.negative != null) document.getElementById("output-negative").value = data.negative;
      const llmNote = data.used_llm ? " · LLM" : "";
      toast(`Converted (${data.detected_format})${llmNote}`);
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-normalize")?.addEventListener("click", async () => {
    const promptText = document.getElementById("prompting-analyze-input")?.value.trim();
    if (!promptText) return toast("Вставьте промпт");
    try {
      const data = await api("/prompt/analyze/normalize", {
        method: "POST",
        body: JSON.stringify({ prompt: promptText }),
      });
      document.getElementById("prompting-analyze-output").textContent = JSON.stringify(data, null, 2);
      toast("Weights normalized");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-import-merge")?.addEventListener("click", async () => {
    const promptText = document.getElementById("prompting-import-input")?.value.trim();
    if (!promptText) return toast("Вставьте промпт");
    const persist = document.getElementById("prompt-import-persist")?.checked;
    const useOllama = Boolean(document.getElementById("prompt-import-use-llm")?.checked);
    try {
      const data = await withLlmProgress(useOllama, "LLM classify (import)", () =>
        api("/prompt/import/merge", {
          method: "POST",
          body: JSON.stringify({ prompt: promptText, model_id: state.model_id, persist, use_ollama: useOllama }),
        }),
      );
      applyImportTouched(data.state || {}, data.report?.touched || []);
      clearGeneratedOutput();
      await preloadSubgroupMaps();
      refreshAllPanels();
      syncFormControlsFromState();
      renderPromptingImportReport(data);
      await refreshPromptingOverlayStats();
      if (data.llm_status) {
        llmSettingsCache = { ...(llmSettingsCache || {}), health: { ok: data.llm_status.healthy, error: data.llm_status.last_error } };
        applyLlmAvailabilityToPrompting();
      }
      notifyStateChange();
      toast("Import merged");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-import-classify")?.addEventListener("click", async () => {
    const promptText = document.getElementById("prompting-import-input")?.value.trim();
    if (!promptText) return toast("Вставьте промпт");
    const useOllama = Boolean(document.getElementById("prompt-import-use-llm")?.checked);
    try {
      const data = await withLlmProgress(useOllama, "LLM classify", () =>
        api("/prompt/import/classify", {
          method: "POST",
          body: JSON.stringify({ prompt: promptText, model_id: state.model_id, use_ollama: useOllama }),
        }),
      );
      document.getElementById("prompting-import-stats").textContent = `Classified: ${data.classified?.length ?? 0} · Deduped: ${data.deduped?.length ?? 0}`;
      const list = document.getElementById("prompting-import-list");
      list.innerHTML = (data.classified || [])
        .map((c) => `<li><span class="import-tag">${escapeHtml(c.label || c.phrase)}</span> <span class="import-meta">${escapeHtml(c.category_id)} · ${escapeHtml(c.subgroup)}</span></li>`)
        .join("") || "<li class='import-empty'>—</li>";
      if (data.llm_status) {
        llmSettingsCache = { ...(llmSettingsCache || {}), health: { ok: data.llm_status.healthy, error: data.llm_status.last_error } };
        applyLlmAvailabilityToPrompting();
      }
      toast("Classified");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-export-yaml")?.addEventListener("click", async () => {
    try {
      const data = await api("/prompt/import/export", { method: "POST", body: JSON.stringify({ pack_id: "imported_pack" }) });
      toast(`Exported ${data.files?.length ?? 0} files`);
      await refreshPromptingOverlayStats();
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-clear-overlay")?.addEventListener("click", async () => {
    try {
      const data = await api("/prompt/import/clear-overlay", { method: "POST", body: "{}" });
      toast(`Removed ${data.removed} overlay items`);
      await refreshPromptingOverlayStats();
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-prompt-nsfw")?.addEventListener("click", async () => {
    const promptText = document.getElementById("prompting-nsfw-input")?.value.trim();
    const force = document.getElementById("prompt-nsfw-force")?.checked;
    const useUserRewrite = Boolean(document.getElementById("prompt-nsfw-user-rewrite")?.checked);
    const userInstruction = (document.getElementById("prompt-nsfw-user-instruction")?.value || "").trim();
    if (useUserRewrite && !userInstruction) return toast("Введите инструкцию для User prompt rewrite");
    const useRewrite = !useUserRewrite && Boolean(document.getElementById("prompt-nsfw-rewrite")?.checked);
    const useLlm = useUserRewrite || useRewrite || Boolean(document.getElementById("prompt-nsfw-llm")?.checked);
    let llmMode = "catalog";
    if (useUserRewrite) llmMode = "user";
    else if (useRewrite) llmMode = "rewrite";
    const llmLabel = useUserRewrite ? "User rewrite (NSFW)" : useRewrite ? "LLM rewrite (NSFW)" : "LLM refine (NSFW)";
    try {
      const body = {
        model_id: state.model_id,
        intensity: activeNsfwIntensity,
        force,
        use_llm: useLlm,
        llm_mode: llmMode,
        keep_locked: Boolean(document.getElementById("prompt-nsfw-keep-locked")?.checked),
      };
      if (userInstruction) body.user_instruction = userInstruction;
      if (promptText) body.prompt = promptText;
      else body.state = state;
      const data = await withLlmProgress(useLlm, llmLabel, () =>
        api("/prompt/nsfw-style", { method: "POST", body: JSON.stringify(body) }),
      );
      document.getElementById("prompting-nsfw-output").textContent = data.after || "—";
      document.getElementById("output-positive").value = data.after || "";
      renderNsfwStylerReport(data);
      if (data.state && data.llm_mode !== "rewrite" && data.llm_mode !== "user") applyImportTouched(data.state, Object.keys(data.state));
      if (data.llm_status) {
        llmSettingsCache = { ...(llmSettingsCache || {}), health: { ok: data.llm_status.healthy, error: data.llm_status.last_error } };
        applyLlmAvailabilityToPrompting();
      }
      toast(data.used_llm ? "NSFW styler + LLM" : "NSFW styler applied");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-import").onclick = async () => {
    const promptText = document.getElementById("import-prompt").value.trim();
    if (!promptText) return toast("Вставьте промпт");
    try {
      const result = await api("/import", {
        method: "POST",
        body: JSON.stringify({ prompt: promptText, model_id: state.model_id }),
      });
      applyImportTouched(result.state || {}, result.report?.touched || []);
      if (result.state?.model_id) state.model_id = result.state.model_id;
      clearGeneratedOutput();
      await preloadSubgroupMaps();
      refreshAllPanels();
      syncFormControlsFromState();
      initStaticChips();
      renderImportReport(result.report);
      notifyStateChange();
      const n = result.report?.matched_count ?? 0;
      const u = result.report?.unknown_count ?? 0;
      toast(`Импорт: ${n} тегов, ${u} неизвестных`);
    } catch (e) {
      toast(`Ошибка импорта: ${e.message}`);
    }
  };

  document.getElementById("opt-group-mode").onchange = onGroupModeChanged;

  document.getElementById("btn-session-save")?.addEventListener("click", downloadSessionFile);
  document.getElementById("btn-session-load")?.addEventListener("click", () => {
    document.getElementById("session-file-input").click();
  });
  document.getElementById("btn-session-reset")?.addEventListener("click", resetSession);
  document.getElementById("session-file-input").onchange = handleSessionFileInput;

  // Server sessions
  document.getElementById("btn-session-save-server")?.addEventListener("click", openSessionSaveModal);
  document.getElementById("btn-session-load-server")?.addEventListener("click", openSessionLoadModal);
  document.getElementById("session-save-modal-close")?.addEventListener("click", closeSessionSaveModal);
  document.getElementById("session-save-modal-backdrop")?.addEventListener("click", closeSessionSaveModal);
  document.getElementById("session-save-cancel")?.addEventListener("click", closeSessionSaveModal);
  document.getElementById("session-save-form")?.addEventListener("submit", (e) => {
    submitSessionSave(e).catch((err) => toast("Ошибка: " + err.message));
  });
  document.getElementById("session-load-modal-close")?.addEventListener("click", closeSessionLoadModal);
  document.getElementById("session-load-modal-backdrop")?.addEventListener("click", closeSessionLoadModal);

  // Undo
  document.getElementById("btn-undo-state")?.addEventListener("click", undoLastStateChange);

  // History panel
  document.getElementById("btn-history-refresh")?.addEventListener("click", () => {
    loadHistoryPanel().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("history-model-filter")?.addEventListener("change", () => {
    loadHistoryPanel().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-history-clear")?.addEventListener("click", async () => {
    const modelFilter = document.getElementById("history-model-filter")?.value || "";
    const msg = modelFilter ? `Очистить историю для модели ${modelFilter}?` : "Очистить всю историю генераций?";
    if (!confirm(msg)) return;
    try {
      const url = modelFilter ? `/history?model_id=${encodeURIComponent(modelFilter)}` : "/history";
      await api(url, { method: "DELETE" });
      loadHistoryPanel();
      toast("История очищена");
    } catch (e) { toast("Ошибка: " + e.message); }
  });

  // Batch
  initBatchControls();

  // Forge
  loadForgeSettings();
  document.getElementById("btn-forge-save")?.addEventListener("click", () => {
    saveForgeSettings().catch((e) => toast("Ошибка: " + e.message));
  });
  // Batch slider live value
  const _batchSlider = document.getElementById("fq-batch-size-slider");
  const _batchValueEl = document.getElementById("forge-batch-value");
  if (_batchSlider && _batchValueEl) {
    _batchSlider.addEventListener("input", () => {
      _batchValueEl.textContent = _batchSlider.value;
    });
  }

  document.getElementById("btn-forge-test")?.addEventListener("click", () => {
    testForgeConnection().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-forge-reload")?.addEventListener("click", () => {
    reloadForgeOptions().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-forge-send")?.addEventListener("click", async () => {
    try {
      // Always sync Quick Settings to DB before sending so UI values are applied
      await applyForgeQuickSettings();
      await sendToForge();
    } catch (e) {
      toast("Forge error: " + e.message);
    }
  });
  document.getElementById("btn-forge-hires")?.addEventListener("click", () => {
    sendToForgeHires().catch((e) => toast("Forge error: " + e.message));
  });
  document.getElementById("btn-fq-apply")?.addEventListener("click", () => {
    applyForgeQuickSettings().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("fq-hires-enabled")?.addEventListener("change", (e) => {
    document.getElementById("fq-hires-params")?.classList.toggle("visible", e.target.checked);
  });

  // Hotkeys
  initHotkeys();
  document.getElementById("btn-restart-server")?.addEventListener("click", restartServer);
  document.getElementById("btn-llm-refresh-models")?.addEventListener("click", async () => {
    try {
      await refreshLlmModels();
      toast("Models refreshed");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });
  document.getElementById("btn-llm-test")?.addEventListener("click", async () => {
    try {
      const data = await withLlmProgress(true, "Проверка Ollama", () =>
        api("/llm/health", {
          method: "POST",
          body: JSON.stringify(readLlmFormSettings()),
        }),
      );
      renderLlmStatus(data.health);
      llmSettingsCache = { ...(llmSettingsCache || {}), settings: readLlmFormSettings(), health: data.health };
      applyLlmAvailabilityToPrompting();
      toast(data.health?.ok ? "LLM is healthy" : "Health check failed");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });
  document.getElementById("btn-llm-save")?.addEventListener("click", async () => {
    const settings = readLlmFormSettings();
    try {
      const data = await withLlmProgress(settings.enabled, "Проверка Ollama", () =>
        api("/llm/settings", {
          method: "PUT",
          body: JSON.stringify(settings),
        }),
      );
      llmSettingsCache = data;
      fillLlmSettingsForm(data.settings || {}, data.health?.models_available || []);
      renderLlmStatus(data.health, data.saved_with_warning ? "Saved with warning" : "");
      applyLlmAvailabilityToPrompting();
      toast(data.saved_with_warning ? "Сохранено, но LLM недоступен" : "LLM settings saved");
    } catch (e) {
      toast("Ошибка: " + e.message);
    }
  });

  document.getElementById("btn-refresh-debug").onclick = () => {
    advancedMetaLoaded = false;
    loadAdvancedMeta();
    toast("Debug refreshed");
  };

  document.getElementById("btn-refresh-plugins")?.addEventListener("click", () => {
    loadPluginsPanel();
    toast("Plugins refreshed");
  });

  document.getElementById("btn-refresh-rules")?.addEventListener("click", () => {
    loadRulesPanel();
    toast("Rules refreshed");
  });
  document.getElementById("btn-rules-save")?.addEventListener("click", saveRulesYaml);
  document.getElementById("btn-rules-use-default")?.addEventListener("click", useDefaultRules);
  document.getElementById("btn-rules-delete-profile")?.addEventListener("click", deleteRulesProfile);
  document.getElementById("btn-rules-download")?.addEventListener("click", downloadRulesYaml);
  document.getElementById("btn-rules-load-file")?.addEventListener("click", loadRulesFromFile);
  document.getElementById("rules-file-input")?.addEventListener("change", handleRulesFileSelected);
}

async function init() {
  initNavCounters();
  loadPersistedSession();
  state.character = sanitizeCharacter(state.character);
  initStaticChips();
  bindEvents();
  const llmSettingsPromise = loadLlmSettingsCard().catch(() => {});
  await Promise.all([ensureClothingStateCatalog(), loadWildcardsIndex()]);
  void llmSettingsPromise;
  refreshAllPanels();
  syncFormControlsFromState();
  loadFavorites();
  loadCharacterLibrary();
  if (pendingActiveTab && pendingActiveTab !== "style") {
    switchTab(pendingActiveTab);
  } else {
    notifyStateChange();
  }
  refreshPromptPreview();
  // Start heavy category preload only after first interactive render to avoid contention.
  preloadSubgroupMaps()
    .then(() => {
      refreshAllPanels();
      syncFormControlsFromState();
      refreshPromptPreview();
      notifyStateChange();
    })
    .catch(() => {});
}

// =============================================================
// UNDO
// =============================================================

function _undoPush() {
  try {
    const snapshot = JSON.stringify(buildPayload());
    // Don't push if identical to last entry
    if (undoStack.length && undoStack[undoStack.length - 1] === snapshot) return;
    undoStack.push(snapshot);
    if (undoStack.length > UNDO_STACK_MAX) undoStack.shift();
    document.getElementById("btn-undo-state")?.removeAttribute("disabled");
  } catch (_) {}
}

function undoLastStateChange() {
  if (undoStack.length < 2) {
    toast("Нечего отменять");
    return;
  }
  // Pop current, restore previous
  undoStack.pop();
  const prev = undoStack[undoStack.length - 1];
  try {
    applyPayloadToState(JSON.parse(prev));
    refreshAllPanels();
    syncFormControlsFromState();
    notifyStateChange();
    toast("Отменено");
  } catch (e) {
    toast("Ошибка undo: " + e.message);
  }
  if (undoStack.length <= 1) {
    document.getElementById("btn-undo-state")?.setAttribute("disabled", "");
  }
}

// =============================================================
// SERVER SESSIONS
// =============================================================

function openSessionSaveModal() {
  const el = document.getElementById("session-save-modal");
  const input = document.getElementById("session-save-name");
  if (el) el.classList.remove("hidden");
  if (input) { input.value = ""; setTimeout(() => input.focus(), 50); }
}

function closeSessionSaveModal() {
  document.getElementById("session-save-modal")?.classList.add("hidden");
}

async function submitSessionSave(event) {
  event?.preventDefault();
  const name = document.getElementById("session-save-name")?.value.trim();
  if (!name) return toast("Введите название");
  syncStateFromFormControls();
  try {
    await api("/sessions", {
      method: "POST",
      body: JSON.stringify({ name, state: serializeSession() }),
    });
    closeSessionSaveModal();
    toast(`Сессия «${name}» сохранена`);
  } catch (e) {
    toast("Ошибка сохранения: " + e.message);
  }
}

async function openSessionLoadModal() {
  const el = document.getElementById("session-load-modal");
  const listEl = document.getElementById("session-load-list");
  if (!el || !listEl) return;
  el.classList.remove("hidden");
  listEl.innerHTML = "Загрузка…";
  try {
    const data = await api("/sessions");
    const sessions = data.sessions || [];
    if (!sessions.length) {
      listEl.innerHTML = '<span style="color:var(--text-muted);font-size:13px">Нет сохранённых сессий.</span>';
      return;
    }
    listEl.innerHTML = sessions.map((s) => `
      <div class="session-load-item" data-session-id="${s.id}">
        <span class="session-load-name" title="${escapeHtml(s.name)}">${escapeHtml(s.name)}</span>
        <span class="session-load-date">${(s.created_at || "").slice(0, 10)}</span>
        <div class="session-load-actions">
          <button class="btn btn-secondary btn-sm session-load-btn" data-id="${s.id}">Load</button>
          <button class="btn-ghost danger session-delete-btn" data-id="${s.id}" title="Удалить">✕</button>
        </div>
      </div>
    `).join("");
    listEl.querySelectorAll(".session-load-btn").forEach((btn) => {
      btn.addEventListener("click", () => loadServerSession(Number(btn.dataset.id)));
    });
    listEl.querySelectorAll(".session-delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => deleteServerSession(Number(btn.dataset.id), btn));
    });
  } catch (e) {
    listEl.innerHTML = `<span style="color:#eb3b5a;font-size:12px">Ошибка: ${escapeHtml(e.message)}</span>`;
  }
}

function closeSessionLoadModal() {
  document.getElementById("session-load-modal")?.classList.add("hidden");
}

async function loadServerSession(id) {
  try {
    const data = await api(`/sessions/${id}`);
    const sessionData = data.session?.state;
    if (!sessionData) return toast("Сессия пуста");
    applySession(sessionData);
    closeSessionLoadModal();
    toast(`Сессия загружена`);
  } catch (e) {
    toast("Ошибка загрузки: " + e.message);
  }
}

async function deleteServerSession(id, btn) {
  if (!confirm("Удалить сессию?")) return;
  try {
    await api(`/sessions/${id}`, { method: "DELETE" });
    btn.closest(".session-load-item")?.remove();
    const listEl = document.getElementById("session-load-list");
    if (listEl && !listEl.querySelector(".session-load-item")) {
      listEl.innerHTML = '<span style="color:var(--text-muted);font-size:13px">Нет сохранённых сессий.</span>';
    }
  } catch (e) {
    toast("Ошибка удаления: " + e.message);
  }
}

// =============================================================
// GENERATION HISTORY
// =============================================================

async function loadHistoryPanel() {
  const listEl = document.getElementById("history-list");
  if (!listEl) return;
  listEl.innerHTML = "Загрузка…";
  try {
    const modelFilter = document.getElementById("history-model-filter")?.value || "";
    const url = modelFilter ? `/history?limit=50&model_id=${encodeURIComponent(modelFilter)}` : "/history?limit=50";
    const data = await api(url);
    const entries = data.history || [];
    if (!entries.length) {
      listEl.innerHTML = '<span style="color:var(--text-muted);font-size:13px">История пуста.</span>';
      return;
    }
    listEl.innerHTML = entries.map((e) => `
      <div class="history-item">
        <div class="history-item-header">
          <span>${escapeHtml(MODEL_LABELS[e.model_id] || e.model_id)} · ${(e.created_at || "").replace("T", " ").slice(0, 16)}</span>
          <div class="history-item-actions">
            <button class="btn btn-secondary btn-sm history-load-btn" data-id="${e.id}">Load</button>
            <button class="btn-ghost danger history-del-btn" data-id="${e.id}" title="Удалить">✕</button>
          </div>
        </div>
        <div class="history-item-prompt">${escapeHtml(e.positive || "")}</div>
      </div>
    `).join("");
    listEl.querySelectorAll(".history-load-btn").forEach((btn) => {
      const id = Number(btn.dataset.id);
      btn.addEventListener("click", () => {
        const entry = entries.find((e) => e.id === id);
        if (!entry?.payload?.state) return toast("Нет данных state");
        applySession(entry.payload.state, { skipOutputs: true });
        toast("State загружен из истории");
      });
    });
    listEl.querySelectorAll(".history-del-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api(`/history/${btn.dataset.id}`, { method: "DELETE" });
          btn.closest(".history-item")?.remove();
        } catch (e) { toast("Ошибка: " + e.message); }
      });
    });
  } catch (e) {
    listEl.innerHTML = `<span style="color:#eb3b5a;font-size:12px">Ошибка: ${escapeHtml(e.message)}</span>`;
  }
}

// =============================================================
// BATCH VARIATIONS
// =============================================================

function initBatchControls() {
  const slider = document.getElementById("batch-count");
  const display = document.getElementById("batch-count-display");
  const btnN = document.getElementById("btn-batch-n");
  if (slider) {
    slider.addEventListener("input", () => {
      const v = slider.value;
      if (display) display.textContent = v;
      if (btnN) btnN.textContent = v;
    });
  }

  document.getElementById("btn-batch-generate")?.addEventListener("click", async () => {
    const count = Number(document.getElementById("batch-count")?.value || 4);
    const axes = [...document.querySelectorAll(".batch-axis:checked")].map((cb) => cb.value);
    const resultsEl = document.getElementById("batch-results");
    if (resultsEl) { resultsEl.innerHTML = "Генерация…"; resultsEl.classList.remove("hidden"); }

    try {
      syncStateFromFormControls();
      const data = await api("/generate/batch", {
        method: "POST",
        body: JSON.stringify({ state: buildPayload(), count, randomize_axes: axes }),
      });
      const results = data.results || [];
      if (!resultsEl) return;
      if (!results.length) { resultsEl.innerHTML = "Нет результатов"; return; }

      resultsEl.innerHTML = results.map((r, i) => {
        const variedStr = Object.entries(r.varied_state || {})
          .filter(([, v]) => v)
          .map(([k, v]) => `${k}: ${v}`)
          .join(" · ");
        return `
          <div class="batch-result-item">
            <div class="batch-result-header">
              <span>#${i + 1} · ${escapeHtml(MODEL_LABELS[r.model_id] || r.model_id)}</span>
              <span>${r.quality_score?.score ?? "—"}/100</span>
            </div>
            ${variedStr ? `<div class="batch-result-header" style="font-style:italic">${escapeHtml(variedStr)}</div>` : ""}
            <div class="batch-result-prompt">${escapeHtml(r.positive || "")}</div>
            <div class="batch-result-actions">
              <button class="btn btn-secondary btn-sm batch-copy-btn" data-idx="${i}">Copy</button>
              <button class="btn btn-secondary btn-sm batch-forge-btn" data-idx="${i}">→ Forge</button>
            </div>
          </div>
        `;
      }).join("");

      resultsEl.querySelectorAll(".batch-copy-btn").forEach((btn) => {
        const r = results[Number(btn.dataset.idx)];
        btn.addEventListener("click", () => {
          navigator.clipboard.writeText(r.positive || "");
          toast("Скопировано");
        });
      });
      resultsEl.querySelectorAll(".batch-forge-btn").forEach((btn) => {
        const r = results[Number(btn.dataset.idx)];
        btn.addEventListener("click", () => sendToForge(r.positive, r.negative || ""));
      });
    } catch (e) {
      if (resultsEl) resultsEl.innerHTML = `<span style="color:#eb3b5a">Ошибка: ${escapeHtml(e.message)}</span>`;
    }
  });
}

// =============================================================
// FORGE INTEGRATION
// =============================================================

async function loadForgeSettings() {
  try {
    forgeSettingsCache = await api("/forge/settings");
    populateForgeSettingsForm(forgeSettingsCache);
    populateForgeQuickSettings(forgeSettingsCache);
    updateForgeSendCard(forgeSettingsCache);
    if (forgeSettingsCache.enabled) loadForgeOptions({ silent: true });
  } catch (_) {}
}

function populateForgeQuickSettings(s) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ""; };
  const setChk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
  set("fq-steps", s.default_steps);
  set("fq-cfg", s.default_cfg);
  set("fq-width", s.default_width);
  set("fq-height", s.default_height);
  set("fq-sampler", s.default_sampler);
  set("fq-scheduler", s.default_scheduler);
  set("fq-batch-size", s.batch_size ?? 1);
  const batchVal = s.batch_size ?? 1;
  const sliderEl = document.getElementById("fq-batch-size-slider");
  const batchLbl = document.getElementById("forge-batch-value");
  if (sliderEl) sliderEl.value = batchVal;
  if (batchLbl) batchLbl.textContent = batchVal;
  setChk("fq-hires-enabled", s.hires_enabled);
  set("fq-hires-upscaler", s.hires_upscaler);
  set("fq-hires-scale", s.hires_scale);
  set("fq-hires-steps", s.hires_steps);
  set("fq-hires-denoising", s.hires_denoising);
  set("fq-hires-cfg", s.hires_cfg ?? 0);
  set("fq-hires-resize-x", s.hires_resize_x ?? 0);
  set("fq-hires-resize-y", s.hires_resize_y ?? 0);
  setChk("fq-save-images", s.save_images);
  document.getElementById("fq-hires-params")?.classList.toggle("visible", !!s.hires_enabled);
}

async function applyForgeQuickSettings() {
  const get = (id) => document.getElementById(id)?.value ?? "";
  const getChk = (id) => document.getElementById(id)?.checked ?? false;
  const current = forgeSettingsCache || await api("/forge/settings");
  const updated = {
    ...current,
    default_steps: Number(get("fq-steps")) || current.default_steps,
    default_cfg: Number(get("fq-cfg")) || current.default_cfg,
    default_width: Number(get("fq-width")) || current.default_width,
    default_height: Number(get("fq-height")) || current.default_height,
    default_sampler: get("fq-sampler") || current.default_sampler,
    default_scheduler: get("fq-scheduler") || current.default_scheduler,
    batch_size: Math.min(4, Math.max(1, Number(document.getElementById("fq-batch-size-slider")?.value) || Number(get("fq-batch-size")) || current.batch_size || 1)),
    hires_enabled: getChk("fq-hires-enabled"),
    hires_upscaler: get("fq-hires-upscaler") || current.hires_upscaler,
    hires_scale: Number(get("fq-hires-scale")) || current.hires_scale,
    hires_steps: Number(get("fq-hires-steps")) ?? current.hires_steps,
    hires_denoising: Number(get("fq-hires-denoising")) || current.hires_denoising,
    hires_cfg: Number(get("fq-hires-cfg")) ?? 0,
    hires_resize_x: Number(get("fq-hires-resize-x")) ?? 0,
    hires_resize_y: Number(get("fq-hires-resize-y")) ?? 0,
    save_images: getChk("fq-save-images"),
  };
  try {
    forgeSettingsCache = await api("/forge/settings", { method: "PUT", body: JSON.stringify(updated) });
    populateForgeSettingsForm(forgeSettingsCache);
    toast("Forge settings saved");
  } catch (e) { toast("Ошибка: " + e.message); }
}

function populateForgeSettingsForm(s) {
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val ?? ""; };
  const setChk = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
  setChk("forge-enabled", s.enabled);
  set("forge-base-url", s.base_url);
  set("forge-checkpoint", s.default_checkpoint);
  set("forge-steps", s.default_steps);
  set("forge-cfg", s.default_cfg);
  set("forge-width", s.default_width);
  set("forge-height", s.default_height);
  set("forge-sampler", s.default_sampler);
  set("forge-scheduler", s.default_scheduler);
  set("forge-batch-size", s.batch_size ?? 1);
  setChk("forge-hires-enabled", s.hires_enabled);
  set("forge-hires-upscaler", s.hires_upscaler);
  set("forge-hires-scale", s.hires_scale);
  set("forge-hires-steps", s.hires_steps);
  set("forge-hires-denoising", s.hires_denoising);
  set("forge-hires-cfg", s.hires_cfg ?? 0);
  set("forge-hires-resize-x", s.hires_resize_x ?? 0);
  set("forge-hires-resize-y", s.hires_resize_y ?? 0);
  setChk("forge-save-images", s.save_images);
}

async function loadForgeSamplers() {
  await loadForgeOptions();
}

async function loadForgeOptions({ silent = false } = {}) {
  const fill = (id, items) => {
    const dl = document.getElementById(id);
    if (dl && items?.length) {
      dl.innerHTML = items.filter(Boolean).map((s) => `<option value="${escapeHtml(s)}"></option>`).join("");
    }
  };
  try {
    const data = await api("/forge/catalog");
    fill("forge-models-list", data.models);
    fill("forge-samplers-list", data.samplers);
    fill("forge-upscalers-list", data.upscalers);
    fill("forge-schedulers-list", data.schedulers);
    if (!silent && data.counts) {
      const c = data.counts;
      toast(`Forge loaded: ${c.models} models · ${c.samplers} samplers · ${c.upscalers} upscalers · ${c.schedulers} schedulers`);
    }
    return data;
  } catch (e) {
    if (!silent) toast("Forge catalog error: " + e.message);
  }
}

async function saveForgeSettings() {
  const get = (id) => document.getElementById(id)?.value ?? "";
  const getChk = (id) => document.getElementById(id)?.checked ?? false;
  const settings = {
    enabled: getChk("forge-enabled"),
    base_url: get("forge-base-url") || "http://127.0.0.1:7860",
    default_checkpoint: get("forge-checkpoint"),
    default_steps: Number(get("forge-steps")) || 20,
    default_cfg: Number(get("forge-cfg")) || 7.0,
    default_width: Number(get("forge-width")) || 832,
    default_height: Number(get("forge-height")) || 1216,
    default_sampler: get("forge-sampler") || "DPM++ 2M",
    default_scheduler: get("forge-scheduler") || "Karras",
    batch_size: Math.min(4, Math.max(1, Number(get("forge-batch-size")) || 1)),
    hires_enabled: getChk("forge-hires-enabled"),
    hires_upscaler: get("forge-hires-upscaler") || "4x-UltraSharp",
    hires_scale: Number(get("forge-hires-scale")) || 1.5,
    hires_steps: Number(get("forge-hires-steps")) || 15,
    hires_denoising: Number(get("forge-hires-denoising")) || 0.45,
    hires_cfg: Number(get("forge-hires-cfg")) || 0,
    hires_resize_x: Number(get("forge-hires-resize-x")) || 0,
    hires_resize_y: Number(get("forge-hires-resize-y")) || 0,
    save_images: getChk("forge-save-images"),
  };
  try {
    forgeSettingsCache = await api("/forge/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
    });
    updateForgeSendCard(forgeSettingsCache);
    if (forgeSettingsCache.enabled) loadForgeOptions({ silent: true });
    toast("Forge settings saved");
  } catch (e) {
    toast("Ошибка: " + e.message);
  }
}

async function testForgeConnection() {
  const badge = document.getElementById("forge-status-badge");
  if (badge) badge.textContent = "Checking…";
  try {
    const data = await api("/forge/health", { method: "POST" });
    const dot = document.getElementById("forge-status-dot");
    if (data.ok) {
      if (badge) badge.textContent = `✓ OK · ${data.sd_model_checkpoint || "no checkpoint"}`;
      if (dot) { dot.className = "forge-status-dot ok"; dot.title = "Connected"; }
      loadForgeOptions({ silent: true });
    } else {
      if (badge) badge.textContent = `✗ ${data.error || "unreachable"}`;
      if (dot) { dot.className = "forge-status-dot err"; dot.title = data.error || "Error"; }
    }
  } catch (e) {
    if (badge) badge.textContent = `✗ ${e.message}`;
  }
}

async function reloadForgeOptions() {
  const btn = document.getElementById("btn-forge-reload");
  if (btn) { btn.disabled = true; btn.textContent = "↺ Loading…"; }
  try {
    await loadForgeOptions({ silent: false });
  } catch (e) {
    toast("Reload error: " + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "↺ Reload"; }
  }
}

function updateForgeSendCard(settings) {
  const card = document.getElementById("forge-send-card");
  const hint = document.getElementById("forge-send-hint");
  const btn = document.getElementById("btn-forge-send");
  if (!card) return;
  if (settings?.enabled) {
    card.classList.remove("hidden");
    if (hint) hint.textContent = `${settings.base_url} · steps ${settings.default_steps} · CFG ${settings.default_cfg}`;
    if (btn) btn.removeAttribute("disabled");
  } else {
    card.classList.remove("hidden");
    if (hint) hint.textContent = "Forge не настроен — включите в Advanced → LLM Settings → Forge.";
    if (btn) btn.setAttribute("disabled", "");
  }
}

// Forge state
let _lastForgeResult = null;   // { positive, negative, seed }
let _lastForgeImages = [];     // all base64 images from last batch
let _lastForgeParams = null;
let _lastForgeInfo = null;
let _forgeProgressTimer = null;

function _forgeProgressStop() {
  if (_forgeProgressTimer) { clearInterval(_forgeProgressTimer); _forgeProgressTimer = null; }
  const prog = document.getElementById("forge-progress");
  const preview = document.getElementById("forge-preview-img");
  const skeleton = document.getElementById("forge-preview-skeleton");
  if (prog) prog.classList.add("hidden");
  if (preview) { preview.classList.add("hidden"); preview.src = ""; }
  if (skeleton) skeleton.classList.add("hidden");
}

function _forgeProgressStart(batchSize) {
  const prog = document.getElementById("forge-progress");
  const bar = document.getElementById("forge-progress-bar");
  const label = document.getElementById("forge-progress-label");
  const eta = document.getElementById("forge-progress-eta");
  const preview = document.getElementById("forge-preview-img");
  const skeleton = document.getElementById("forge-preview-skeleton");
  if (prog) prog.classList.remove("hidden");
  if (bar) bar.style.width = "0%";
  if (preview) { preview.classList.add("hidden"); preview.src = ""; }

  const n = Math.max(1, Math.min(4, batchSize || 1));
  if (skeleton) {
    skeleton.classList.remove("hidden");
    if (n > 1) {
      skeleton.innerHTML = Array.from({ length: n }, () =>
        `<div class="forge-skeleton-tile"></div>`
      ).join("");
      skeleton.classList.add("batch-mode");
    } else {
      skeleton.innerHTML = "";
      skeleton.classList.remove("batch-mode");
    }
  }

  _forgeProgressTimer = setInterval(async () => {
    try {
      const d = await api("/forge/progress");
      if (!d.ok || d.phase === "idle") return;
      const pct = Math.round(d.progress * 100);
      if (bar) bar.style.width = pct + "%";
      const phaseLabel = d.phase === "hires" ? "Hires fix" : "Generating";
      const stepInfo = d.steps > 0 ? ` · step ${d.step}/${d.steps}` : "";
      if (label) label.textContent = `${phaseLabel}${stepInfo}`;
      if (eta) eta.textContent = d.eta > 0 ? `${Math.ceil(d.eta)}s` : "";
      if (d.image && preview) {
        preview.src = `data:image/png;base64,${d.image}`;
        preview.classList.remove("hidden");
        if (skeleton) skeleton.classList.add("hidden");
      }
    } catch (_) { /* ignore transient errors during polling */ }
  }, 600);
}

function _renderForgeGenParams(params, info, seed) {
  const el = document.getElementById("forge-gen-params");
  if (!el) return;
  const p = params || {};
  const isHires = !!p.enable_hr;
  const displaySeed = seed ?? info?.seed ?? "?";
  const rows = [
    ["Seed", displaySeed],
    ["Steps", p.steps ?? "?"],
    ["CFG", p.cfg_scale ?? "?"],
    ["Sampler", [p.sampler_name, p.scheduler].filter(Boolean).join(" · ") || "?"],
    ["Size", p.width && p.height ? `${p.width} × ${p.height}` : "?"],
  ];
  if (isHires) {
    rows.push(["Hires scale", `×${p.hr_scale ?? "?"}`]);
    rows.push(["Hires steps", p.hr_second_pass_steps ?? "?"]);
    rows.push(["Denoise", p.denoising_strength ?? "?"]);
    if (p.hr_upscaler) rows.push(["Upscaler", p.hr_upscaler]);
  }
  if (p.override_settings?.sd_model_checkpoint) {
    rows.push(["Checkpoint", p.override_settings.sd_model_checkpoint]);
  }
  el.innerHTML = rows.map(([k, v]) =>
    `<div class="forge-param-row"><span class="forge-param-key">${k}</span><span class="forge-param-val">${v}</span></div>`
  ).join("");
}

function _selectForgeTile(idx) {
  const images = _lastForgeImages;
  if (!images.length) return;
  const info = _lastForgeInfo || {};
  const allSeeds = info.all_seeds || [];
  const seed = allSeeds[idx] ?? info.seed ?? -1;

  // show selected image in the main slot (visible below the grid)
  const imgEl = document.getElementById("forge-result-img");
  if (imgEl) {
    imgEl.src = `data:image/png;base64,${images[idx]}`;
    imgEl.style.display = "";
  }

  // update tile highlight
  document.querySelectorAll(".forge-batch-tile").forEach((t, i) => {
    t.classList.toggle("selected", i === idx);
  });

  // update gen params and last result for hires
  _renderForgeGenParams(_lastForgeParams, info, seed);
  if (_lastForgeResult) _lastForgeResult = { ..._lastForgeResult, seed };

  // update save button for selected image
  const saveBtn = document.getElementById("btn-forge-save-img");
  if (saveBtn) {
    saveBtn.onclick = () => {
      const a = document.createElement("a");
      a.href = `data:image/png;base64,${images[idx]}`;
      a.download = `forge_${seed}.png`;
      a.click();
    };
  }
}

function _renderForgeBatchGrid(images) {
  const grid = document.getElementById("forge-batch-grid");
  const singleImg = document.getElementById("forge-result-img");
  if (!grid) return;

  if (images.length <= 1) {
    grid.classList.add("hidden");
    grid.innerHTML = "";
    if (singleImg) singleImg.style.display = "";
    return;
  }

  // batch: show grid, hide single image (tile click sets it)
  grid.classList.remove("hidden");
  if (singleImg) singleImg.style.display = "none";

  grid.innerHTML = images.map((img, i) =>
    `<div class="forge-batch-tile${i === 0 ? " selected" : ""}" data-idx="${i}">` +
    `<img src="data:image/png;base64,${img}" alt="${i + 1}" loading="lazy" /></div>`
  ).join("");
  grid.querySelectorAll(".forge-batch-tile").forEach(tile => {
    tile.addEventListener("click", () => _selectForgeTile(Number(tile.dataset.idx)));
  });
}

async function _forgeZipSaveAll(images, info) {
  if (typeof JSZip === "undefined") {
    // fallback: sequential downloads
    images.forEach((img, i) => {
      const seed = (info?.all_seeds?.[i] ?? info?.seed ?? i);
      const a = document.createElement("a");
      a.href = `data:image/png;base64,${img}`;
      a.download = `forge_${seed}.png`;
      a.click();
    });
    return;
  }
  const zip = new JSZip();
  images.forEach((img, i) => {
    const seed = (info?.all_seeds?.[i] ?? info?.seed ?? i);
    zip.file(`forge_${seed}.png`, img, { base64: true });
  });
  const blob = await zip.generateAsync({ type: "blob" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `forge_batch_${Date.now()}.zip`;
  a.click();
  URL.revokeObjectURL(url);
}

async function sendToForge(positiveOverride, negativeOverride, extraOverride) {
  const positive = positiveOverride ?? document.getElementById("output-positive")?.value ?? "";
  const negative = negativeOverride ?? document.getElementById("output-negative")?.value ?? "";
  if (!positive) return toast("Нет промпта для отправки");

  const resultEl = document.getElementById("forge-result");
  const imgEl = document.getElementById("forge-result-img");
  const btn = document.getElementById("btn-forge-send");
  const hiresBtn = document.getElementById("btn-forge-hires");
  const saveBtn = document.getElementById("btn-forge-save-img");

  if (resultEl) resultEl.classList.add("hidden");
  if (hiresBtn) hiresBtn.classList.add("hidden");
  if (saveBtn) saveBtn.classList.add("hidden");
  document.getElementById("btn-forge-save-all")?.classList.add("hidden");
  if (btn) { btn.disabled = true; btn.textContent = "Generating…"; }

  const _batchSize = Math.max(1, Number(document.getElementById("fq-batch-size-slider")?.value) || Number(document.getElementById("fq-batch-size")?.value) || 1);
  _forgeProgressStart(_batchSize);

  try {
    const body = { positive, negative };
    if (extraOverride) body.override = extraOverride;
    const data = await api("/forge/send", { method: "POST", body: JSON.stringify(body) });

    if (data.images?.length) {
      const images = data.images;
      const info = data.info || {};
      const params = data.parameters || {};
      const isHires = !!params.enable_hr;
      const allSeeds = info.all_seeds || [];
      const firstSeed = allSeeds[0] ?? info.seed ?? -1;

      // store batch state
      _lastForgeImages = images;
      _lastForgeParams = params;
      _lastForgeInfo = info;
      _lastForgeResult = { positive, negative, seed: firstSeed };

      // render grid (hidden when single image)
      _renderForgeBatchGrid(images);

      // show first image in main slot
      const imgEl = document.getElementById("forge-result-img");
      if (imgEl) imgEl.src = `data:image/png;base64,${images[0]}`;

      _renderForgeGenParams(params, info, firstSeed);

      if (resultEl) resultEl.classList.remove("hidden");

      if (hiresBtn) {
        hiresBtn.classList.remove("hidden");
        hiresBtn.textContent = isHires ? "↑ Hires (again)" : "↑ Hires";
      }

      const saveBtn = document.getElementById("btn-forge-save-img");
      if (saveBtn) {
        saveBtn.classList.remove("hidden");
        saveBtn.onclick = () => {
          const seed = _lastForgeResult?.seed ?? firstSeed;
          const a = document.createElement("a");
          a.href = document.getElementById("forge-result-img")?.src || "";
          a.download = `forge_${seed}.png`;
          a.click();
        };
      }

      const saveAllBtn = document.getElementById("btn-forge-save-all");
      if (saveAllBtn) {
        if (images.length > 1) {
          saveAllBtn.classList.remove("hidden");
          saveAllBtn.onclick = () => _forgeZipSaveAll(images, info);
        } else {
          saveAllBtn.classList.add("hidden");
        }
      }

      toast(isHires ? "Hi-res готов" : images.length > 1 ? `${images.length} изображений получено` : "Изображение получено от Forge");
    }
  } catch (e) {
    toast("Forge error: " + e.message);
  } finally {
    _forgeProgressStop();
    if (btn) { btn.disabled = false; btn.textContent = "Send to Forge ▶"; }
  }
}

async function sendToForgeHires() {
  if (!_lastForgeResult) return toast("Сначала сгенерируйте изображение");
  const { positive, negative, seed } = _lastForgeResult;
  const btn = document.getElementById("btn-forge-hires");
  if (btn) { btn.disabled = true; btn.textContent = "Upscaling…"; }
  try {
    await sendToForge(positive, negative, {
      enable_hr: true,
      seed: seed ?? -1,
    });
  } finally {
    if (btn) { btn.disabled = false; }
  }
}

// =============================================================
// HOTKEYS  (Ctrl+Enter, Ctrl+Z, Ctrl+S)
// =============================================================

function initHotkeys() {
  document.addEventListener("keydown", (event) => {
    const tag = (event.target?.tagName || "").toLowerCase();
    const inInput = tag === "input" || tag === "textarea" || tag === "select";

    // Ctrl+Enter → Generate (works everywhere)
    if (event.ctrlKey && event.key === "Enter") {
      event.preventDefault();
      document.getElementById("btn-generate")?.click();
      return;
    }

    // Ctrl+S → Save session to server
    if (event.ctrlKey && event.key === "s") {
      event.preventDefault();
      openSessionSaveModal();
      return;
    }

    // Ctrl+Z → Undo (not in text inputs — let browser handle those)
    if (event.ctrlKey && event.key === "z" && !inInput) {
      event.preventDefault();
      undoLastStateChange();
      return;
    }
  });
}

init();
