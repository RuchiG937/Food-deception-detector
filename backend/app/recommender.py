import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np
import requests

logger = logging.getLogger("cleanlabel.recommender")

# ==========================================
# 0. Settings
# ==========================================
# Feature order used EVERYWHERE (AI prompt, local DB, live API), always per 100g:
#   [calories_kcal, protein_g, sugar_g, fat_g]
USE_LIVE_API = True          # False = only use fallback_db.json (good if it holds Indian products)
TOP_N = 2                    # how many swaps to return
API_TIMEOUT_SEC = 3.0
LIVE_POOL_SIZE = 10          # fetch more live products so ranking has real choice
DEFAULT_FEATURES = [400.0, 5.0, 5.0, 15.0]

# Rough "max" per 100g for each feature, so calories (hundreds) don't drown out protein/sugar (single digits)
FEATURE_SCALE = np.array([600.0, 40.0, 50.0, 60.0])

NUTRI_HEALTH_SCORE = {"A": 95, "B": 85, "C": 65}  # D / E / unknown grades are not suggested as swaps

# ==========================================
# 1. Small helpers
# ==========================================
def _to_float(value) -> Optional[float]:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def _to_features(value) -> Optional[List[float]]:
    """Returns a clean list of 4 non-negative numbers, or None if the data is not usable."""
    try:
        arr = [_to_float(x) for x in value]
    except TypeError:
        return None
    if len(arr) != 4 or any(x is None or x < 0 for x in arr):
        return None
    return arr


# ==========================================
# 2. Load Fallback Database from JSON
# ==========================================
# Looks for fallback_db.json in the same folder as this file.
DB_PATH = os.path.join(os.path.dirname(__file__), "fallback_db.json")


def _load_local_db() -> List[Dict[str, Any]]:
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        logger.error(f"Could not load fallback_db.json: {e}")
        return []

    items = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        feats = _to_features(item.get("features"))
        if feats is None:
            logger.warning(f"Skipping '{item.get('name')}' in fallback_db.json: 'features' must be 4 numbers")
            continue
        item = dict(item)
        item["features"] = feats
        items.append(item)
    return items


LOCAL_BACKUP_DB = _load_local_db()


# ==========================================
# 3. Math Logic (closeness of macros)
# ==========================================
def macro_closeness(v1: List[float], v2: List[float]) -> float:
    """
    0 to 1 score: how close the alternative's macros are to the scanned product (1 = identical).
    Values are scaled first, and distance is used (not cosine), because cosine ignores
    quantity: a product with half the sugar would look identical to the original.
    """
    a = np.array(v1) / FEATURE_SCALE
    b = np.array(v2) / FEATURE_SCALE
    dist = float(np.linalg.norm(a - b))
    return 1.0 / (1.0 + dist)


# ==========================================
# 4. Category mapping
# ==========================================
def _category_query(detected_category: str) -> Optional[str]:
    c = (detected_category or "").lower()
    if "cereal" in c or "oat" in c:
        return "cereals"
    if "bever" in c or "drink" in c or "juice" in c:
        return "beverages"
    if "chip" in c or "snack" in c or "namkeen" in c:
        return "snacks"
    if "bak" in c or "biscuit" in c or "cookie" in c or "bread" in c:
        return "biscuits"
    if "dairy" in c or "paneer" in c or "milk" in c or "cheese" in c or "butter" in c:
        return "dairies"
    if "sweet" in c or "chocolat" in c or "dessert" in c:
        return "chocolates"
    if "noodle" in c or "pasta" in c or "maggi" in c:
        return "noodles"
    if "sauce" in c or "ketchup" in c or "condiment" in c:
        return "sauces"
    
    # Agar koi nayi/anjaan category aaye, toh blank skip na kare, balki API ko uska pehla word bhej de
    words = c.replace("/", " ").split()
    return words[0] if words else "snacks"


def _local_for_category(cat_query: Optional[str]) -> List[Dict[str, Any]]:
    """Prefers local items of the same category. If none match (or names differ), uses all items."""
    if not cat_query:
        return LOCAL_BACKUP_DB
    key = cat_query[:4]  # chips -> chip, beverages -> beve, cereals -> cere
    matches = [i for i in LOCAL_BACKUP_DB if key in str(i.get("category", "")).lower()]
    return matches or LOCAL_BACKUP_DB


