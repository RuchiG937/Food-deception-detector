// ==========================================
// 1. Configuration & Element Selection
// ==========================================
const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://127.0.0.1:8000"
  : "https://food-deception-detector.onrender.com";

const REQUEST_TIMEOUT_MS = 90000;      // 90 sec (free Render server can take time to wake up)
const SLOW_NOTICE_MS = 6000;           // show "server waking up" message after 6 sec
const MAX_FILE_SIZE_MB = 8;

// Base UI Elements
const dropArea = document.getElementById("dropArea");
const imageInput = document.getElementById("imageInput");
const imagePreview = document.getElementById("imagePreview");
const uploadPlaceholder = document.getElementById("uploadPlaceholder");
const analyzeBtn = document.getElementById("analyzeBtn");
const loader = document.getElementById("loader");
const loaderText = loader ? loader.querySelector("p") : null;
const emptyState = document.getElementById("emptyState");
const resultContent = document.getElementById("resultContent");

// Custom Input Elements
const dietGoalDropdown = document.getElementById("dietGoal");
const customDietInput = document.getElementById("customDietInput");
const otherHealthCb = document.getElementById("otherHealthCb");
const customHealthInput = document.getElementById("customHealthInput");

// Modal Elements
const offlineModal = document.getElementById("offlineModal");
const closeModalBtn = document.getElementById("closeModalBtn");
const modalProductName = document.getElementById("modalProductName");
const modalPrice = document.getElementById("modalPrice");
const modalTaste = document.getElementById("modalTaste");
const modalShelfTip = document.getElementById("modalShelfTip");

const DEFAULT_LOADER_TEXT = loaderText ? loaderText.textContent : "";
let selectedFile = null;

// ==========================================
// 2. Helper Functions (Security & Safety)
// ==========================================

// Escapes text so AI/backend output can never run as HTML or JavaScript (fixes XSS)
function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Safe number: returns a number between min and max, or fallback
function num(value, fallback = 0, min = -Infinity, max = Infinity) {
  const n = Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.min(max, Math.max(min, n));
}

function setLoaderText(text) {
  if (loaderText) loaderText.textContent = text;
}

// ==========================================
// 3. UI Event Listeners & Logic
// ==========================================

// Handle Image Upload
if (dropArea) {
  dropArea.addEventListener("click", () => imageInput.click());
}

if (imageInput) {
  imageInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
    // Allows choosing the same file again later
    e.target.value = "";
  });
}

function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please select an image file (JPG, PNG, etc.).");
    return;
  }
  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    alert(`Image is too large. Please use a photo under ${MAX_FILE_SIZE_MB} MB.`);
    return;
  }

  selectedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    imagePreview.src = e.target.result;
    imagePreview.classList.remove("hidden");
    uploadPlaceholder.classList.add("hidden");
  };
  reader.readAsDataURL(file);
}

// Toggle Custom Diet Input
if (dietGoalDropdown) {
  dietGoalDropdown.addEventListener("change", (e) => {
    if (e.target.value === "Custom") {
      customDietInput.classList.remove("hidden");
    } else {
      customDietInput.classList.add("hidden");
      customDietInput.value = "";
    }
  });
}

// Toggle Custom Health Input
if (otherHealthCb) {
  otherHealthCb.addEventListener("change", (e) => {
    if (e.target.checked) {
      customHealthInput.classList.remove("hidden");
    } else {
      customHealthInput.classList.add("hidden");
      customHealthInput.value = "";
    }
  });
}

// ---------- Modal ----------
function closeModal() {
  offlineModal.classList.add("hidden");
}

function openOfflineCard(name, price, taste) {
  // textContent is already safe (no HTML is parsed)
  modalProductName.textContent = name;
  modalPrice.textContent = price || "₹35 - ₹50 (Approx)";
  modalTaste.textContent = taste || "Wholesome & Healthy";
  modalShelfTip.textContent = `Check the healthy snacks / organic aisle of your nearby kirana store or supermarket for "${name}".`;
  offlineModal.classList.remove("hidden");
}

if (closeModalBtn) {
  closeModalBtn.addEventListener("click", closeModal);
}

window.addEventListener("click", (e) => {
  if (e.target === offlineModal) closeModal();
});

// Close popup with the Escape key
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !offlineModal.classList.contains("hidden")) closeModal();
});

// Event delegation: handles "Offline Store Guide" buttons created dynamically.
// Uses data-attributes instead of inline onclick, so quotes in names can't break anything.
resultContent.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn-offline");
  if (!btn) return;
  openOfflineCard(btn.dataset.name, btn.dataset.price, btn.dataset.taste);
});

