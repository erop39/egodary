"""Camera catalog subgroup definitions for camera_pack tags."""

CAMERA_FIELD_LABELS: dict[str, str] = {
    "angle": "Camera Angle",
    "framing": "Framing / Shot Type",
    "lens": "Focal Length",
    "focus": "Focus & Depth of Field",
    "composition": "Composition",
    "nsfw_shot": "NSFW-Specific Shots",
}

CAMERA_SUBGROUP_LABELS: dict[str, dict[str, str]] = {
    "angle": {
        "standard_angles": "Standard Angles",
        "extreme_dramatic": "Extreme & Dramatic",
        "nsfw_angles": "NSFW-oriented Angles",
    },
    "framing": {
        "close_intimate": "Close & Intimate",
        "medium_shots": "Medium Shots",
        "full_wide": "Full & Wide",
        "special_framing": "Special Framing",
    },
    "lens": {
        "focal_length": "Focal Length",
    },
    "focus": {
        "focus_dof": "Focus & DOF",
    },
    "composition": {
        "classic": "Classic Compositions",
        "cinematic": "Cinematic & Dramatic",
        "nsfw_composition": "NSFW / Erotic Composition",
    },
    "nsfw_shot": {
        "power_submission": "Power & Submission",
        "intimate_teasing": "Intimate & Teasing",
        "pov_immersive": "POV & Immersive",
        "dynamic_kinky": "Dynamic & Kinky",
    },
}

CAMERA_CATALOG: dict[str, dict[str, list[str]]] = {
    "angle": {
        "standard_angles": [
            "Eye Level",
            "Low Angle",
            "High Angle",
            "Dutch Angle",
        ],
        "extreme_dramatic": [
            "Extreme Low Angle",
            "Extreme High Angle",
            "Worm's Eye View",
            "Bird's Eye View",
            "Over the Shoulder",
            "POV (first person)",
        ],
        "nsfw_angles": [
            "Low Angle looking up (dominance)",
            "High Angle looking down (vulnerability)",
            "Low Angle from floor level",
            "High Angle from above (submission)",
            "Dutch Angle for tension",
        ],
    },
    "framing": {
        "close_intimate": [
            "Extreme Close-Up (face/eyes/lips)",
            "Close-Up",
            "Tight Close-Up",
            "Portrait",
        ],
        "medium_shots": [
            "Upper Body",
            "Cowboy Shot (thighs)",
            "Medium Shot",
        ],
        "full_wide": [
            "Full Body",
            "Full Body with space",
            "Wide Shot",
            "Extreme Wide Shot",
        ],
        "special_framing": [
            "Over the Shoulder Shot",
            "From Behind",
            "Mirror Reflection Shot",
            "Split Diopter / Two focus planes",
        ],
    },
    "lens": {
        "focal_length": [
            "24mm (wide angle)",
            "35mm",
            "50mm (standard)",
            "85mm (portrait)",
            "105mm",
            "135mm (strong compression)",
        ],
    },
    "focus": {
        "focus_dof": [
            "Shallow Depth of Field",
            "Deep Depth of Field",
            "Sharp focus on face",
            "Sharp focus on eyes",
            "Focus on lips",
            "Bokeh background",
            "Creamy bokeh",
            "Foreground blur",
            "Background blur (strong)",
        ],
    },
    "composition": {
        "classic": [
            "Rule of Thirds",
            "Centered composition",
            "Symmetrical composition",
            "Asymmetrical composition",
            "Leading lines",
            "Negative space",
        ],
        "cinematic": [
            "Cinematic composition",
            "Dramatic angle",
            "Low key composition",
            "High key composition",
            "Silhouette composition",
            "Rim lighting composition",
        ],
        "nsfw_composition": [
            "Focus on body curves",
            "Emphasis on legs / thighs",
            "Emphasis on chest",
            "Emphasis on ass (from behind)",
            "Intimate close framing",
        ],
    },
    "nsfw_shot": {
        "power_submission": [
            "Low angle dominance shot",
            "High angle submission shot",
            "Looking up from below",
            "Looking down from above",
        ],
        "intimate_teasing": [
            "Extreme close-up on lips",
            "Extreme close-up on eyes",
            "Close-up on neck and cleavage",
            "Focus on inner thighs",
            "Focus on ass (bent over)",
        ],
        "pov_immersive": [
            "POV (male gaze)",
            "POV from below",
            "Over the shoulder POV",
            "Mirror POV",
        ],
        "dynamic_kinky": [
            "Dutch angle erotic tension",
            "Low angle looking up skirt",
            "High angle on kneeling figure",
            "Bent over from behind framing",
            "Legs spread framing",
        ],
    },
}