# ==========================================
# 5. Live API Fetch (Open Food Facts)
# ==========================================
def _goals_from_nutrients(nutriments: Dict[str, Any], feats: List[float]) -> List[str]:
    """Works out which diet goals a live product really suits, from its actual numbers."""
    cal, protein, sugar, _fat = feats
    goals = ["General Health"]
    if cal <= 400 and sugar <= 10:
        goals.append("Fat Loss / Calorie Deficit")
    if protein >= 15:
        goals.append("Muscle Gain / High Protein")
    carbs = _to_float(nutriments.get("carbohydrates_100g"))
    if carbs is not None and carbs <= 10:
        goals.append("Keto / Low Carb")
    salt = _to_float(nutriments.get("salt_100g"))
    if salt is not None and salt <= 0.3:
        goals.append("Heart Health / Low Sodium")
    return goals


def fetch_open_food_facts(category_search: str, limit: int = LIVE_POOL_SIZE) -> List[Dict[str, Any]]:
    """Fetches real market items from Open Food Facts API v2 (Free, No Auth Needed)"""
    try:
        url = "https://world.openfoodfacts.org/api/v2/search"
        headers = {"User-Agent": "CleanLabelAI-StudentHackathon - v1.0"}
        params = {
            "categories_tags": category_search,
            "fields": "product_name,nutriments,nutriscore_grade",
            "page_size": limit,
            "sort_by": "nutriscore_score",
        }
        res = requests.get(url, params=params, headers=headers, timeout=API_TIMEOUT_SEC)
        if res.status_code != 200:
            logger.warning(f"OpenFoodFacts returned status {res.status_code}")
            return []

        live_items = []
        for p in res.json().get("products", []):
            name = (p.get("product_name") or "").strip()
            nutriments = p.get("nutriments") or {}

            # Skip products with missing nutrition data (no made-up default numbers)
            feats = _to_features([
                nutriments.get("energy-kcal_100g"),
                nutriments.get("proteins_100g"),
                nutriments.get("sugars_100g"),
                nutriments.get("fat_100g"),
            ])
            grade = str(p.get("nutriscore_grade") or "").upper()
            if not name or feats is None or grade not in NUTRI_HEALTH_SCORE:
                continue

            live_items.append({
                "name": name,
                "category": category_search,
                "approx_price": "Check Online",
                "taste_profile": "Clean Market Alternative",
                "health_score": NUTRI_HEALTH_SCORE[grade],
                "features": feats,
                "target_goals": _goals_from_nutrients(nutriments, feats),
                "why": f"Verified profile from global food database (Nutri-Score: {grade}).",
            })
        return live_items
    except Exception as e:
        logger.warning(f"OpenFoodFacts API fallback triggered: {e}")
    return []


# ==========================================
# 6. Main Recommendation Engine
# ==========================================
def find_smart_swaps(detected_category: str, diet_goal: str, est_features: List[float]) -> List[Dict[str, Any]]:
    """
    Finds the best alternative products using three things:
      40% macro closeness (a believable swap), 40% healthiness, 20% match with the user's diet goal.
    """
    features = _to_features(est_features) or list(DEFAULT_FEATURES)
    cat_query = _category_query(detected_category)

    # Try live data first, fall back to the local JSON database if it fails or returns nothing
    dataset: List[Dict[str, Any]] = []
    if USE_LIVE_API and cat_query:
        dataset = fetch_open_food_facts(cat_query)
    if not dataset:
        dataset = _local_for_category(cat_query)

    goal = (diet_goal or "").strip()
    ranked = []
    for item in dataset:
        closeness = macro_closeness(features, item["features"])

        health = _to_float(item.get("health_score"))
        health = min(max(health if health is not None else 90.0, 0.0), 100.0) / 100.0

        goal_match = 1.0 if goal in (item.get("target_goals") or []) else 0.0

        score = 0.4 * closeness + 0.4 * health + 0.2 * goal_match
        match_rating = max(1.0, min(round(score * 100, 1), 99.0))

        ranked.append({
            "name": str(item["name"]),
            "approx_price": item.get("approx_price", "₹40 - ₹80"),
            "taste_profile": item.get("taste_profile", "Wholesome"),
            "health_score": item.get("health_score", 90),
            "match_rating": match_rating,
            "why": item.get("why") or "A cleaner alternative with a better nutrition profile.",
        })

    ranked.sort(key=lambda x: x["match_rating"], reverse=True)
    return ranked[:TOP_N]