// ==========================================
// 4. API Call & Request Building
// ==========================================
analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) {
    alert("Please upload a label picture first!");
    return;
  }

  const intent = document.querySelector('input[name="userIntent"]:checked').value;
  const frontClaim = document.getElementById("frontClaim").value.trim();

  // Extract Diet Goal (Handle Custom)
  let dietGoal = dietGoalDropdown.value;
  if (dietGoal === "Custom") {
    dietGoal = customDietInput.value.trim() || "General Health";
  }

  // Extract Health Profiles (Handle Custom)
  const selectedProfiles = Array.from(document.querySelectorAll('input[name="healthProfile"]:checked'))
    .map(cb => cb.value);

  if (otherHealthCb.checked && customHealthInput.value.trim()) {
    selectedProfiles.push(customHealthInput.value.trim());
  }
  const profilesString = selectedProfiles.join(", ");

  const formData = new FormData();
  formData.append("image", selectedFile); // 'files' ko wapas 'image' kar diya
  formData.append("health_profiles", profilesString);
  formData.append("front_claim", frontClaim);
  formData.append("diet_goal", dietGoal);
  formData.append("intent", intent);

  // UI: loading state (button disabled so double-click can't send two requests)
  analyzeBtn.disabled = true;
  analyzeBtn.style.opacity = "0.6";
  analyzeBtn.style.cursor = "not-allowed";
  setLoaderText(DEFAULT_LOADER_TEXT);
  loader.classList.remove("hidden");
  emptyState.classList.add("hidden");
  resultContent.classList.add("hidden");

  // Message if the free server is waking up
  const slowTimer = setTimeout(() => {
    setLoaderText("Server is waking up, this can take up to a minute on the first request. Please wait...");
  }, SLOW_NOTICE_MS);

  // Timeout so the app never hangs forever
  const controller = new AbortController();
  const abortTimer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE_URL}/api/audit`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (!res.ok) {
      let message = `Audit failed (status ${res.status})`;
      try {
        const err = await res.json();
        if (err && err.detail) {
          message = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        }
      } catch (_) {
        // Response was not JSON, keep the default message
      }
      throw new Error(message);
    }

    const data = await res.json();
    renderOutput(data);
  } catch (err) {
    emptyState.classList.remove("hidden");
    if (err.name === "AbortError") {
      alert("The server took too long to respond. Please try again in a moment.");
    } else {
      alert(`Error: ${err.message}`);
    }
  } finally {
    clearTimeout(slowTimer);
    clearTimeout(abortTimer);
    loader.classList.add("hidden");
    setLoaderText(DEFAULT_LOADER_TEXT);
    analyzeBtn.disabled = false;
    analyzeBtn.style.opacity = "";
    analyzeBtn.style.cursor = "";
  }
});

// ==========================================
// 5. Output Rendering Engine
// ==========================================
function renderOutput(data) {
  resultContent.innerHTML = "";
  data = data || {};

  const isPrePurchase = data.current_intent === "pre_purchase";
  const intentMode = isPrePurchase ? "🛒 Market Decision Mode" : "🏠 Zero-Waste Pantry Rescue";
  const productName = data.product_name || "Unknown Product";

  // Top Title & Deception Score
  const headerHtml = `
    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.8rem; margin-bottom: 1rem;">
      <div>
        <span style="font-size:0.75rem; text-transform:uppercase; color:#94a3b8;">${esc(intentMode)}</span>
        <h3 style="margin:0.2rem 0; font-size:1.3rem; color:#fff;">${esc(productName)}</h3>
      </div>
      <span class="swap-badge" style="background:#ef4444; color:#fff;">Deception: ${esc(data.deception_score || "Detected")}</span>
    </div>
  `;

  // Sugar & Salt Conversions
  const metrics = data.sugar_salt_metrics || {};
  const metricsHtml = `
    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:0.6rem; margin-bottom:1rem;">
      <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); padding:0.6rem; border-radius:8px; text-align:center;">
        <div style="font-size:1.1rem; font-weight:700; color:#f87171;">🥄 ~${num(metrics.teaspoons_of_sugar_per_pack, 0)} Spoons</div>
        <div style="font-size:0.75rem; color:#cbd5e1;">Sugar Equivalent</div>
      </div>
      <div style="background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); padding:0.6rem; border-radius:8px; text-align:center;">
        <div style="font-size:1.1rem; font-weight:700; color:#fbbf24;">🧂 ${num(metrics.daily_sodium_percentage, 0)}%</div>
        <div style="font-size:0.75rem; color:#cbd5e1;">Daily Sodium Quota</div>
      </div>
    </div>
  `;

  // Jargon Buster
  let jargonList = "";
  if (Array.isArray(data.plain_language_breakdown) && data.plain_language_breakdown.length > 0) {
    jargonList = data.plain_language_breakdown.map(item => `
      <div class="jargon-card">
        <span class="tech-term">🔬 ${esc(item.technical_term)}</span>
        <p class="plain-meaning"><strong>Actual Reality:</strong> ${esc(item.what_it_actually_is)}</p>
        <p class="plain-meaning" style="color:#94a3b8; font-size:0.85rem; margin-top:0.2rem;"><em>Impact:</em> ${esc(item.health_concern)}</p>
      </div>
    `).join("");
  }

  // Buying vs Pantry Advice Context
  let contextualHtml = "";
  if (isPrePurchase) {
    contextualHtml = `
      <div class="rescue-box" style="border-color:#10b981; background:rgba(16,185,129,0.08);">
        <h4 style="color:#34d399;">🛒 Should You Buy This?</h4>
        <p style="margin:0.2rem 0; font-size:0.9rem;"><strong>Verdict:</strong> ${esc(data.buying_advice?.is_worth_buying || "THINK TWICE")}</p>
        <p style="margin:0.2rem 0; font-size:0.88rem; color:#cbd5e1;">${esc(data.buying_advice?.verdict_summary || "")}</p>
        <p style="margin:0.4rem 0 0 0; font-size:0.85rem; color:#a7f3d0;"><strong>Goal Impact:</strong> ${esc(data.buying_advice?.diet_goal_compatibility || "")}</p>
      </div>
    `;
  } else {
    contextualHtml = `
      <div class="rescue-box">
        <h4>🏠 Zero-Waste Pantry Rescue</h4>
        <p style="margin:0.2rem 0; font-size:0.88rem;"><strong>Safe Portion:</strong> ${esc(data.zero_waste_hack?.safe_portion || "Consume in strict moderation")}</p>
        <p style="margin:0.2rem 0; font-size:0.88rem;"><strong>Eat It With:</strong> ${esc(data.zero_waste_hack?.damage_control_pairing || "Pair with fiber/protein to reduce glucose spike")}</p>
        <p style="margin:0.4rem 0 0 0; font-size:0.85rem; color:#93c5fd;"><strong>Household Guidance:</strong> ${esc(data.zero_waste_hack?.family_guidance || "Not recommended for kids or diabetics")}</p>
      </div>
    `;
  }

  // ==========================================
  // Optimal Product Match OR Alternative Swaps
  // ==========================================
  let swapsHtml = "";

  if (data.is_product_optimal) {
    const blinkitUrl = `https://blinkit.com/s/?q=${encodeURIComponent(productName)}`;
    const zeptoUrl = `https://www.zeptonow.com/search?q=${encodeURIComponent(productName)}`;

    swapsHtml = `
      <div style="margin-top:1.2rem; background:rgba(16,185,129,0.1); border:1px solid #10b981; border-radius:10px; padding:1.2rem;">
        <h4 style="margin:0 0 0.5rem 0; color:#34d399;">🏆 Great Choice! This Product is Optimal</h4>
        <p style="margin:0.2rem 0; font-size:0.9rem; color:#e2e8f0;">This product perfectly aligns with your health profiles and diet goals. No alternative needed. Check live prices below:</p>

        <div class="swap-actions" style="margin-top:1rem;">
          <a href="${esc(blinkitUrl)}" target="_blank" rel="noopener noreferrer" class="btn-action btn-blinkit">
            ⚡ Buy on Blinkit
          </a>
          <a href="${esc(zeptoUrl)}" target="_blank" rel="noopener noreferrer" class="btn-action btn-zepto">
            ⚡ Buy on Zepto
          </a>
        </div>
      </div>
    `;
  }
  else if (Array.isArray(data.smart_swaps) && data.smart_swaps.length > 0) {
    const swapCards = data.smart_swaps.map(item => {
      const name = item.name || "Healthy Alternative";
      const blinkitUrl = `https://blinkit.com/s/?q=${encodeURIComponent(name)}`;
      const zeptoUrl = `https://www.zeptonow.com/search?q=${encodeURIComponent(name)}`;

      return `
        <div class="swap-card">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="swap-badge">⭐ ${num(item.match_rating, 0, 0, 100)}% ML Match</span>
            <span style="font-size:0.8rem; color:#94a3b8;">${esc(item.approx_price || "")}</span>
          </div>
          <h4 style="margin:0.2rem 0; color:#fff;">${esc(name)}</h4>
          <p style="margin:0.2rem 0; font-size:0.8rem; color:#a7f3d0;"><strong>Taste:</strong> ${esc(item.taste_profile || "")}</p>
          <p style="margin:0.3rem 0 0 0; font-size:0.85rem; color:#e2e8f0;">${esc(item.why || "")}</p>

          <div class="swap-actions">
            <button type="button" class="btn-action btn-offline"
              data-name="${esc(name)}"
              data-price="${esc(item.approx_price || "")}"
              data-taste="${esc(item.taste_profile || "")}">
              🏪 Offline Store Guide
            </button>
            <a href="${esc(blinkitUrl)}" target="_blank" rel="noopener noreferrer" class="btn-action btn-blinkit">
              ⚡ Blinkit
            </a>
            <a href="${esc(zeptoUrl)}" target="_blank" rel="noopener noreferrer" class="btn-action btn-zepto">
              ⚡ Zepto
            </a>
          </div>
        </div>
      `;
    }).join("");

    swapsHtml = `
      <div style="margin-top:1.2rem;">
        <h4 style="margin:0 0 0.5rem 0; color:#34d399;">🌱 Recommended Clean Swaps</h4>
        ${swapCards}
      </div>
    `;
  }

  // Combine everything and display
  resultContent.innerHTML = headerHtml + metricsHtml + jargonList + contextualHtml + swapsHtml;
  resultContent.classList.remove("hidden");
}