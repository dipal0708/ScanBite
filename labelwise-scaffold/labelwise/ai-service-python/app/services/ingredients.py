"""
Ingredient parsing + classification.

Splits a raw ingredients string into individual ingredients (parenthesis-
aware, since sub-ingredients nest e.g. "Chocolate (sugar, cocoa butter)"),
then tags each one against a small seed knowledge base. In production,
seed this from Open Food Facts + manual curation instead of the inline
dict below, and back it with the `ingredients_kb` Postgres table.
"""

import re

# Seed knowledge base: canonical_name -> tags. Extend this a lot in production.
INGREDIENT_KB = {
    "sugar": {"category": "added_sugar"},
    "cane sugar": {"category": "added_sugar"},
    "high fructose corn syrup": {"category": "added_sugar"},
    "corn syrup": {"category": "added_sugar"},
    "dextrose": {"category": "added_sugar"},
    "sucrose": {"category": "added_sugar"},
    "glucose syrup": {"category": "added_sugar"},
    "honey": {"category": "added_sugar", "animal_derived": True},
    "aspartame": {"category": "artificial_sweetener"},
    "sucralose": {"category": "artificial_sweetener"},
    "sodium benzoate": {"category": "preservative", "e_number": "E211"},
    "potassium sorbate": {"category": "preservative", "e_number": "E202"},
    "monosodium glutamate": {"category": "flavor_enhancer", "e_number": "E621"},
    "soy lecithin": {"category": "emulsifier", "e_number": "E322"},
    "carrageenan": {"category": "emulsifier", "e_number": "E407"},
    "red 40": {"category": "colorant", "e_number": "E129"},
    "yellow 5": {"category": "colorant", "e_number": "E102"},
    "gelatin": {"category": "other", "animal_derived": True},
    "whey": {"category": "dairy", "animal_derived": True},
    "milk": {"category": "dairy", "animal_derived": True},
    "egg": {"category": "egg", "animal_derived": True},
    "egg white": {"category": "egg", "animal_derived": True},
    "chicken": {"category": "meat", "animal_derived": True, "meat_type": "chicken"},
    "beef": {"category": "meat", "animal_derived": True, "meat_type": "red_meat"},
    "pork": {"category": "meat", "animal_derived": True, "meat_type": "pork"},
    "bacon": {"category": "meat", "animal_derived": True, "meat_type": "pork"},
    "shrimp": {"category": "meat", "animal_derived": True, "meat_type": "seafood"},
    "fish": {"category": "meat", "animal_derived": True, "meat_type": "seafood"},
    "onion": {"category": "root_allium", "root_allium": True},
    "onion powder": {"category": "root_allium", "root_allium": True},
    "garlic": {"category": "root_allium", "root_allium": True},
    "garlic powder": {"category": "root_allium", "root_allium": True},
    "ginger": {"category": "root_allium", "root_allium": True},
    "leek": {"category": "root_allium", "root_allium": True},
    "shallot": {"category": "root_allium", "root_allium": True},
}

ADDED_SUGAR_SYNONYMS = {
    "sugar", "cane sugar", "high fructose corn syrup", "corn syrup",
    "dextrose", "sucrose", "glucose syrup", "honey", "brown sugar",
    "invert sugar", "malt syrup", "agave nectar",
}


def split_ingredients(ingredients_text: str) -> list[str]:
    """Split on commas that are NOT inside parentheses."""
    text = ingredients_text.strip().rstrip(".")
    if not text:
        return []

    parts, depth, current = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth = max(0, depth - 1)
            current += ch
        elif ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())

    return [p for p in parts if p]


def classify_ingredient(name: str) -> dict:
    clean = re.sub(r"\(.*?\)", "", name).strip().lower()
    lookup = INGREDIENT_KB.get(clean)

    if lookup:
        return {"name": name, "matched": clean, **lookup}

    # fuzzy contains-match fallback for unseeded ingredient names
    for key, tags in INGREDIENT_KB.items():
        if key in clean:
            return {"name": name, "matched": key, **tags}

    return {"name": name, "matched": None, "category": "unclassified"}


def classify_all(ingredients_text: str) -> list[dict]:
    return [classify_ingredient(name) for name in split_ingredients(ingredients_text)]
