import io
from app.gemma_client import audit_food_label
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI(
    title="CleanLabel AI - Food Deception Detector API",
    version="1.0.0",
    description="Multimodal Food Safety Auditor powered by Gemma 4",
)


# ---- Rate limiter setup ----
def get_real_ip(request: Request):
  forwarded = request.headers.get("x-forwarded-for")
  if forwarded:
    return forwarded.split(",")[0].strip()
  return request.client.host if request.client else "127.0.0.1"


limiter = Limiter(key_func=get_real_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# ----------------------------

# Allow CORS for local development and Vercel production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://*.vercel.app",  # All vercel preview/prod links
        "*",  # Local testing smooth rakhne ke liye abhi '*' safe hai
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
  return {"status": "online", "service": "CleanLabel Backend"}


@app.post("/api/audit")
@limiter.limit("60/hour")  # Demo ke waqt fail na ho isliye balanced rakha
async def audit_endpoint(
    request: Request,
    image: UploadFile = File(...),
    health_profiles: str = Form(default="General Public"),
    front_claim: str = Form(default=""),
):
  if not image.content_type.startswith("image/"):
    raise HTTPException(
        status_code=400, detail="Uploaded file must be a valid image."
    )

  try:
    image_bytes = await image.read()

    # 5 MB payload limit
    if len(image_bytes) > 5 * 1024 * 1024:
      raise HTTPException(status_code=413, detail="Image too large (max 5 MB).")

    pil_image = Image.open(io.BytesIO(image_bytes))
    result = audit_food_label(
        image=pil_image,
        health_profiles=health_profiles,
        front_claim=front_claim,
    )
    return {"success": True, "data": result}
  except HTTPException:
    raise
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")