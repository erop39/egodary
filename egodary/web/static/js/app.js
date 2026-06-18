/** eGOdary web UI — thin client for FastAPI backend */

const API = "/api";
const SESSION_STORAGE_KEY = "egodary.session.v1";
const SESSION_FILE_VERSION = 6;

const MODEL_LABELS = {
  illustrious: "Illustrious",
  anima: "Anima",
  zimage_turbo: "Z-Image Turbo",
};

let favoritesGenDefaults = null;
let activeFavoriteId = null;
let editingFavoriteId = null;
let addTagCategoriesCache = [];

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
        dress: "",
        top: "",
        bottom: "",
        underwear_layer: "",
        legwear: "",
        jacket: "",
      },
    },
    appearance: {
      hair: "",
      hair_color: "",
      makeup: [],
      accessories: [],
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
      { id: "footwear_thigh", label: "Thigh High & OTK", field: "footwear", categoryId: "outfit.footwear", subgroup: "thigh_high" },
      { id: "footwear_platform", label: "Platform & High Heels", field: "footwear", categoryId: "outfit.footwear", subgroup: "platform_heels" },
      { id: "footwear_fetish", label: "Fetish & Alt Boots", field: "footwear", categoryId: "outfit.footwear", subgroup: "fetish_boots" },
      { id: "footwear_casual", label: "Casual / Sporty NSFW", field: "footwear", categoryId: "outfit.footwear", subgroup: "casual_nsfw" },
    ],
  },
  {
    id: "gloves",
    label: "Gloves",
    children: [
      { id: "gloves_long", label: "Long / Opera", field: "gloves", categoryId: "outfit.gloves", subgroup: "long_opera" },
      { id: "gloves_short", label: "Short & Fashion", field: "gloves", categoryId: "outfit.gloves", subgroup: "short_fashion" },
      { id: "gloves_harness", label: "Harness / Bondage", field: "gloves", categoryId: "outfit.gloves", subgroup: "harness_bondage" },
      { id: "gloves_fingerless", label: "Fingerless & Alt", field: "gloves", categoryId: "outfit.gloves", subgroup: "fingerless_alt" },
    ],
  },
  {
    id: "cape",
    label: "Cape",
    children: [
      { id: "cape_long", label: "Long Dramatic", field: "cape", categoryId: "outfit.cape", subgroup: "long_dramatic" },
      { id: "cape_short", label: "Short / Cropped", field: "cape", categoryId: "outfit.cape", subgroup: "short_cropped" },
      { id: "cape_hooded", label: "Hooded & Fetish", field: "cape", categoryId: "outfit.cape", subgroup: "hooded_fetish" },
      { id: "cape_sheer", label: "Sheer / Revealing", field: "cape", categoryId: "outfit.cape", subgroup: "sheer_revealing" },
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
const fieldSelectionModes = new Map();
let conflictPreviewTimer = null;
let conflictPreviewRequest = 0;
let qualityPreviewRequest = 0;
let promptPreviewTimer = null;
let promptPreviewRequest = 0;

const FACE_VIBE_FIELDS = ["facial_expression", "age_maturity", "beauty_archetype", "facial_details"];
const CHARACTER_FACE_FIELDS = [
  "mouth_lips", "eyes", "eye_color", "skin", "face_shape", "eyebrows", "nose", "jaw_chin",
];
const CHARACTER_FACE_GROUP_IDS = new Set([
  "face_mouth_lips",
  "face_eyes",
  "face_skin",
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
  face: () => FACE_VIBE_FIELDS.filter((field) => state.face[field]).length,
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
    count += Object.values(state.outfit.conditions || {}).filter(Boolean).length;
    return count;
  },
  makeup: () => state.appearance.makeup.length,
  accessories: () => state.appearance.accessories.length,
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

const TREE_PANELS = [
  { tree: getCharacterStructureTree(), elId: "character-tree" },
  { tree: getFaceVibeTree(), elId: "face-tree" },
  { tree: OUTFIT_TREE, elId: "outfit-tree" },
  { tree: MAKEUP_TREE, elId: "makeup-tree" },
  { tree: ACCESSORIES_TREE, elId: "accessories-tree" },
  { tree: POSE_TREE, elId: "pose-tree" },
  { tree: window.CAMERA_TREE || [], elId: "camera-tree" },
  { tree: window.LIGHTING_TREE || [], elId: "lighting-tree" },
  { tree: window.ENVIRONMENT_TREE || [], elId: "environment-tree" },
  { tree: window.STYLE_TREE || [], elId: "style-tree" },
  { tree: window.FETISH_TREE || [], elId: "fetish-tree" },
];

const selectionCountEls = new Map();
let clothingConditionsByField = null;
let clothingConditionsLoadingPromise = null;

const CONDITION_FIELD_LABELS = {
  dress: "Dress wear condition",
  top: "Top wear condition",
  bottom: "Pants / jeans condition",
  underwear_layer: "Lingerie condition",
  legwear: "Stockings / fishnets condition",
  jacket: "Outerwear condition",
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

async function ensureClothingConditions() {
  if (clothingConditionsByField) return clothingConditionsByField;
  if (clothingConditionsLoadingPromise) {
    return clothingConditionsLoadingPromise;
  }
  clothingConditionsLoadingPromise = (async () => {
    try {
      const data = await api("/categories/outfit.clothing_condition");
      clothingConditionsByField = {};
      for (const item of data.items) {
        const field = item.meta?.field;
        const group = item.meta?.group || "Other";
        if (!field) continue;
        if (!clothingConditionsByField[field]) clothingConditionsByField[field] = {};
        if (!clothingConditionsByField[field][group]) clothingConditionsByField[field][group] = [];
        clothingConditionsByField[field][group].push(item);
      }
    } catch (_) {
      clothingConditionsByField = {};
    }
    return clothingConditionsByField;
  })();
  await clothingConditionsLoadingPromise;
  clothingConditionsLoadingPromise = null;
  return clothingConditionsByField;
}

async function renderConditionDropdown(leaf) {
  const panel = document.getElementById("outfit-condition-panel");
  const select = document.getElementById("outfit-condition-select");
  if (!panel || !select) return;

  const conditionField = leaf.conditionField;
  if (!conditionField) {
    panel.classList.add("hidden");
    return;
  }

  const garmentId = getGarmentForConditionField(conditionField);
  const groups = (await ensureClothingConditions())[conditionField];
  if (!groups) {
    panel.classList.add("hidden");
    return;
  }

  panel.classList.remove("hidden");
  document.querySelector(".condition-label").textContent = CONDITION_FIELD_LABELS[conditionField] || "Wear condition";

  const current = state.outfit.conditions?.[conditionField] || "";
  select.innerHTML = "";
  const none = document.createElement("option");
  none.value = "";
  none.textContent = garmentId ? "— No condition —" : "Select garment first";
  select.appendChild(none);

  for (const [groupLabel, items] of Object.entries(groups)) {
    const optgroup = document.createElement("optgroup");
    optgroup.label = groupLabel;
    for (const item of items) {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.label;
      optgroup.appendChild(option);
    }
    select.appendChild(optgroup);
  }

  select.value = current;
  select.disabled = !garmentId;
  select.onchange = () => {
    if (!state.outfit.conditions) state.outfit.conditions = {};
    state.outfit.conditions[conditionField] = select.value;
    notifyStateChange();
  };
}

function clearConditionForField(field) {
  if (!field || !state.outfit.conditions) return;
  state.outfit.conditions[field] = "";
}

function registerCategoryItems(categoryId, items) {
  if (!itemSubgroupMaps[categoryId]) itemSubgroupMaps[categoryId] = {};
  for (const item of items) {
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
  if (stored) return stored;
  if (count > 0) return "item";
  return "none";
}

function getStateValueForTreeNode(node) {
  if (!node?.field) return "";
  if (node.field === "makeup") return state.appearance.makeup;
  if (node.field === "accessories") return state.appearance.accessories;
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

function getTreeLeafSelectionState(node) {
  const scopeKey = nodeSelectionScopeKey(node);
  if (node.categoryId?.startsWith("style.") && !state.style?.enabled) {
    return { count: 0, mode: "off", scopeKey };
  }
  const value = getStateValueForTreeNode(node);
  let count = 0;
  if (Array.isArray(value)) {
    count = countItemsInSubgroup(node.categoryId, node.subgroup, value);
  } else if (valueMatchesNodeSubgroup(node, value)) {
    count = 1;
  }
  if (node.conditionField) {
    const garmentId = getGarmentForConditionField(node.conditionField);
    const conditionId = state.outfit.conditions?.[node.conditionField];
    if (garmentId && conditionId && garmentMatchesLeaf(node, garmentId)) {
      count += 1;
    }
  }
  const mode = getFieldSelectionMode(scopeKey, count);
  return { count, mode, scopeKey };
}

function applyCountDisplay(el, { count, mode }) {
  if (!el) return;
  el.classList.remove("tree-count-random", "tree-count-off", "tree-count-item");
  if (mode === "off") {
    el.textContent = "0";
    el.classList.add("tree-count-off");
    return;
  }
  if (mode === "random" && count > 0) {
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
        if (countEl) countEl.textContent = count > 0 ? String(count) : "";
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
  updateTreeCountsInContainer(getCharacterStructureTree(), document.getElementById("character-tree"));
  updateTreeCountsInContainer(getFaceVibeTree(), document.getElementById("face-tree"));
  for (const { tree, elId } of TREE_PANELS) {
    if (elId === "character-tree" || elId === "face-tree") continue;
    updateTreeCountsInContainer(tree, document.getElementById(elId));
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
    if (!data.version || data.version < SESSION_FILE_VERSION) {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      return false;
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
  initCameraPresets();
  initCameraPanel();
  initLightingPresets();
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
    "face.skin",
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
      conditions: {
        ...defaults.outfit.conditions,
        ...sanitizeStringRecord(data.outfit?.conditions, defaults.outfit.conditions),
      },
    },
    appearance: {
      hair: asString(data.appearance?.hair),
      hair_color: asString(data.appearance?.hair_color),
      makeup: asStringArray(data.appearance?.makeup),
      accessories: asStringArray(data.appearance?.accessories),
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
  const tree = window.ENVIRONMENT_TREE || [];
  if (!tree.length) {
    const chips = document.getElementById("environment-chips");
    if (chips) {
      chips.innerHTML = '<span style="color:#eb3b5a;font-size:12px">Environment catalog not loaded (environment-tree-data.js)</span>';
    }
    return;
  }

  const selectLeaf = (leaf) => {
    if (!leaf) return;
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
      );
      updateSelectionCounts();
    } else {
      selectionCountEls.delete(detailSelectionKey);
      document.getElementById("environment-detail-title").textContent = leaf.label;
    }
    const treeEl = document.getElementById("environment-tree");
    treeEl.innerHTML = "";
    renderCategoryTree(tree, treeEl, activeEnvironmentLeafId, selectLeaf);

    const container = document.getElementById("environment-chips");
    const opts = leaf.subgroup ? { subgroup: leaf.subgroup } : {};
    if (isMulti) {
      loadCategoryMultiChips(
        container,
        leaf.categoryId,
        () => getEnvironmentLeafValue(leaf),
        (v) => {
          setEnvironmentLeafValue(leaf, v);
          notifyStateChange();
        },
        { max: 2, randomCount: 1, ...opts },
      );
    } else {
      loadCategoryChips(
        container,
        leaf.categoryId,
        () => getEnvironmentLeafValue(leaf),
        (v) => {
          setEnvironmentLeafValue(leaf, v);
          notifyStateChange();
        },
        opts,
      );
    }
  };

  refreshEnvironmentPanel = () => {
    selectLeaf(findTreeLeaf(activeEnvironmentLeafId, tree) || tree[0]?.children?.[0]);
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
  const tree = window.STYLE_TREE || [];
  if (!tree.length) {
    const chips = document.getElementById("style-chips");
    if (chips) {
      chips.innerHTML = '<span style="color:#eb3b5a;font-size:12px">Style catalog not loaded (style-tree-data.js)</span>';
    }
    return;
  }

  const selectLeaf = (leaf) => {
    if (!leaf || !state.style.enabled) return;
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
      );
      updateSelectionCounts();
    } else {
      selectionCountEls.delete(detailSelectionKey);
      document.getElementById("style-detail-title").textContent = leaf.label;
    }
    const treeEl = document.getElementById("style-tree");
    treeEl.innerHTML = "";
    renderCategoryTree(tree, treeEl, activeStyleLeafId, selectLeaf);

    const container = document.getElementById("style-chips");
    const opts = leaf.subgroup ? { subgroup: leaf.subgroup } : {};
    if (isMulti) {
      const multiOpts = STYLE_MULTI_LIMITS[leaf.field] || { max: 4, randomCount: 1 };
      loadCategoryMultiChips(
        container,
        leaf.categoryId,
        () => state.style[leaf.field] || [],
        (v) => {
          state.style[leaf.field] = v;
          notifyStateChange();
        },
        { ...multiOpts, ...opts },
      );
    } else {
      loadCategoryChips(
        container,
        leaf.categoryId,
        () => state.style[leaf.field] || "",
        (v) => {
          state.style[leaf.field] = v;
          notifyStateChange();
        },
        opts,
      );
    }
  };

  refreshStylePanel = () => {
    initStyleEnabledChips();
    if (!state.style.enabled) return;
    selectLeaf(findTreeLeaf(activeStyleLeafId, tree) || tree[0]?.children?.[0]);
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

function findOutfitLeaf(leafId, nodes = OUTFIT_TREE) {
  return findTreeLeaf(leafId, nodes);
}

function isPoseLeafDisabled(node) {
  return Boolean(node.requiresGroup) && !state.group_mode;
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
      title.innerHTML = `<span class="tree-label">${node.label}</span><span class="tree-count">${groupCount > 0 ? groupCount : ""}</span>`;
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
    btn.className = "outfit-tree-item"
      + (depth > 0 ? " child" : "")
      + (node.id === activeLeafId ? " active" : "")
      + (disabled ? " disabled" : "");
    btn.innerHTML = `<span class="tree-label">${node.label}</span><span class="tree-count"></span>`;
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
  document.getElementById("outfit-detail-title").textContent = leaf.label;
  const tree = document.getElementById("outfit-tree");
  tree.innerHTML = "";
  renderOutfitTree(OUTFIT_TREE, tree);

  loadCategoryChips(
    document.getElementById("outfit-chips"),
    leaf.categoryId,
    () => state.outfit[leaf.field],
    async (v) => {
      handleOutfitFieldChange(leaf, v);
      await renderConditionDropdown(leaf);
    },
    leaf.subgroup ? { subgroup: leaf.subgroup } : {},
  );
  renderConditionDropdown(leaf);
}

function setDetailTitleWithSelectionCount(titleElId, label, selectionKey, getSubgroupValues, scopeKey = "") {
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
}

function initCategoryTreePanel({
  tree,
  treeElId,
  titleElId,
  chipsElId,
  getActiveLeafId,
  setActiveLeafId,
  getFieldValue,
  setFieldValue,
  multiOpts = null,
}) {
  const detailSelectionKey = `${treeElId}-detail`;
  const selectLeaf = (leaf) => {
    setActiveLeafId(leaf.id);
    const isMulti = Boolean(leaf.multi);
    if (isMulti) {
      setDetailTitleWithSelectionCount(titleElId, leaf.label, detailSelectionKey, () => {
        const values = getFieldValue();
        if (!Array.isArray(values)) return values ? [values] : [];
        if (!leaf.subgroup) return values;
        const map = itemSubgroupMaps[leaf.categoryId] || {};
        return values.filter((id) => map[id] === leaf.subgroup);
      }, nodeSelectionScopeKey(leaf));
      updateSelectionCounts();
    } else {
      setDetailTitleWithSelectionCount(titleElId, leaf.label, detailSelectionKey, () => {
        const value = getFieldValue();
        if (Array.isArray(value)) return value;
        return value || "";
      }, nodeSelectionScopeKey(leaf));
      updateSelectionCounts();
    }
    const treeEl = document.getElementById(treeElId);
    treeEl.innerHTML = "";
    renderCategoryTree(tree, treeEl, getActiveLeafId(), selectLeaf);

    const container = document.getElementById(chipsElId);
    const chipOpts = {
      ...(leaf.subgroup ? { subgroup: leaf.subgroup } : {}),
      selectionScope: nodeSelectionScopeKey(leaf),
    };
    if (leaf.multi) {
      loadCategoryMultiChips(
        container,
        leaf.categoryId,
        getFieldValue,
        setFieldValue,
        { ...multiOpts, ...chipOpts },
      );
    } else {
      loadCategoryChips(container, leaf.categoryId, getFieldValue, setFieldValue, chipOpts);
    }
  };

  selectLeaf(findTreeLeaf(getActiveLeafId(), tree));
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
    tree,
    treeElId: "character-tree",
    titleElId: "character-detail-title",
    chipsElId: "character-chips",
    getActiveLeafId: () => activeCharacterLeafId,
    setActiveLeafId: (id) => { activeCharacterLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeCharacterLeafId, tree);
      return resolveCharacterLeafAccess(leaf)?.get() ?? "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeCharacterLeafId, tree);
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
    tree,
    treeElId: "face-tree",
    titleElId: "face-detail-title",
    chipsElId: "face-chips",
    getActiveLeafId: () => activeFaceLeafId,
    setActiveLeafId: (id) => { activeFaceLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeFaceLeafId, tree);
      return leaf?.field ? (state.face[leaf.field] || "") : "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeFaceLeafId, tree);
      if (leaf?.field) state.face[leaf.field] = v;
    },
  });
}

function initMakeupPanel() {
  initCategoryTreePanel({
    tree: MAKEUP_TREE,
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
      clearGeneratedOutput();
      initAccessoriesPanel();
      notifyStateChange();
      toast("Все аксессуары отключены");
    };
  }
  initCategoryTreePanel({
    tree: ACCESSORIES_TREE,
    treeElId: "accessories-tree",
    titleElId: "accessories-detail-title",
    chipsElId: "accessories-chips",
    getActiveLeafId: () => activeAccessoriesLeafId,
    setActiveLeafId: (id) => { activeAccessoriesLeafId = id; },
    getFieldValue: () => state.appearance.accessories,
    setFieldValue: (v) => {
      state.appearance.accessories = Array.isArray(v) ? v.slice(0, 4) : [];
    },
    multiOpts: { max: 4, randomCount: 2 },
  });
}

function initPosePanel() {
  const selectLeaf = (leaf) => {
    if (isPoseLeafDisabled(leaf)) {
      toast("Couple poses require Group mode (2girls)");
      return;
    }
    activePoseLeafId = leaf.id;
    document.getElementById("pose-detail-title").textContent = leaf.label;
    const treeEl = document.getElementById("pose-tree");
    treeEl.innerHTML = "";
    renderCategoryTree(POSE_TREE, treeEl, activePoseLeafId, selectLeaf, 0, { isDisabled: isPoseLeafDisabled });

    loadCategoryChips(
      document.getElementById("pose-chips"),
      leaf.categoryId,
      () => state.pose,
      (v) => { state.pose = v; },
      leaf.subgroup ? { subgroup: leaf.subgroup } : {},
    );
  };

  const leaf = findTreeLeaf(activePoseLeafId, POSE_TREE);
  if (!leaf || isPoseLeafDisabled(leaf)) {
    if (leaf?.categoryId === "pose.couple") state.pose = "";
    activePoseLeafId = "pose_standing_seductive";
  }
  selectLeaf(findTreeLeaf(activePoseLeafId, POSE_TREE));
}

function onGroupModeChanged() {
  state.group_mode = document.getElementById("opt-group-mode").checked;
  const activeLeaf = findTreeLeaf(activePoseLeafId, POSE_TREE);
  if (activeLeaf?.categoryId === "pose.couple" && !state.group_mode) {
    state.pose = "";
    activePoseLeafId = "pose_standing_seductive";
  }
  initPosePanel();
  notifyStateChange();
}

let activeCameraLeafId = "camera_angle_standard_angles";

function applyCameraPreset(preset) {
  for (const [field, value] of Object.entries(preset.camera || {})) {
    if (Object.prototype.hasOwnProperty.call(state.camera, field)) {
      state.camera[field] = value;
    }
  }
  initCameraPanel();
  notifyStateChange();
  toast(`Preset: ${preset.label}`);
}

function initCameraPresets() {
  const container = document.getElementById("camera-preset-chips");
  if (!container) return;
  container.innerHTML = "";
  for (const preset of window.CAMERA_PRESETS || []) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip chip-preset";
    chip.textContent = preset.label;
    chip.title = preset.hint || preset.label;
    chip.onclick = () => applyCameraPreset(preset);
    container.appendChild(chip);
  }
}

function initCameraPanel() {
  const tree = window.CAMERA_TREE || [];
  initCategoryTreePanel({
    tree,
    treeElId: "camera-tree",
    titleElId: "camera-detail-title",
    chipsElId: "camera-chips",
    getActiveLeafId: () => activeCameraLeafId,
    setActiveLeafId: (id) => { activeCameraLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeCameraLeafId, tree);
      return leaf?.field ? state.camera[leaf.field] : "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeCameraLeafId, tree);
      if (leaf?.field) state.camera[leaf.field] = v;
    },
  });
}

let activeLightingLeafId = "lighting_light_type_natural";
let activeFetishLeafId = "fetish_bdsm_restraints_items";

function applyLightingPreset(preset) {
  for (const [field, value] of Object.entries(preset.lighting || {})) {
    if (Object.prototype.hasOwnProperty.call(state.lighting, field)) {
      state.lighting[field] = value;
    }
  }
  for (const [field, value] of Object.entries(preset.camera || {})) {
    if (Object.prototype.hasOwnProperty.call(state.camera, field)) {
      state.camera[field] = value;
    }
  }
  initLightingPanel();
  initCameraPanel();
  notifyStateChange();
  toast(`Preset: ${preset.label}`);
}

function initLightingPresets() {
  const container = document.getElementById("lighting-preset-chips");
  if (!container) return;
  container.innerHTML = "";
  for (const preset of window.LIGHTING_PRESETS || []) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip chip-preset";
    chip.textContent = preset.label;
    chip.title = preset.hint || preset.label;
    chip.onclick = () => applyLightingPreset(preset);
    container.appendChild(chip);
  }
}

function initLightingPanel() {
  const tree = window.LIGHTING_TREE || [];
  initCategoryTreePanel({
    tree,
    treeElId: "lighting-tree",
    titleElId: "lighting-detail-title",
    chipsElId: "lighting-chips",
    getActiveLeafId: () => activeLightingLeafId,
    setActiveLeafId: (id) => { activeLightingLeafId = id; },
    getFieldValue: () => {
      const leaf = findTreeLeaf(activeLightingLeafId, tree);
      return leaf?.field ? state.lighting[leaf.field] : "";
    },
    setFieldValue: (v) => {
      const leaf = findTreeLeaf(activeLightingLeafId, tree);
      if (leaf?.field) state.lighting[leaf.field] = v;
    },
  });
}

function initFetishPanel() {
  const tree = window.FETISH_TREE || [];
  initCategoryTreePanel({
    tree,
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
  if (tab === "tagstudio") loadTagStudioPanel();
  if (tab === "favorites") loadFavorites();
  if (tab === "llm") loadLlmPanel();
  if (tab === "advanced") loadAdvancedMeta();
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
  output.textContent = JSON.stringify(data, null, 2);
}

async function runTagStudioDedupe() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const categoryId = document.getElementById("tagstudio-category")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (categoryId) params.set("category_id", categoryId);
  params.set("fuzzy_threshold", "0.9");
  const data = await api(`/tag-studio/deduplicate?${params.toString()}`);
  output.textContent = JSON.stringify(data, null, 2);
}

async function runTagStudioMigration() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const data = await api("/tag-studio/migrate/runtime-subcategory", {
    method: "POST",
    body: JSON.stringify({ status: "active" }),
  });
  output.textContent = JSON.stringify(data, null, 2);
  toast(`Migration done: ${data.migrated || 0}`);
}

async function runTagStudioRollback() {
  const output = document.getElementById("tagstudio-output");
  if (!output) return;
  const data = await api("/tag-studio/rollback/runtime-subcategory", {
    method: "POST",
    body: JSON.stringify({ status: "active" }),
  });
  output.textContent = JSON.stringify(data, null, 2);
  toast(`Rollback done: ${data.rolled_back || 0}`);
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
    await Promise.all([loadDebugPanel(), loadChangelogPanel()]);
  }
  await loadRulesPanel();
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
    window.CAMERA_TREE || [],
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
  const subgroupSelect = document.getElementById("add-tag-subgroup");
  if (!subgroupSelect) return [];
  const data = await api(`/categories/${encodeURIComponent(categoryId)}`);
  const subgroups = collectKnownSubgroups(categoryId, data);
  subgroupSelect.innerHTML = "";
  if (!subgroups.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "none";
    subgroupSelect.appendChild(option);
    subgroupSelect.disabled = true;
    subgroupSelect.dataset.hasSubgroups = "0";
    return subgroups;
  }
  for (const subgroup of subgroups) {
    const option = document.createElement("option");
    option.value = subgroup;
    option.textContent = subgroup;
    subgroupSelect.appendChild(option);
  }
  subgroupSelect.disabled = false;
  subgroupSelect.dataset.hasSubgroups = "1";
  return subgroups;
}

async function openAddTagModal() {
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
  const activeLeaf = findTreeLeaf(activeOutfitLeafId, OUTFIT_TREE)
    || findTreeLeaf(activeCharacterLeafId, getCharacterStructureTree())
    || findTreeLeaf(activeFaceLeafId, getFaceVibeTree())
    || findTreeLeaf(activeMakeupLeafId, MAKEUP_TREE)
    || findTreeLeaf(activeAccessoriesLeafId, ACCESSORIES_TREE)
    || findTreeLeaf(activePoseLeafId, POSE_TREE)
    || findTreeLeaf(activeCameraLeafId, window.CAMERA_TREE || [])
    || findTreeLeaf(activeLightingLeafId, window.LIGHTING_TREE || [])
    || findTreeLeaf(activeEnvironmentLeafId, window.ENVIRONMENT_TREE || [])
    || findTreeLeaf(activeStyleLeafId, window.STYLE_TREE || [])
    || findTreeLeaf(activeFetishLeafId, window.FETISH_TREE || []);
  if (activeLeaf?.categoryId) categorySelect.value = activeLeaf.categoryId;
  if (!categorySelect.value && categories[0]?.id) categorySelect.value = categories[0].id;
  const subgroups = await fillAddTagSubgroups(categorySelect.value);
  if (activeLeaf?.subgroup && subgroups.includes(activeLeaf.subgroup)) subgroupSelect.value = activeLeaf.subgroup;
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
        aliases,
        description,
        default_weight: defaultWeight,
        persist,
      }),
    });
    await preloadSubgroupMaps();
    clothingConditionsByField = null;
    await ensureClothingConditions();
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
  document.querySelectorAll("[data-open-add-tag-modal]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await openAddTagModal();
      } catch (e) {
        toast("Ошибка: " + e.message);
      }
    });
  });
  document.getElementById("add-tag-modal-close")?.addEventListener("click", closeAddTagModal);
  document.getElementById("add-tag-modal-backdrop")?.addEventListener("click", closeAddTagModal);
  document.getElementById("add-tag-cancel")?.addEventListener("click", closeAddTagModal);
  document.getElementById("add-tag-form")?.addEventListener("submit", createTagFromModal);
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
    loadTagStudioPanel().catch((e) => toast("Ошибка: " + e.message));
  });
  document.getElementById("btn-tagstudio-search")?.addEventListener("click", () => {
    loadTagStudioPanel().catch((e) => toast("Ошибка: " + e.message));
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
  await ensureClothingConditions();
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
    })
    .catch(() => {});
}

init();
