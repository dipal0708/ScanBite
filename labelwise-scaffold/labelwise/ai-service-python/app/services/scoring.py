"""
Turns classified ingredients + parsed nutrition numbers into the 0-100
sub-scores shown on the result card. Deliberately simple/transparent
formulas — a health app's scoring should be explainable, not a black box.
"""

import re

# Daily guidance reference points (grams), used only to contextualize %,
# not as medical thresholds.
DAILY_ADDED_SUGAR_G = 25  # WHO conservative guidance
DAILY_SODIUM_MG = 2300
DAILY_SAT_FAT_G = 20


def parse_nutrition_numbers(nutrition_text: str) -> dict:
    def find(pattern):
        m = re.search(pattern, nutrition_text, re.IGNORECASE)
        return float(m.group(1)) if m else None

    return {
        "sugar_g": find(r"sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"),
        "added_sugar_g": find(r"added sugars?\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"),
        "sodium_mg": find(r"sodium\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*mg"),
        "sat_fat_g": find(r"saturated fat\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"),
        "fiber_g": find(r"fiber\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"),
        "protein_g": find(r"protein\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*g"),
    }


def score_sugar(nutrition: dict) -> int:
    added = nutrition.get("added_sugar_g") or nutrition.get("sugar_g") or 0
    pct_daily = added / DAILY_ADDED_SUGAR_G
    return max(0, round(100 - pct_daily * 100))


def score_additives(classified_ingredients: list[dict]) -> int:
    flagged_categories = {"artificial_sweetener", "preservative", "colorant", "flavor_enhancer"}
    count = sum(1 for i in classified_ingredients if i.get("category") in flagged_categories)
    return max(0, 100 - count * 15)


def score_label(sugar_score: int, additive_score: int, diet_fit: dict, allergen_flags: list) -> int:
    base = round((sugar_score + additive_score) / 2)
    if not diet_fit["fits"]:
        base -= 20
    if allergen_flags:
        base -= 30
    return max(0, min(100, base))
