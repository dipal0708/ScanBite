"""
Deterministic diet-fit checking. Kept rule-based (not LLM-based) on purpose:
correctness matters here, and every flag must be traceable to the exact
ingredient that triggered it. The LLM agent layer explains these flags in
plain language; it does not decide them.
"""

DIET_TYPES = {
    "vegan",
    "vegan_no_roots",
    "vegetarian",
    "vegetarian_with_eggs",
    "non_vegetarian",
}


def check_diet_fit(classified_ingredients: list[dict], diet_type: str, meat_subprefs: list[str]) -> dict:
    flags = []

    def flag(ingredient, reason):
        flags.append({"ingredient": ingredient["name"], "reason": reason})

    for ing in classified_ingredients:
        category = ing.get("category")
        animal_derived = ing.get("animal_derived", False)
        root_allium = ing.get("root_allium", False)
        meat_type = ing.get("meat_type")

        if diet_type == "vegan":
            if animal_derived:
                flag(ing, "Not vegan — this ingredient is animal-derived.")

        elif diet_type == "vegan_no_roots":
            if animal_derived:
                flag(ing, "Not vegan — this ingredient is animal-derived.")
            if root_allium:
                flag(ing, "Contains a root/allium ingredient you've excluded.")

        elif diet_type == "vegetarian":
            if category == "meat":
                flag(ing, "Contains meat or fish.")
            elif category == "egg":
                flag(ing, "Contains egg.")
            # dairy and honey are allowed for plain vegetarian

        elif diet_type == "vegetarian_with_eggs":
            if category == "meat":
                flag(ing, "Contains meat or fish.")
            # eggs and dairy allowed

        elif diet_type == "non_vegetarian":
            if category == "meat" and meat_type and meat_type not in meat_subprefs:
                flag(ing, f"Contains {meat_type.replace('_', ' ')}, which isn't in your allowed meats.")

    return {
        "diet_type": diet_type,
        "fits": len(flags) == 0,
        "flags": flags,
    }


def check_allergens(classified_ingredients: list[dict], allergens: list[str]) -> list[dict]:
    flags = []
    allergen_terms = {a.lower() for a in allergens}
    for ing in classified_ingredients:
        name_lower = ing["name"].lower()
        for term in allergen_terms:
            if term in name_lower:
                flags.append({"ingredient": ing["name"], "reason": f"Contains {term}, which you've flagged as an allergen."})
    return flags
