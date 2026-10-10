import io
import logging
from typing import List
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps

from app.gemma_client import audit_food_label
from app.recommender import find_smart_swaps

logger = logging.getLogger("cleanlabel.api")

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB (same limit as the frontend)
MAX_IMAGE_SIDE = 1600              # big phone photos are shrunk before sending to AI
VALID_INTENTS = {"pre_purchase", "post_purchase"}

app = FastAPI(title="CleanLabel AI Backend", version="1.2.0")

# No cookies/logins are used, so credentials are not needed.
# (Wildcard origin together with credentials is an unsafe combination.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "CleanLabel AI API running with Gemma 4"}


@app.get("/health")
def health():
    # Lightweight endpoint, useful to wake up a sleeping free server
    return {"status": "ok"}


def _load_image(image_bytes: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)  # fixes sideways phone photos
    img = img.convert("RGB")
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    return img

@app.post("/api/audit")
async def audit_label_endpoint(
    image: UploadFile = File(...),  # Wapas 'image' set kar diya
    health_profiles: str = Form(""),
    front_claim: str = Form(""),
    diet_goal: str = Form("General Health"),
    intent: str = Form("pre_purchase"),
):
    # ---- Validate & read image ----
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    image_bytes = await image.read(MAX_IMAGE_BYTES + 1)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 8 MB).")

    try:
        pil_image = _load_image(image_bytes)
    except Exception:
        logger.exception("Could not read uploaded image")
        raise HTTPException(status_code=400, detail="Invalid image file.")

    # ---- Clean inputs ----
    if intent not in VALID_INTENTS:
        intent = "pre_purchase"
    health_profiles = health_profiles.strip()[:300]
    front_claim = front_claim.strip()[:200]
    diet_goal = diet_goal.strip()[:100] or "General Health"

    # ---- Step 1: AI audit ----
    try:
        audit_result = await run_in_threadpool(
            audit_food_label,
            pil_image,
            health_profiles,
            front_claim,
            diet_goal=diet_goal,
            intent=intent,
        )
    except Exception:
        logger.exception("AI audit failed")
        raise HTTPException(status_code=502, detail="The AI analysis failed.")

    # ---- Step 2: Smart swaps ----
    smart_swaps = []
    if not audit_result.get("is_product_optimal", False):
        try:
            smart_swaps = await run_in_threadpool(
                find_smart_swaps,
                audit_result.get("category", "Snacks / Chips"),
                diet_goal,
                audit_result.get("estimated_macros"),
            )
        except Exception:
            logger.exception("Recommender failed")
            smart_swaps = []

    audit_result["smart_swaps"] = smart_swaps
    audit_result["current_intent"] = intent
    return audit_result