# Preset definitions — labels resolved to item ids by build_camera_catalog.py
CAMERA_PRESETS: list[dict[str, str]] = [
    {
        "id": "dominant_view",
        "label": "Доминирующий вид",
        "hint": "Low Angle + Cowboy Shot + 35mm + Shallow DOF",
        "angle": "Low Angle",
        "framing": "Cowboy Shot (thighs)",
        "lens": "35mm",
        "focus": "Shallow Depth of Field",
    },
    {
        "id": "vulnerability",
        "label": "Уязвимость",
        "hint": "High Angle + Close-Up + 85mm",
        "angle": "High Angle",
        "framing": "Close-Up",
        "lens": "85mm (portrait)",
    },
    {
        "id": "intimate_portrait",
        "label": "Интимный портрет",
        "hint": "Close-Up + 105mm + Shallow DOF + focus on eyes",
        "framing": "Close-Up",
        "lens": "105mm",
        "focus": "Sharp focus on eyes",
    },
    {
        "id": "pov_erotic",
        "label": "POV эротика",
        "hint": "POV + Extreme Close-Up + 50mm",
        "angle": "POV (first person)",
        "framing": "Extreme Close-Up (face/eyes/lips)",
        "lens": "50mm (standard)",
    },
    {
        "id": "body_silhouette",
        "label": "Силуэт и форма тела",
        "hint": "Full Body + 35mm + Low Angle",
        "angle": "Low Angle",
        "framing": "Full Body",
        "lens": "35mm",
    },
    {
        "id": "tension",
        "label": "Напряжение",
        "hint": "Dutch Angle + Upper Body + 50mm",
        "angle": "Dutch Angle",
        "framing": "Upper Body",
        "lens": "50mm (standard)",
    },
]

# Compatibility warnings — label tuples resolved at build time
CAMERA_COMPAT_WARNINGS: list[dict] = [
    {
        "message": "Low angle + extreme close-up may heavily distort the face.",
        "angle_labels": [
            "Low Angle",
            "Extreme Low Angle",
            "Low Angle looking up (dominance)",
            "Low Angle from floor level",
        ],
        "framing_labels": [
            "Extreme Close-Up (face/eyes/lips)",
            "Tight Close-Up",
        ],
    },
    {
        "message": "High angle + full body can look awkward — check composition.",
        "angle_labels": [
            "High Angle",
            "Extreme High Angle",
            "High Angle looking down (vulnerability)",
            "High Angle from above (submission)",
        ],
        "framing_labels": ["Full Body", "Full Body with space", "Wide Shot", "Extreme Wide Shot"],
    },
    {
        "message": "24mm close-up causes strong facial distortion.",
        "lens_labels": ["24mm (wide angle)"],
        "framing_labels": [
            "Extreme Close-Up (face/eyes/lips)",
            "Close-Up",
            "Tight Close-Up",
            "Portrait",
        ],
    },
    {
        "message": "105mm + full body compresses the figure too much.",
        "lens_labels": ["105mm", "135mm (strong compression)"],
        "framing_labels": ["Full Body", "Full Body with space", "Wide Shot", "Extreme Wide Shot"],
    },
    {
        "message": "Dutch angle works best with dynamic or tense poses.",
        "angle_labels": ["Dutch Angle", "Dutch Angle for tension"],
        "requires_static_pose": True,
    },
    {
        "message": "Extreme close-up pairs best with 85mm or 105mm lenses.",
        "framing_labels": ["Extreme Close-Up (face/eyes/lips)", "Tight Close-Up"],
        "lens_labels": ["24mm (wide angle)", "35mm"],
    },
    {
        "message": "Full body framing works best with 24–50mm lenses.",
        "framing_labels": ["Full Body", "Full Body with space"],
        "lens_labels": ["85mm (portrait)", "105mm", "135mm (strong compression)"],
    },
]

# Lens × pose auto-fix (extends legacy hardcoded rule)
CAMERA_LENS_POSE_FIXES: list[dict] = [
    {
        "lens_label": "85mm (portrait)",
        "pose_ids": ["on_all_fours_ass_high_chest_low"],
        "target_lens_label": "35mm",
        "message": "Lens auto-switched to 35mm for floor pose visibility.",
    },
    {
        "lens_label": "105mm",
        "pose_ids": ["on_all_fours_ass_high_chest_low"],
        "target_lens_label": "35mm",
        "message": "Lens auto-switched to 35mm for floor pose visibility.",
    },
]
