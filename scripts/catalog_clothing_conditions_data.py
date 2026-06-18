"""Clothing wear / damage / wet condition phrases by outfit field."""

CLOTHING_CONDITIONS: dict[str, dict[str, list[str]]] = {
    "legwear": {
        "Damage States": [
            "ripped fishnet stockings",
            "torn fishnet tights",
            "fishnets with large holes",
            "heavily ripped fishnets",
            "fishnet stockings with multiple tears",
            "distressed fishnet tights",
            "fishnets with big ragged holes",
            "partially torn fishnets",
        ],
        "Wet States": [
            "wet fishnet stockings",
            "soaked fishnet tights",
            "drenched fishnet pantyhose",
            "wet fishnets clinging to legs",
            "completely soaked fishnets",
            "rain-soaked fishnet stockings",
        ],
        "Wet + Ripped Combinations": [
            "wet ripped fishnet stockings",
            "soaked torn fishnets",
            "drenched ripped fishnet tights",
            "wet fishnets with holes",
            "soaked fishnet stockings with large tears",
            "wet ripped fishnets clinging to skin",
        ],
        "Shiny / Glossy Wet States": [
            "shiny wet fishnet stockings",
            "glossy soaked fishnets",
            "glistening wet fishnet tights",
            "shiny drenched fishnets",
            "wet fishnets with glossy sheen",
        ],
        "Other Conditions": [
            "fishnets with runs and ladders",
            "snagged fishnet tights",
            "worn out fishnet stockings",
            "over-stretched fishnets",
            "fishnets with uneven mesh",
        ],
    },
    "underwear_layer": {
        "Damage States": [
            "ripped lace lingerie",
            "torn bra and panties",
            "lingerie with holes",
            "partially torn lace bodysuit",
            "distressed lace underwear",
        ],
        "Wet States": [
            "wet lace lingerie",
            "soaked lingerie clinging to skin",
            "drenched lace bra and panties",
            "wet lingerie stuck to body",
            "completely soaked through lingerie",
        ],
        "Wet + Ripped Combinations": [
            "wet ripped lace lingerie",
            "soaked torn lingerie",
            "wet lace with holes clinging to skin",
        ],
        "Shiny / Glossy States": [
            "shiny wet satin lingerie",
            "glossy soaked lace bodysuit",
            "glistening wet lingerie",
        ],
        "Other Conditions": [
            "sheer wet lingerie",
            "lingerie in sweat",
            "partially removed lingerie",
            "messy and disheveled lingerie",
        ],
    },
    "top": {
        "Damage States": [
            "ripped t-shirt",
            "torn white blouse",
            "t-shirt with large holes",
            "ripped and frayed shirt",
            "distressed oversized t-shirt",
        ],
        "Wet States": [
            "wet t-shirt",
            "soaked white t-shirt clinging to body",
            "drenched blouse",
            "wet shirt stuck to skin",
            "completely soaked t-shirt",
        ],
        "Wet + Ripped Combinations": [
            "wet ripped t-shirt",
            "soaked torn blouse",
            "wet t-shirt with holes",
            "drenched ripped shirt clinging to skin",
        ],
        "Shiny / Glossy Wet States": [
            "shiny wet satin blouse",
            "glossy soaked t-shirt",
            "glistening wet button-up shirt",
        ],
        "Other Conditions": [
            "wet t-shirt effect",
            "sweat-soaked t-shirt",
            "partially unbuttoned wet shirt",
            "wrinkled wet blouse",
        ],
    },
    "dress": {
        "Damage States": [
            "ripped dress",
            "torn evening dress",
            "dress with large holes",
            "partially torn cocktail dress",
            "distressed maxi dress",
        ],
        "Wet States": [
            "wet dress",
            "soaked dress clinging to body",
            "drenched summer dress",
            "wet dress stuck to skin",
            "completely soaked through dress",
        ],
        "Wet + Ripped Combinations": [
            "wet ripped dress",
            "soaked torn evening dress",
            "wet dress with holes clinging to figure",
        ],
        "Shiny / Glossy Wet States": [
            "shiny wet satin dress",
            "glossy soaked silk dress",
            "glistening wet cocktail dress",
        ],
        "Other Conditions": [
            "wet dress effect",
            "rain-soaked dress",
            "partially unzipped wet dress",
            "sweat-drenched dress",
        ],
    },
    "bottom": {
        "Damage States": [
            "ripped jeans",
            "torn black jeans",
            "jeans with holes on knees",
            "heavily ripped distressed jeans",
            "jeans with large tears",
        ],
        "Wet States": [
            "wet jeans",
            "soaked jeans clinging to legs",
            "drenched denim pants",
            "wet jeans stuck to skin",
            "rain-soaked jeans",
        ],
        "Wet + Ripped Combinations": [
            "wet ripped jeans",
            "soaked torn jeans",
            "wet jeans with holes",
            "drenched ripped denim clinging to legs",
        ],
        "Shiny / Glossy States": [
            "shiny wet leather pants",
            "glossy soaked jeans",
            "glistening wet coated denim",
        ],
        "Other Conditions": [
            "faded and ripped jeans",
            "dirty wet jeans",
            "over-stretched wet jeans",
        ],
    },
    "jacket": {
        "Damage States": [
            "ripped leather jacket",
            "torn coat",
            "jacket with holes",
            "distressed denim jacket",
            "partially torn trench coat",
        ],
        "Wet States": [
            "wet leather jacket",
            "soaked coat",
            "drenched raincoat",
            "wet jacket clinging to body",
            "completely soaked outerwear",
        ],
        "Wet + Ripped Combinations": [
            "wet ripped leather jacket",
            "soaked torn coat",
            "wet jacket with holes",
        ],
        "Shiny / Glossy Wet States": [
            "shiny wet leather jacket",
            "glossy soaked coat",
            "glistening wet raincoat",
        ],
        "Other Conditions": [
            "heavy wet coat",
            "rain-drenched jacket",
            "wet and dirty outerwear",
            "partially open wet coat",
        ],
    },
}

CONDITION_FIELDS = tuple(CLOTHING_CONDITIONS.keys())
