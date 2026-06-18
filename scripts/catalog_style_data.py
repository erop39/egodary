"""Style catalog definitions for style_pack tags."""

STYLE_FIELD_LABELS: dict[str, str] = {
    "art_style": "Art Style",
    "artist_style": "Artist Styles",
    "quality": "Rendering Quality",
    "aesthetic": "Aesthetic / Mood",
    "technique": "Technique / Styling",
}

STYLE_SUBGROUP_LABELS: dict[str, dict[str, str]] = {
    "art_style": {
        "anime_stylized": "Anime / Stylized",
        "realistic_semi": "Realistic / Semi-realistic",
        "illustration_artistic": "Illustration / Artistic",
        "other_styles": "Other Styles",
    },
    "artist_style": {
        "retro_pinup": "Retro Sci-Fi / Pin-up",
        "cyberpunk_scifi": "Cyberpunk / Sci-Fi",
        "other_artists": "Other Popular",
    },
    "quality": {
        "rendering_quality": "Rendering Quality",
    },
    "aesthetic": {
        "general": "General Aesthetics",
        "nsfw_sensual": "NSFW / Sensual",
        "nsfw": "NSFW",
        "styled_vibes": "Styled Vibes",
    },
    "technique": {
        "technique": "Technique / Styling",
    },
}

STYLE_CATALOG: dict[str, dict[str, list[str]]] = {
    "art_style": {
        "anime_stylized": [
            "Anime style",
            "Semi-realistic anime",
            "Detailed anime",
            "Clean anime style",
            "Anime illustration",
            "Anime screencap style",
            "Modern anime style",
            "Anime key visual",
        ],
        "realistic_semi": [
            "Realistic",
            "Semi-realistic",
            "Photorealistic",
            "Hyperrealistic",
            "Cinematic realism",
            "Realistic anime blend",
        ],
        "illustration_artistic": [
            "Illustration",
            "Digital illustration",
            "Concept art style",
            "Anime concept art",
            "Detailed illustration",
            "Stylized illustration",
        ],
        "other_styles": [
            "3D render",
            "Pixar style",
            "Disney style",
            "Western comic style",
            "Manga style",
            "Manhwa style",
            "Game CG style",
            "Visual novel style",
        ],
    },
    "artist_style": {
        "retro_pinup": [
            "Alfonso Azpiri style",
            "Hajime Sorayama style",
            "Boris Vallejo style",
            "Julie Bell style",
            "Frank Frazetta style",
            "Chris Achilleos style",
        ],
        "cyberpunk_scifi": [
            "Masamune Shirow style",
            "Syd Mead style",
            "Moebius style",
            "Simon Stålenhag style",
        ],
        "other_artists": [
            "Ilya Kuvshinov style",
            "WLOP style",
            "Artgerm style",
            "Ross Tran style",
            "Sakimichan style",
            "Loish style",
            "Alphonse Mucha style",
            "Greg Rutkowski style",
            "Zdzisław Beksiński style",
            "Junji Ito style",
        ],
    },
    "quality": {
        "rendering_quality": [
            "Masterpiece",
            "Best quality",
            "High quality",
            "Very detailed",
            "Extremely detailed",
            "Intricate details",
            "Sharp focus",
            "High resolution",
            "8k",
            "Ultra detailed",
            "Clean lines",
            "Beautiful rendering",
            "Professional illustration",
            "High-end anime production quality",
        ],
    },
    "aesthetic": {
        "general": [
            "Aesthetic",
            "Very aesthetic",
            "Beautiful composition",
            "Elegant",
            "Stylish",
            "Moody",
            "Atmospheric",
            "Dreamy",
            "Ethereal",
            "Dark aesthetic",
            "Bright aesthetic",
        ],
        "nsfw_sensual": [
            "Sensual",
            "Erotic",
            "Tasteful sensual",
            "Seductive atmosphere",
            "Lewd",
            "Suggestive",
            "Provocative",
            "Intimate",
            "Sultry",
        ],
        "nsfw": [
            "Uncensored",
            "Nude",
            "Explicit",
            "Spicy",
        ],
        "styled_vibes": [
            "Cyberpunk aesthetic",
            "Neon aesthetic",
            "Retro anime aesthetic",
            "Modern anime aesthetic",
            "Kawaii",
            "Dark fantasy",
            "Elegant mature",
            "Soft and delicate",
            "Cool and calculating",
            "Intense and dramatic",
        ],
    },
    "technique": {
        "technique": [
            "Clean lines and shading",
            "Soft shading",
            "Cell shading",
            "Detailed shading",
            "Gradient shading",
            "Dramatic shading",
            "Soft glow",
            "Rim lighting emphasis",
            "Volumetric lighting",
            "Beautiful color grading",
            "Cinematic color grading",
            "High contrast",
            "Low contrast",
            "Vibrant colors",
            "Muted colors",
        ],
    },
}

STYLE_EXCLUSIVE_GROUPS: list[list[str]] = [
    [
        "anime_style",
        "detailed_anime",
        "clean_anime_style",
        "anime_illustration",
        "anime_screencap_style",
        "modern_anime_style",
        "anime_key_visual",
        "manga_style",
        "manhwa_style",
        "game_cg_style",
        "visual_novel_style",
        "pixar_style",
        "disney_style",
        "western_comic_style",
    ],
    [
        "realistic",
        "semi_realistic",
        "photorealistic",
        "hyperrealistic",
        "cinematic_realism",
        "3d_render",
    ],
]

STYLE_BLEND_EXCEPTIONS = frozenset({"semi_realistic_anime", "realistic_anime_blend"})

STYLE_COMPAT_WARNINGS: list[dict] = [
    {
        "message": "Anime art style with photorealistic or hyperrealistic quality tags usually conflict.",
        "art_style_subgroup": "anime_stylized",
        "quality_ids": ["photorealistic", "hyperrealistic", "realistic"],
    },
    {
        "message": "Lewd / erotic aesthetics pair better with low-key or dramatic lighting.",
        "aesthetic_ids": ["lewd", "erotic", "provocative"],
        "lighting_nsfw_ids": [],
    },
    {
        "message": "Tasteful sensual aesthetic works best with soft lighting and elegant looks.",
        "aesthetic_ids": ["tasteful_sensual", "elegant", "intimate"],
    },
]
