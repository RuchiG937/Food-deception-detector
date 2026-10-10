# Food-deception-detector
Automated packaged food misleading marketing &amp; harmful additive auditor powered by Google Gemma 4 multimodal AI.

# CleanLabel AI 🕵️‍♀️🍏
> **Your AI-Powered Food Safety Auditor & Smart Swap Recommender**

## 🚀 The Problem
Modern packaged foods are filled with deceptive marketing. Brands highlight claims like "100% Real" or "Zero Added Sugar" on the front, while hiding harmful emulsifiers, complex chemical names (like Maltodextrin or INS 551), and hidden sugars on the back panel. Consumers lack the time and biochemical knowledge to decode these labels while shopping.

## 💡 Our Solution
**CleanLabel AI** empowers consumers to make informed, healthy choices instantly. By simply uploading a photo of a food product's ingredient list and nutritional table, our system:
1. **Audits the Label:** Uses Google's Gemma 4 Vision AI to extract exact brand names, decode complex chemical ingredients into plain language, and identify health risks.
2. **Personalizes the Verdict:** Tailors the analysis based on user-defined health profiles (e.g., Diabetic, PCOS, Kids Safe) and fitness goals.
3. **Recommends Smart Swaps:** If a product is unhealthy, our recommendation engine cross-references the Open Food Facts API (with a robust localized JSON fallback database for Indian brands like Saras or Amul) to suggest cleaner, healthier alternatives.

## ⚙️ Tech Stack
* **Backend:** Python, FastAPI, Uvicorn
* **AI & Vision:** Google GenAI SDK (Gemma-4 models)
* **Image Processing:** Pillow (PIL)
* **External APIs:** Open Food Facts API
* **Frontend:** Vanilla HTML5, CSS3, JavaScript
* **Deployment (Target):** Render

## ✨ Key Features
* **Smart Health Swaps:** Analyzes user-specific factors (like Diabetic, PCOS profiles, and Diet Goals) to recommend the most optimal, healthy alternative for any deceptive food item.
* **Direct E-Commerce Integration:** Provides direct purchase links to popular online platforms (like Blinkit, Zepto, or Instamart), allowing users to instantly buy the recommended healthy swaps.
* **Single-Image Vision Audit:** Optimized, memory-safe single-image processing tailored for fast mobile and web scanning.
* **Strict AI JSON Output:** Engineered prompt architecture ensuring reliable macro-nutrient extraction and categorical consistency.
* **Intelligent Category Mapping:** Custom backend routing that accurately translates local Indian food categories (e.g., Paneer, Dairy) into global API-friendly queries.
* **Resilient Architecture:** Fallback recommendation database triggers automatically if the primary external API fails or lacks localized data.
* **Zero-Waste Hacks:** Provides damage-control pairings and portion guidance for products already sitting in the user's pantry.  

## 🛠️ Local Setup & Installation

Follow these steps to run the CleanLabel AI backend locally:

**1. Clone the repository**
```bash
git clone https://github.com/RuchiG937/Food-deception-detector.git
cd Food-deception-detector
```

**2. Set up a virtual environment**
```bash
python -m venv venv
# For Windows (Git Bash / MINGW64)
source venv/Scripts/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure Environment Variables**
Create a `.env` file in the root directory and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_api_key_here
```

**5. Start the FastAPI Server**
```bash
uvicorn backend.app.main:app --reload
```
The API will be available at `http://127.0.0.1:8000`. You can view the interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

**6. Run the Frontend**
Open the `frontend/index.html` file using VS Code Live Server or simply double-click the file to open it in your browser.

## 📂 Project Structure
```text
Food-deception-detector/
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI entry point & image processing
│   │   ├── gemma_client.py     # AI prompt logic & Gemma 4 integration
│   │   ├── recommender.py      # Open Food Facts API & smart swap logic
│   │   └── fallback_db.json    # Localized offline recommendation database
├── frontend/
│   ├── index.html              # UI layout & upload interface
│   ├── style.css               # Styling
│   └── app.js                  # API integration & form handling
├── requirements.txt            # Python dependencies
└── README.md
```

## 🔮 Future Roadmap
* **Multi-Image Stitching:** Implementing backend image collaging to process front and back packet panels simultaneously without memory overhead.
* **Barcode Scanning Engine:** Integrating barcode lookups for instantaneous product identification.
* **Community Database:** Allowing users to submit verified healthy local swaps to expand the Indian context database.
