"""
OCR pipeline for packaged-food labels.

Preprocesses the photo (deskew/denoise/threshold) then runs Tesseract.
For blurry/glare-heavy photos, swap in a cloud OCR fallback
(Google Vision / AWS Textract) behind the same `extract_text` interface —
the rest of the pipeline only depends on getting back raw text plus the
best-guess split between the ingredients panel and nutrition facts panel.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import io
import re


def _preprocess(image_bytes: bytes) -> np.ndarray:
    img_array = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)  # denoise while keeping edges
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    return thresh


def extract_text(image_bytes: bytes) -> str:
    processed = _preprocess(image_bytes)
    pil_img = Image.fromarray(processed)
    return pytesseract.image_to_string(pil_img)


def split_label_sections(raw_text: str) -> dict:
    """
    Naive but effective heuristic split: most labels contain the literal
    words "Ingredients:" and "Nutrition Facts" — split on those anchors.
    A production version should also use layout/bounding-box info from
    the OCR engine rather than text alone.
    """
    ingredients_match = re.search(
        r"ingredients[:\s]+(.*?)(?:nutrition facts|contains|allergen|$)",
        raw_text,
        re.IGNORECASE | re.DOTALL,
    )
    nutrition_match = re.search(
        r"nutrition facts(.*)", raw_text, re.IGNORECASE | re.DOTALL
    )

    return {
        "ingredients_text": (ingredients_match.group(1).strip() if ingredients_match else ""),
        "nutrition_text": (nutrition_match.group(1).strip() if nutrition_match else ""),
        "raw_text": raw_text,
    }
