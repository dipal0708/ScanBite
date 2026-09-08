import json
from fastapi import APIRouter, UploadFile, File, Form

from app.services.ocr import extract_text, split_label_sections
from app.services.ingredients import classify_all
from app.services.diet_rules import check_diet_fit, check_allergens
from app.services.scoring import parse_nutrition_numbers, score_sugar, score_additives, score_label
from app.agents.label_agent import explain_scan

router = APIRouter()


@router.post("/analyze")
async def analyze(images: list[UploadFile] = File(...), profile: str = Form("{}")):
    profile_data = json.loads(profile) if profile else {}
    diet_type = profile_data.get("diet_type", "vegetarian")
    meat_subprefs = profile_data.get("meat_subprefs", [])
    allergens = profile_data.get("allergens", [])
    health_flags = profile_data.get("health_flags", [])

    # 1. OCR every uploaded photo and combine.
    raw_texts = []
    for image in images:
        content = await image.read()
        raw_texts.append(extract_text(content))
    combined_raw_text = "\n".join(raw_texts)
    sections = split_label_sections(combined_raw_text)

    # 2. Parse + classify ingredients.
    classified = classify_all(sections["ingredients_text"])

    # 3. Deterministic diet-fit + allergen checks.
    diet_fit = check_diet_fit(classified, diet_type, meat_subprefs)
    allergen_flags = check_allergens(classified, allergens)

    # 4. Nutrition scoring.
    nutrition = parse_nutrition_numbers(sections["nutrition_text"])
    sugar_score = score_sugar(nutrition)
    additive_score = score_additives(classified)
    label_score = score_label(sugar_score, additive_score, diet_fit, allergen_flags)

    structured_result = {
        "diet_fit": diet_fit,
        "allergen_flags": allergen_flags,
        "scores": {
            "label": label_score,
            "sugar": sugar_score,
            "additives": additive_score,
            "dietFit": 100 if diet_fit["fits"] else 40,
        },
        "classified_ingredients": classified,
        "nutrition": nutrition,
        "health_flags": health_flags,
    }

    # 5. AI agent turns the structured result into a human explanation.
    explanation = explain_scan(structured_result)

    return {
        "ocrRawText": combined_raw_text,
        "scores": structured_result["scores"],
        "flags": diet_fit["flags"] + allergen_flags,
        "dietFit": diet_fit,
        "nutrition": nutrition,
        "classifiedIngredients": classified,
        "summary": explanation.get("summary"),
        "suggestions": explanation.get("suggestions", []),
    }
