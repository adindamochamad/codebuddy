"""CodeBuddy — Gradio Frontend.

Design system:
- Palette  : Deep Navy (#0F172A) + Electric Indigo (#6366F1) + Emerald (#10B981)
- Layout   : Max 1280px, 2-column symmetric grid, 24px gap, card-first
- Type     : Inter/system-ui, clear size scale (12/14/16/20/24/32)
- Spacing  : 4px base unit (4/8/12/16/20/24/32/48)
- Effects  : Subtle glassmorphism, micro-shadow, smooth transitions
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import gradio as gr
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

# Import demo data
from demo_data import (
    DEMO_OCR, DEMO_TUTOR, DEMO_VOICE, DEMO_EXERCISE, DEMO_STUDENT,
    CODE_EXAMPLES, ONBOARDING_MESSAGES, DEMO_BUTTON_LABEL, DEMO_INFO_MESSAGE,
    get_demo_image_path
)

_API     = os.getenv("CODEBUDDY_API", "http://localhost:8000")
_TIMEOUT = 180.0

LANGUAGE_OPTIONS = {
    "Indonesian": "id",
    "Javanese": "jw",
    "Sundanese": "su",
    "Minangkabau": "min",
    "Batak Toba": "bbc",
}

# ============================================================================ #
# CSS                                                                          #
# ============================================================================ #

def dapatkan_css_gradi() -> str:
    """Gabungkan CSS dasar + stamp waktu file agar browser tidak pakai cache lama setelah restart."""
    cap_stempel = Path(__file__).stat().st_mtime
    return f"{BASE_CSS}\n/* codebuddy-ui-stempel:{cap_stempel} */\n"


BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Colorful Enterprise Tokens ──────────────────────────────────────────── */
:root {
  --c-bg:          #F0F4F8; /* Brighter, cooler background */
  --c-surface:     #FFFFFF; /* White cards */
  --c-surface2:    #F8FAFC; /* Secondary bg */
  --c-border:      #E2E8F0; /* Soft border */
  --c-border2:     #CBD5E1;
  --c-border-hover:#8B5CF6; /* Vibrant hover border */

  --c-navy:        #0F172A; /* Deep dark blue for headers */
  --c-indigo:      #8B5CF6; /* Vibrant Violet/Indigo primary */
  --c-indigo-dark: #7C3AED;
  --c-indigo-pale: #EDE9FE;
  --c-indigo-glow: rgba(139, 92, 246, 0.25);
  
  --c-emerald:     #10B981; /* Fresh Emerald success */
  --c-emerald-pale:#D1FAE5;
  --c-rose:        #F43F5E; /* Bright Rose danger */
  --c-rose-pale:   #FFE4E6;
  --c-amber:       #F59E0B; /* Golden Amber warning */
  --c-sky:         #0EA5E9; /* Sky Blue accent */

  --c-text:        #1E293B; /* Crisp dark slate text */
  --c-text-2:      #475569; /* Muted slate */
  --c-text-3:      #94A3B8; /* Light slate */

  /* Metronic border radii (Professional style) */
  --r-sm:  0.475rem;
  --r-md:  0.475rem;
  --r-lg:  0.625rem;
  --r-xl:  0.75rem;
  --r-2xl: 1rem;

  /* Diffuse, soft shadows (Metronic style) */
  --s-sm:  0px 0px 20px 0px rgba(76, 87, 125, 0.02);
  --s-md:  0px 0px 20px 0px rgba(76, 87, 125, 0.02);
  --s-lg:  0px 0px 20px 0px rgba(76, 87, 125, 0.05);
  --s-glow: 0 0 20px var(--c-indigo-glow);

  --grad-hero:    #181C32; /* Solid dark blue/black header */
  --font:         'Inter', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', monospace;
}

/* ── Base ────────────────────────────────────────────────────────────────── */
body, .gradio-container {
  background: var(--c-bg) !important;
  font-family: var(--font) !important;
  color: var(--c-text) !important;
}
.gradio-container {
  max-width: 1280px !important;
  margin: 0 auto !important;
  padding: 0 24px 64px !important;
}

/* Remove default Gradio outlines from layout containers */
.contain, .wrap, .panel { background: transparent !important; border: none !important; box-shadow: none !important; }

/* ── Premium Typography ──────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
  letter-spacing: -0.02em !important;
}
.gradio-container label, .cb-lbl {
  font-family: var(--font) !important;
  font-weight: 700 !important;
  font-size: 1rem !important;
  color: var(--c-text) !important;
  letter-spacing: -0.01em !important;
  text-transform: none !important;
}

/* ── Hero Component (Colorful Modern SaaS Style) ──────────────────────── */
.cb-hero {
  background: linear-gradient(135deg, var(--c-indigo) 0%, #3B82F6 100%);
  border-radius: var(--r-sm);
  padding: 40px 48px;
  margin-top: 30px;
  margin-bottom: 30px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--s-md);
  border: none;
}
.cb-hero::before {
  content: '';
  position: absolute; inset: 0;
  background:
    radial-gradient(circle at 90% 10%, rgba(255,255,255,0.15) 0%, transparent 40%),
    radial-gradient(circle at 10% 90%, rgba(255,255,255,0.1) 0%, transparent 40%);
  pointer-events: none;
}
.cb-hero-inner { position: relative; z-index: 1; display: flex; flex-direction: column; }
.cb-hero-top { display: flex; align-items: center; gap: 20px; margin-bottom: 24px; }
.cb-hero-logo {
  width: 64px; height: 64px; border-radius: 12px; flex-shrink: 0;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  display: flex; align-items: center; justify-content: center;
  font-size: 32px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  backdrop-filter: blur(8px);
}
.cb-hero-brand h1 {
  font-size: 2rem; font-weight: 800; color: #FFFFFF;
  letter-spacing: -0.02em; margin: 0; line-height: 1.2;
}
.cb-hero-brand p {
  font-size: 1.1rem; color: rgba(255,255,255,0.9);
  margin: 4px 0 0; font-weight: 500;
}
.cb-hero-badges { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 32px; }
.cb-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 6px;
  font-size: 0.8rem; font-weight: 600;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.2);
  color: #FFFFFF;
  backdrop-filter: blur(8px);
}
.cb-hero-features { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.cb-feat {
  background: rgba(255,255,255,0.1);
  border: 1px dashed rgba(255,255,255,0.2);
  border-radius: var(--r-sm);
  padding: 20px;
  transition: all 0.3s ease;
  backdrop-filter: blur(4px);
}
.cb-feat:hover { 
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.2);
  transform: translateY(-2px);
}
.cb-feat-icon  { font-size: 1.5rem; margin-bottom: 12px; display: block; }
.cb-feat-title { font-size: 0.95rem; font-weight: 600; color: #FFFFFF; margin: 0 0 4px; }
.cb-feat-desc  { font-size: 0.8rem; color: rgba(255,255,255,0.8); margin: 0; line-height: 1.5; }

/* ── Tab Navigation (Metronic Nav-Line Style) ────────────────────────────────────── */
.tabs { background: transparent !important; }
.tab-nav {
  background: transparent !important;
  border-bottom: 1px solid var(--c-border) !important;
  padding: 0 !important;
  box-shadow: none !important;
  margin-bottom: 30px !important;
  gap: 20px !important; overflow-x: auto !important;
  display: flex !important;
  border-radius: 0 !important;
}
.tab-nav button {
  border-radius: 0 !important;
  font-weight: 500 !important; font-size: 0.95rem !important;
  padding: 12px 0 12px 0 !important; color: var(--c-text-3) !important;
  transition: all 0.2s ease !important; border: none !important;
  font-family: var(--font) !important;
  border-bottom: 2px solid transparent !important;
  background: transparent !important;
}
.tab-nav button.selected {
  background: transparent !important;
  color: var(--c-indigo) !important;
  font-weight: 600 !important;
  border-bottom: 2px solid var(--c-indigo) !important;
}
.tab-nav button:hover:not(.selected) {
  background: transparent !important; color: var(--c-indigo) !important;
}

/* ── Premium Bento Card Layout ───────────────────────────────────────────── */
/* Helper for 2-column symmetry */
.cb-split {
  display: grid !important;
  grid-template-columns: 1fr 1fr !important;
  gap: 20px !important;
  align-items: stretch !important; /* Force equal height */
  overflow: visible !important; /* Fix dropdown scroll bug */
}

/* The core Bento Cell (Card) */
.cb-card-col {
  background: var(--c-surface) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r-sm) !important;
  box-shadow: var(--s-sm) !important;
  padding: 30px !important; /* Generous padding */
  display: flex !important;
  flex-direction: column !important;
  gap: 20px !important;
  height: auto !important; /* Let flex stretch it */
  overflow: visible !important; /* Fix dropdown scroll bug */
  z-index: 1; /* Keep dropdowns above siblings */
}
.cb-card-col:hover {
  z-index: 10; /* Elevate card on hover to keep dropdowns on top */
}

/* Nuke Gradio's internal borders inside our beautiful cards */
.cb-card-col > .form, 
.cb-card-col > .block,
.cb-card-col fieldset {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
  margin: 0 !important;
  padding: 0 !important;
  gap: 16px !important;
}

/* Inner form elements in cards — sedikit depth */
.cb-card-col input[type="text"],
.cb-card-col input[type="number"],
.cb-card-col textarea,
.cb-card-col select,
.cb-card-col .gradio-dropdown {
  box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
}

/* Pustaka Latihan: card + field lebih tegas dari polos */
.cb-pustaka-latihan {
  box-shadow: 0 6px 28px rgba(76, 87, 125, 0.14) !important;
  border-color: rgba(139, 92, 246, 0.22) !important;
}
.cb-pustaka-latihan input[type="text"],
.cb-pustaka-latihan textarea,
.cb-pustaka-latihan .gradio-dropdown {
  box-shadow: 0 2px 8px rgba(76, 87, 125, 0.1) !important;
}

/* ── Premium Inputs & Controls ───────────────────────────────────────────── */
input[type="text"], input[type="number"], textarea, select {
  background: var(--c-surface2) !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r-sm) !important;
  font-family: var(--font) !important; 
  font-size: 0.95rem !important;
  font-weight: 500 !important;
  padding: 12px 16px !important;
  color: var(--c-text) !important;
  transition: all 0.2s ease !important;
}
input[type="text"]:focus, textarea:focus, select:focus {
  background: var(--c-surface) !important;
  border-color: var(--c-border-hover) !important;
  box-shadow: 0 0 0 3px var(--c-indigo-glow) !important;
  outline: none !important;
}

/* Fix Dropdown styling that was broken */
.gradio-dropdown {
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r-sm) !important;
  background: var(--c-surface2) !important;
  transition: all 0.2s ease !important;
}
.gradio-dropdown:focus-within {
  background: var(--c-surface) !important;
  border-color: var(--c-border-hover) !important;
  box-shadow: 0 0 0 3px var(--c-indigo-glow) !important;
}

/* Radio Suara (TTS) — Gradio 5 pakai struktur berbeda; target lewat elem_classes */
.cb-tts-suara .wrap,
.cb-tts-suara [data-testid="radio-group"],
.cb-tts-suara fieldset {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 10px !important;
  align-items: center !important;
  border: none !important;
  margin: 0 !important;
  padding: 0 !important;
}
.cb-tts-suara label {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 10px 18px !important;
  margin: 0 !important;
  border: 1px solid var(--c-border) !important;
  border-radius: var(--r-sm) !important;
  background: var(--c-surface2) !important;
  cursor: pointer !important;
  font-weight: 500 !important;
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease !important;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}
.cb-tts-suara label:hover {
  border-color: var(--c-border-hover) !important;
  background: var(--c-surface) !important;
}
.cb-tts-suara label:has(input[type="radio"]:checked) {
  border-color: var(--c-indigo) !important;
  background: var(--c-indigo-pale) !important;
  color: var(--c-indigo) !important;
  font-weight: 600 !important;
  box-shadow: 0 0 0 2px var(--c-indigo-glow) !important;
}
.cb-tts-suara input[type="radio"] {
  accent-color: var(--c-indigo) !important;
  width: 1.05rem !important;
  height: 1.05rem !important;
}

/* Code Editor overrides */
.cm-editor {
  border-radius: var(--r-sm) !important;
  border: 1px solid var(--c-border) !important;
  box-shadow: none !important;
  overflow: hidden !important;
  font-family: var(--font-mono) !important;
  font-size: 0.85rem !important;
}

/* ── Premium Buttons ─────────────────────────────────────────────────────── */
button.lg, button.primary {
  background: var(--c-indigo) !important;
  color: #fff !important; 
  border: none !important;
  border-radius: var(--r-sm) !important;
  padding: 12px 24px !important;
  font-weight: 600 !important; 
  font-size: 0.95rem !important;
  box-shadow: none !important;
  transition: all 0.2s ease !important;
  min-height: 48px !important; 
  font-family: var(--font) !important; 
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
}
button.lg:hover, button.primary:hover {
  background: var(--c-indigo-dark) !important;
}
button.lg:active, button.primary:active { 
  transform: translateY(1px) !important; 
}

/* ── Modern Alerts & Intros ──────────────────────────────────────────────── */
.cb-intro {
  background: var(--c-indigo-pale); 
  border: 1px dashed var(--c-indigo);
  border-radius: var(--r-sm);
  padding: 16px 24px; 
  margin-bottom: 24px;
  font-size: 0.95rem; font-weight: 500; color: var(--c-text-2);
  display: flex; align-items: center; gap: 16px; line-height: 1.5;
}
.cb-intro span { font-size: 1.5rem; }
.cb-intro strong { color: var(--c-indigo); font-weight: 600; }

.cb-alert {
  display: flex; align-items: flex-start; gap: 16px;
  border-radius: var(--r-sm); padding: 16px 20px;
  font-size: 0.95rem; font-weight: 500; line-height: 1.5; margin: 12px 0;
  border: 1px dashed transparent;
}
.cb-alert-icon { font-size: 1.25rem; flex-shrink: 0; margin-top: 2px; }
.cb-a-success { background: var(--c-emerald-pale); border-color: var(--c-emerald); color: var(--c-text-2); }
.cb-a-error   { background: var(--c-rose-pale); border-color: var(--c-rose); color: var(--c-text-2); }
.cb-a-warning { background: var(--c-surface2); border-color: var(--c-amber); color: var(--c-text-2); }
.cb-a-info    { background: var(--c-surface2); border-color: var(--c-border2); color: var(--c-text-2); }

/* ── Upload Area (Refined) ───────────────────────────────────────────────── */
.upload-area {
  border: 1px dashed var(--c-border2) !important;
  border-radius: var(--r-sm) !important;
  background: var(--c-surface2) !important;
  transition: all 0.3s ease !important;
  min-height: 240px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.upload-area:hover { 
  border-color: var(--c-indigo) !important; 
  background: var(--c-indigo-pale) !important;
}

/* ── Stats & Dashboards ──────────────────────────────────────────────────── */
.cb-stat-grid {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px;
}
.cb-stat {
  border-radius: var(--r-sm);
  padding: 24px 20px;
  text-align: center; position: relative; overflow: hidden;
  box-shadow: var(--s-sm);
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  transition: all 0.3s ease;
}
.cb-stat:hover {
  transform: translateY(-2px);
  border-color: var(--c-border-hover);
  box-shadow: var(--s-md);
}
.cb-stat::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
  background: linear-gradient(90deg, var(--c-indigo), var(--c-sky));
}
.cb-stat-val {
  font-size: 2.5rem; font-weight: 800;
  line-height: 1; letter-spacing: -0.02em; margin-bottom: 8px;
  color: #8B5CF6;
}
.cb-stat-lbl {
  font-size: 0.8rem; font-weight: 600; color: #94A3B8;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.cb-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 0.625rem;
  padding: 20px;
  box-shadow: 0px 0px 20px 0px rgba(76,87,125,0.05);
}

/* ── Mobile Responsive Overrides ─────────────────────────────────────────── */
@media (max-width: 768px) {
  .cb-split {
    grid-template-columns: 1fr !important;
  }
  .cb-hero {
    padding: 24px 20px !important;
  }
  .cb-hero-brand h1 { font-size: 1.8rem !important; }
  .cb-stat-grid, .cb-hero-features {
    grid-template-columns: 1fr 1fr !important;
  }
  .cb-card-col { padding: 20px !important; }
}

/* ── Custom UI Blocks (Metronic Style) ───────────────────────────────────── */
.cb-ex {
  background: var(--c-surface);
  border: 1px dashed var(--c-border);
  border-radius: var(--r-sm);
  padding: 20px; 
  margin-bottom: 16px; 
  transition: all 0.3s ease;
}
.cb-ex:hover {
  border-color: var(--c-border-hover);
  background: var(--c-surface2);
}
.cb-lp {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.cb-lp-b { background: var(--c-indigo-pale); color: var(--c-indigo); }
.cb-lp-i { background: var(--c-surface2); color: var(--c-amber); }
.cb-lp-a { background: var(--c-rose-pale); color: var(--c-rose); }
.cb-code-preview {
  background: #181C32;
  color: #A1A5B7;
  padding: 16px;
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: 0.85rem;
  overflow-x: auto;
  border: 1px solid #2B2B40;
}

/* ── Simple Footer ───────────────────────────────────────────────────────── */
.cb-footer {
  text-align: center; 
  padding: 32px 24px;
  background: var(--c-surface);
  color: var(--c-text-2);
  font-size: 0.9rem;
  border-top: 1px solid var(--c-border);
  margin-top: 48px; 
  line-height: 1.6;
}
.cb-footer strong { color: var(--c-text); font-weight: 600; }
.cb-footer-links {
  display: flex; justify-content: center; gap: 16px; margin-top: 16px;
}
.cb-footer-link {
  font-size: 0.85rem; font-weight: 500; color: var(--c-text-2);
  text-decoration: none; padding: 8px 16px;
  border-radius: var(--r-sm);
  transition: all 0.2s ease;
  background: var(--c-surface2);
  border: 1px solid var(--c-border);
}
.cb-footer-link:hover {
  color: var(--c-indigo);
  border-color: var(--c-indigo);
  background: var(--c-indigo-pale);
}

/* Utility Animations */
@keyframes cb-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
@keyframes cb-dot-pulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
.cb-mascot { animation: cb-bounce 2s ease-in-out infinite; font-size: 3rem; }
.cb-success-animation { animation: cb-slide-in 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes cb-slide-in {
  from { opacity: 0; transform: translateY(-10px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
"""

FORCE_LIGHT_JS = """
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<script>
(function(){
  var u=new URL(window.location.href);
  if(u.searchParams.get('__theme')!=='light'){
    u.searchParams.set('__theme','light');
    window.location.replace(u.toString());
  }
})();

// Audio feedback untuk interaksi (dapat di-mute oleh user)
const CodeBuddyAudio = {
  enabled: localStorage.getItem('cb-audio-enabled') !== 'false',
  
  sounds: {
    click: 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBCx+zPLTgTYHGGS57OefTBAMT6Xh8LZjHAY4kNfyzXksBCR2x/DdkUAKFF607+inVRQKRp/g8r9sIQQsfsry04I2Bxhluuvnn0wQDE+l4fC2YxwGOI/W8s15LAQkdsfw3ZFACRVetezoqFUUCkaf4PK/bCEELH7K8tOCNgcYZbnr559MEAxPpeHwtmMcBjiP1vLNeSUEJHXH8N2RQAkVXrTs6KdWFApGnt/yv24gBCx9yfLUgjUHGGS56+efSxAMT6Tg8LdjGwY4jtbyzXokBCR0x+/dkj8JFVyz6+inVBMKRp3e8sBuHwQrfMjy1II0Bxhit+vnnkoQDFCj3++4YxoGN4zV8s16IwQkc8fv3ZI/CRRbs+romFQTCkWc3PLBYB4EK3vH8tSCMwcZYrfq56BLDwxQo9/wuGIZBjmM1vLNeSMEJXHG792SPQoUWrLp55lUEgpFnNvywWAdBCt6x/LUgTIHGGG36OegSwwMUKHe77hjGAY5jNXxy3omBCVwxu7ekT4JFFqx6OiZVRIJRZzb8sFfHAQrf8by1H8yBxlhtObnnUgLDFCg3e+4YxgGOYrU8ct6JQQkcMbt3ZI+CRNZr+fnmlYRCUSa2vK/XhoELH3E8tOBMQcZYbPl55xHCgxQn93uuGMXBzqJ0/HLeSQEI27F7d2ROwkUWa7m55tVEQlEmdnxwF4ZBSx9w/HTgDAHGWCy5Oec/rBi',
    success: 'data:audio/wav;base64,UklGRhIFAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0Ya4EAACBk6Ckn5+jqaiclJGSlZienJ2dmqCdmpWUmJmZmp+eoKGhlpujpaago5+enp+fo6iom5SSlJWYnZ+fnJ2gnZ2dnKCfnZ6enJ2enJ2fnZ+foKChoqKipKWmpqanqKmpqqqqq6urq6usrKysra6ur7CxsrK0tbW2t7m6u7y9vr/AwcLDxMXGx8nKy8zNzs/R0tPU1dbX2Nna3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/AAAAAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7//wD/fv18+/r5+Pf29fTz8vHw7+7t7Ovq6ejn5uXk4+Lh4N/e3dzb2tnY19bV1NPSz87NzMrJyMbFxMPCwL++vbu6ubm3trW0s7KxsK+urayrqqinpqWko6KhoJ+enZybmpqYl5aVlJOSkY+OjoyLioqJh4aFhIOCgIB/fn59fHt6enl5eHh3d3Z2dnZ2dnZ2d3d3eHh5eXp6e3x9fn+AgYKDhIWGh4iJiouMjY6PkJGSk5SVlpeYmZqbnJ2en6ChoqOkpaanqKmqq6ytr6+wsrO0tra3uLm6vL2+v8DBwsPFxsfIycvMzc7P0NHS09TV1tfY2drb3d3e3+Dh4eLj5OXm5+jp6evs7e7v8PHy8/T19vf4+fr7/P3+/w==',
    error: 'data:audio/wav;base64,UklGRhIFAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0Ya4EAAD/AP8A/wD/AP8A/gD+AP4A/gD+AP4A/QD9AP0A/QD9AP0A/AD8APwA/AD8APwA+wD7APsA+wD7APsA+gD6APoA+gD6APoA+QD5APkA+QD5APkA+AD4APgA+AD4APgA9wD3APcA9wD3APcA9gD2APYA9gD2APYA9QD1APUA9QD1APUA9AD0APQA9AD0APQA8wDzAPMA8wDzAPMA8gDyAPIA8gDyAPIA8QDxAPEA8QDxAPEA8ADwAPAA8ADwAPAA7wDvAO8A7wDvAO8A7gDuAO4A7gDuAO4A7QDtAO0A7QDtAO0A7ADsAOwA7ADsAOwA6wDrAOsA6wDrAOsA6gDqAOoA6gDqAOoA6QDpAOkA6QDpAOkA6ADo',
    achievement: 'data:audio/wav;base64,UklGRhIFAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0Ya4EAACJ0/TTrJGOnKCgn56dnJ2en6ChoqOkpaanqKmqq6ytr7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/AAAAAQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyAhIiMkJSYnKCkqKywtLi8wMTIzNDU2Nzg5Ojs8PT4/QEFCQ0RFRkdISUpLTE1OT1BRUlNUVVZXWFlaW1xdXl9gYWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXp7fH1+f4CBgoOEhYaHiImKi4yNjo+QkZKTlJWWl5iZmpucnZ6foKGio6SlpqeoqaqrrK2ur7CxsrO0tba3uLm6u7y9vr/AwcLDxMXGx8jJysvMzc7P0NHS09TV1tfY2drb3N3e3+Dh4uPk5ebn6Onq6+zt7u/w8fLz9PX29/j5+vv8/f7/'
  },

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem('cb-audio-enabled', this.enabled);
  },

  play(soundName) {
    if (!this.enabled || !this.sounds[soundName]) return;
    try {
      const audio = new Audio(this.sounds[soundName]);
      audio.volume = 0.3;
      audio.play().catch(() => {}); // Ignore autoplay policy errors
    } catch(e) {}
  }
};

// Tambahkan audio pada button clicks
document.addEventListener('DOMContentLoaded', function() {
  // Audio untuk semua buttons
  document.addEventListener('click', function(e) {
    if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
      CodeBuddyAudio.play('click');
    }
  });
  
  // Deteksi success/error alerts dan play corresponding sound
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.nodeType === 1 && node.classList) {
          if (node.classList.contains('cb-a-success') || node.querySelector('.cb-a-success')) {
            CodeBuddyAudio.play('success');
          } else if (node.classList.contains('cb-a-error') || node.querySelector('.cb-a-error')) {
            CodeBuddyAudio.play('error');
          }
        }
      });
    });
  });
  
  // Observe body untuk deteksi alert baru
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
});
</script>
"""

# ============================================================================ #
# API helpers                                                                  #
# ============================================================================ #

async def _post(ep, **kw):
    async with httpx.AsyncClient(base_url=_API, timeout=_TIMEOUT) as c:
        r = await c.post(ep, **kw); r.raise_for_status(); return r.json()

async def _post_raw(ep, **kw):
    async with httpx.AsyncClient(base_url=_API, timeout=_TIMEOUT) as c:
        r = await c.post(ep, **kw); r.raise_for_status()
        return r.content, dict(r.headers)

async def _get(ep, **kw):
    async with httpx.AsyncClient(base_url=_API, timeout=_TIMEOUT) as c:
        r = await c.get(ep, **kw); r.raise_for_status(); return r.json()

def run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio; nest_asyncio.apply()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

def lang_code(label: str) -> str:
    return LANGUAGE_OPTIONS.get(label, "id")

def alert(kind: str, msg: str) -> str:
    icons = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "💡"}
    cls   = {"success": "cb-a-success", "error": "cb-a-error",
             "warning": "cb-a-warning", "info": "cb-a-info"}.get(kind, "cb-a-info")
    
    # Tambahkan class untuk success animation
    extra_cls = " cb-success-animation" if kind == "success" else ""
    
    return (
        f'<div class="cb-alert {cls}{extra_cls}">'
        f'<span class="cb-alert-icon{"" if kind != "success" else " cb-success-icon"}">{icons.get(kind,"ℹ️")}</span>'
        f'<div class="cb-alert-body">{msg}</div>'
        f'</div>'
    )

def loading_state(pesan: str = "CodeBot sedang berpikir...") -> str:
    """Generate loading state dengan CodeBot mascot."""
    return (
        f'<div class="cb-loading">'
        f'<div class="cb-mascot-thinking">'
        f'<div class="cb-mascot">🤖</div>'
        f'<div class="cb-loading-dots"><span></span><span></span><span></span></div>'
        f'</div>'
        f'<div class="cb-loading-text">{pesan}</div>'
        f'</div>'
    )

def panel(icon: str, title: str, body: str) -> str:
    """Uniform panel wrapper used in every split-column layout."""
    return (
        f'<div class="cb-panel">'
        f'<div class="cb-panel-head"><span style="font-size:1.1rem">{icon}</span><h3>{title}</h3></div>'
        f'<div class="cb-panel-body">{body}</div>'
        f'</div>'
    )

# ============================================================================ #
# Demo Mode Handlers                                                           #
# ============================================================================ #

def demo_load_ocr():
    """Load demo image untuk OCR tab."""
    demo_img_path = get_demo_image_path()
    if not demo_img_path:
        return None, alert("error", "Demo image tidak ditemukan. Pastikan file ada di folder Test Pic OCR/")
    return demo_img_path, alert("info", DEMO_INFO_MESSAGE)

def demo_load_tutor_error():
    """Load demo code dengan error untuk AI Tutor."""
    return (
        DEMO_TUTOR["code_with_error"],
        DEMO_TUTOR["student_id"],
        DEMO_TUTOR["level"],
        DEMO_TUTOR["exercise_id"],
        alert("info", DEMO_INFO_MESSAGE + " Kode ini punya error yang perlu diperbaiki.")
    )

def demo_load_tutor_success():
    """Load demo code tanpa error untuk AI Tutor."""
    return (
        DEMO_TUTOR["code_success"],
        DEMO_TUTOR["student_id"],
        DEMO_TUTOR["level"],
        DEMO_TUTOR["exercise_id"],
        alert("success", DEMO_INFO_MESSAGE + " Kode ini sudah benar!")
    )

def demo_load_voice_tts():
    """Load demo text untuk TTS."""
    return DEMO_VOICE["tts_text"], DEMO_VOICE["gender"], alert("info", DEMO_INFO_MESSAGE)

def demo_load_exercise():
    """Load demo topic untuk generate exercise."""
    return (
        DEMO_EXERCISE["topic"],
        DEMO_EXERCISE["difficulty"],
        alert("info", DEMO_INFO_MESSAGE + " Klik 'Buat!' untuk generate latihan AI.")
    )

def demo_load_student():
    """Load demo data siswa untuk registrasi."""
    return (
        DEMO_STUDENT["register"]["name"],
        DEMO_STUDENT["register"]["age"],
        DEMO_STUDENT["register"]["level"],
        alert("info", DEMO_INFO_MESSAGE)
    )

def demo_load_progress():
    """Load demo student ID untuk cek progress."""
    return DEMO_STUDENT["progress_student_id"], alert("info", DEMO_INFO_MESSAGE + " Klik 'Lihat Progress' untuk melihat data siswa.")

# ============================================================================ #
# Handlers                                                                     #
# ============================================================================ #

def h_ocr(image):
    if not image:
        return "", alert("info", "Please upload or take a photo of handwritten Python code first.")
    with open(image, "rb") as f:
        raw = f.read()
    try:
        d    = run(_post("/api/ocr/extract", files={"berkas": ("photo.jpg", raw, "image/jpeg")}))
        conf = d.get("confidence", 0)
        pct  = int(conf * 100)
        bar  = (
            f'<div style="margin-top:10px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:0.8rem;'
            f'font-weight:600;margin-bottom:4px;"><span>AI Confidence</span><span>{pct}%</span></div>'
            f'<div class="cb-bar-bg"><div class="cb-bar-fill" style="width:{pct}%"></div></div>'
            f'</div>'
        )
        return d.get("code", ""), alert("success", f"Vision AI successfully extracted the code!{bar}")
    except Exception as e:
        return "", alert("error", f"Failed to process image: {str(e)[:200]}")


def h_tutor(code, sid_str, level, ex_id, lang_label):
    if not code.strip():
        return "", "", "", alert("info", "Please enter your Python code in the editor on the left.")
    bhs = lang_code(lang_label)
    sid = int(sid_str) if sid_str.strip().isdigit() else 1
    try:
        d = run(_post("/api/agent/tutor", json={
            "code": code, "student_id": sid,
            "student_level": level, "exercise_id": ex_id or None, "bahasa": bhs,
        }))
        final    = d.get("final_result", "")
        attempts = d.get("attempts", [])
        exec_out = next((a.get("output", "") for a in attempts if a.get("stage") == "execution"), "")
        fb       = next((a["ai_feedback"] for a in reversed(attempts) if a.get("ai_feedback")), {})

        status_map = {
            "success":       ("success", "🎉 Code ran perfectly — great work!"),
            "syntax_error":  ("error",   "📝 Syntax error found — let's fix it together!"),
            "runtime_error": ("warning", "⚡ Runtime error — check the output for details."),
            "timeout":       ("error",   "⏱️ Code timed out — there may be an infinite loop."),
        }
        t, msg   = status_map.get(final, ("info", final))
        status_h = alert(t, msg)

        md = ""
        if fb.get("encouragement"):
            md += f'<div class="cb-bubble">{fb["encouragement"]}</div>\n\n'
        if fb.get("understanding"):
            md += f"**🧠 About this code:**\n\n{fb['understanding']}\n\n"
        errors = fb.get("errors", [])
        if errors:
            md += "**🔍 Issues found:**\n\n"
            for e in errors:
                ln  = f"Line {e['line']}: " if e.get("line") else ""
                md += f"- 🔴 **{ln}**{e.get('explanation', '')}\n"
                if e.get("fix"):
                    md += f"  - 💡 _{e['fix']}_\n"
            md += "\n"
        sug = fb.get("suggestions", [])
        if sug:
            md += "**✨ Tutor tips:**\n\n" + "".join(f"- {s}\n" for s in sug)

        fixed = fb.get("corrected_code", "") or "# Your code is already correct! 🎉"
        return exec_out or "(no output)", md, fixed, status_h
    except Exception as e:
        return "", "", "", alert("error", f"Request failed: {str(e)[:250]}")


def h_hint(code, err_msg, lvl, lang_label):
    if not code.strip():
        return alert("info", "Please enter your code in the AI Tutor tab first.")
    try:
        d = run(_post("/api/agent/hint", json={
            "code": code, "error": err_msg or "-",
            "hint_level": int(lvl), "student_level": "beginner",
        }))
        hint   = d.get("hint", "")
        labels = {1: ("🌱", "Guiding Question"), 2: ("🔍", "Error Location"), 3: ("🎯", "Full Solution")}
        icon, title = labels.get(int(lvl), ("💡", "Hint"))
        return (
            f'<div class="cb-alert cb-a-info" style="flex-direction:column;gap:10px;">'
            f'<div style="display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:1.2rem;">{icon}</span>'
            f'<strong style="font-size:0.92rem;">Level {int(lvl)} — {title}</strong>'
            f'</div>'
            f'<div style="font-size:0.9rem;line-height:1.7;">{hint}</div>'
            f'</div>'
        )
    except Exception as e:
        return alert("error", f"Request failed: {str(e)[:200]}")


def h_voice_ask(audio_path, lang_label, level):
    """Generator agar Gradio bisa tampil status loading sambil menunggu proses panjang."""
    path_audio = audio_path
    if isinstance(audio_path, dict):
        # Gradio kadang mengirim struktur berisi path file
        path_audio = (
            audio_path.get("path")
            or audio_path.get("name")
            or audio_path.get("file")
        )
    if not path_audio or (isinstance(path_audio, str) and not path_audio.strip()):
        yield None, alert("info", "Rekam pertanyaanmu dulu menggunakan mikrofon, lalu tekan Kirim.")
        return

    bhs = lang_code(lang_label)

    # Tampilkan status loading segera agar UI tidak terasa beku
    yield None, (
        '<div class="cb-loading" style="padding:12px 0;">'
        '<div class="cb-mascot-thinking">'
        '<div class="cb-mascot">🎤</div>'
        '<div class="cb-loading-dots"><span></span><span></span><span></span></div>'
        '</div>'
        '<div class="cb-loading-text">CodeBot sedang mendengarkan &amp; berpikir...<br>'
        '<small style="color:var(--c-text-3);">Whisper STT → Gemma AI → TTS — butuh 15–60 detik</small></div>'
        '</div>'
    )

    try:
        with open(path_audio, "rb") as berkas_suara:
            isi_audio = berkas_suara.read()
        isi_respons, header_respons = run(_post_raw(
            "/api/audio/ask",
            files={"berkas": ("q.wav", isi_audio, "audio/wav")},
            params={"bahasa": bhs, "student_level": level},
        ))
        import tempfile
        path_output = tempfile.mktemp(suffix=".mp3")
        with open(path_output, "wb") as berkas_output:
            berkas_output.write(isi_respons)
        teks_pertanyaan = header_respons.get("x-pertanyaan", "...")
        teks_jawaban    = header_respons.get("x-jawaban", "...")
        info_html = (
            f'<div style="display:flex;flex-direction:column;gap:8px;">'
            f'{alert("info", f"<strong>Pertanyaan kamu:</strong><br>{teks_pertanyaan}")}'
            f'{alert("success", f"<strong>CodeBot menjawab:</strong><br>{teks_jawaban}")}'
            f'</div>'
        )
        yield path_output, info_html
    except httpx.HTTPStatusError as kesalahan_httpx:
        pesan_detail = ""
        try:
            isi_json = kesalahan_httpx.response.json()
            if isinstance(isi_json, dict) and "detail" in isi_json:
                pesan_detail = str(isi_json["detail"])
            else:
                pesan_detail = str(isi_json)
        except Exception:
            pesan_detail = (kesalahan_httpx.response.text or str(kesalahan_httpx))[:400]
        yield None, alert("error", f"Request gagal: {pesan_detail}")
    except Exception as kesalahan_umum:
        yield None, alert("error", f"Request gagal: {str(kesalahan_umum)[:200]}")


def h_tts(text, lang_label, gender):
    if not text.strip():
        return None, alert("info", "Please enter the text you want to be read aloud.")
    try:
        content, _ = run(_post_raw("/api/audio/tts", json={
            "teks": text, "bahasa": lang_code(lang_label), "gender": gender,
        }))
        import tempfile
        out = tempfile.mktemp(suffix=".mp3")
        with open(out, "wb") as f:
            f.write(content)
        return out, alert("success", "Audio ready — press ▶ to play.")
    except Exception as e:
        return None, alert("error", f"TTS failed: {str(e)[:200]}")


def h_exercise_list(diff):
    try:
        params = {} if diff == "All" else {"difficulty": diff.lower()}
        d      = run(_get("/api/exercises/", params=params))
        items  = d.get("latihan", [])
        if not items:
            return alert("info", "No exercises found for this filter.")
        lp = {"beginner": "cb-lp-b", "intermediate": "cb-lp-i", "advanced": "cb-lp-a"}
        html = '<div style="display:flex;flex-direction:column;gap:8px;">'
        for i in items:
            lvl   = i.get("difficulty", "beginner")
            cls   = lp.get(lvl, "cb-lp-b")
            judul = i["judul"]
            desc  = i["ringkas"]
            kode  = i["starter_code"]
            eid   = i["exercise_id"]
            html += (
                f'<div class="cb-ex">'
                f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;">'
                f'<span style="font-weight:800;font-size:0.97rem;color:var(--c-text);">{judul}</span>'
                f'<span class="cb-lp {cls}">{lvl}</span>'
                f'</div>'
                f'<p style="color:var(--c-text-2);margin:0 0 10px;font-size:0.86rem;line-height:1.5;">{desc}</p>'
                f'<pre class="cb-code-preview">{kode}</pre>'
                f'<div style="margin-top:8px;font-size:0.73rem;color:var(--c-text-3);">'
                f'ID: <code style="background:var(--c-surface2);padding:2px 6px;border-radius:4px;">{eid}</code>'
                f'</div>'
                f'</div>'
            )
        return html + '</div>'
    except Exception as e:
        return alert("error", f"Failed to load exercises: {e}")


def h_generate_exercise(topic, diff, lang_label):
    if not topic.strip():
        return "", "", "", alert("info", "Enter an exercise topic first.")
    try:
        d = run(_post("/api/exercises/generate", json={
            "topic": topic, "difficulty": diff.lower(), "bahasa": lang_code(lang_label),
        }))
        if "error" in d:
            return "", "", "", alert("error", "AI failed to generate an exercise. Please try again.")
        title = d.get("title", "")
        return (
            title, d.get("instructions", ""), d.get("starter_code", ""),
            alert("success", f"Exercise <strong>{title}</strong> created successfully!"),
        )
    except Exception as e:
        return "", "", "", alert("error", f"Request failed: {e}")


def h_latihan_cek(kode_siswa, instruksi_latihan, level, lang_label):
    """Jalankan kode latihan dan minta feedback AI — mirip tab AI Tutor."""
    if not kode_siswa.strip():
        return "", "", alert("warning", "Tulis atau edit kode di editor dulu, baru tekan Jalankan & Cek.")
    bhs = lang_code(lang_label)
    try:
        hasil_tutor = run(_post("/api/agent/tutor", json={
            "code": kode_siswa,
            "student_id": 1,
            "student_level": level,
            "exercise_id": None,
            "bahasa": bhs,
            # Sertakan instruksi latihan sebagai konteks tambahan agar AI tahu
            # tujuan latihan saat memberikan feedback
            "context": instruksi_latihan or "",
        }))
        status_akhir = hasil_tutor.get("final_result", "")
        daftar_percobaan = hasil_tutor.get("attempts", [])

        # Ambil output eksekusi
        keluaran_kode = next(
            (p.get("output", "") for p in daftar_percobaan if p.get("stage") == "execution"),
            "",
        )
        # Ambil feedback AI dari percobaan terakhir yang punya feedback
        umpan_balik = next(
            (p["ai_feedback"] for p in reversed(daftar_percobaan) if p.get("ai_feedback")),
            {},
        )

        peta_status = {
            "success":       ("success", "Kode berhasil dijalankan dengan benar!"),
            "syntax_error":  ("error",   "Ada kesalahan sintaks — yuk perbaiki bersama!"),
            "runtime_error": ("warning", "Ada error saat dijalankan — cek output di bawah."),
            "timeout":       ("error",   "Kode berjalan terlalu lama — mungkin ada loop tak berujung."),
        }
        tipe_alert, pesan_alert = peta_status.get(status_akhir, ("info", status_akhir))
        html_status = alert(tipe_alert, pesan_alert)

        # Susun markdown feedback
        teks_feedback = ""
        if umpan_balik.get("encouragement"):
            teks_feedback += f'<div class="cb-bubble">{umpan_balik["encouragement"]}</div>\n\n'
        if umpan_balik.get("understanding"):
            teks_feedback += f"**Penjelasan kode:**\n\n{umpan_balik['understanding']}\n\n"
        daftar_error = umpan_balik.get("errors", [])
        if daftar_error:
            teks_feedback += "**Masalah yang ditemukan:**\n\n"
            for err in daftar_error:
                nomor_baris = f"Baris {err['line']}: " if err.get("line") else ""
                teks_feedback += f"- {nomor_baris}{err.get('explanation', '')}\n"
                if err.get("fix"):
                    teks_feedback += f"  - Saran: _{err['fix']}_\n"
            teks_feedback += "\n"
        daftar_saran = umpan_balik.get("suggestions", [])
        if daftar_saran:
            teks_feedback += "**Tips dari CodeBot:**\n\n" + "".join(f"- {s}\n" for s in daftar_saran)

        kode_perbaikan = umpan_balik.get("corrected_code", "") or ""
        return keluaran_kode or "(tidak ada output)", teks_feedback, html_status
    except Exception as kesalahan:
        return "", "", alert("error", f"Request gagal: {str(kesalahan)[:250]}")


def h_register_student(name, age, level):
    if not name.strip():
        return alert("warning", "Student name cannot be empty.")
    try:
        d = run(_post("/api/students/", json={
            "name": name, "age": int(age) if age.isdigit() else None, "level": level,
        }))
        lvl_bg = {"beginner": "#D1FAE5", "intermediate": "#FEF3C7", "advanced": "#FEE2E2"}.get(d["level"], "#EEF2FF")
        return (
            f'<div style="display:flex;flex-direction:column;gap:12px;">'
            f'{alert("success", "Student registered successfully! Save the ID below.")}'
            f'<div style="background:var(--c-surface2);border:1.5px solid var(--c-border);'
            f'border-radius:var(--r-lg);padding:20px;display:flex;align-items:center;gap:16px;">'
            f'<div style="font-size:2.8rem;">🎓</div>'
            f'<div>'
            f'<div style="font-size:1.3rem;font-weight:900;color:var(--c-text);">{d["name"]}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;margin-top:5px;">'
            f'<code style="background:var(--c-indigo-pale);color:var(--c-indigo-dark);'
            f'padding:3px 10px;border-radius:6px;font-size:0.95rem;font-weight:800;">ID #{d["id"]}</code>'
            f'<span style="background:{lvl_bg};padding:3px 10px;border-radius:100px;'
            f'font-size:0.72rem;font-weight:800;">{d["level"]}</span>'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    except Exception as e:
        return alert("error", f"Registration failed: {e}")


def h_progress(sid_str):
    if not sid_str.strip().isdigit():
        return alert("warning", "Please enter a numeric student ID.")
    try:
        d       = run(_get(f"/api/students/{sid_str}/progress"))
        name    = d.get("nama", "?")
        level   = d.get("level", "?")
        done    = d.get("total_selesai", 0)
        avg     = d.get("rata_rata_skor")
        courses = d.get("latihan", [])
        total   = len(courses)
        pct     = int(done / total * 100) if total > 0 else 0
        avg_str = f"{avg:.0f}" if avg is not None else "—"
        badge   = "🏆" if done >= 3 else ("⭐" if done >= 1 else "🌱")

        rows = ""
        for item in courses:
            is_done = item["completed"]
            cls     = "done" if is_done else "ongoing"
            score   = f"{item['avg_score']:.0f}" if item.get("avg_score") is not None else "—"
            rows += (
                f'<div class="cb-row {cls}">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<span style="font-size:1.1rem;">{"✅" if is_done else "🔄"}</span>'
                f'<div>'
                f'<div style="font-weight:700;font-size:0.88rem;">{item["exercise_id"]}</div>'
                f'<div style="font-size:0.76rem;color:var(--c-text-3);">{item["attempts"]} attempt(s)</div>'
                f'</div>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div style="font-weight:900;font-size:1.1rem;color:var(--c-text);">{score}</div>'
                f'<div style="font-size:0.70rem;color:var(--c-text-3);">score</div>'
                f'</div>'
                f'</div>'
            )
        if not rows:
            rows = alert("info", "No exercises attempted yet. Get started!")

        return (
            f'<div style="display:flex;flex-direction:column;gap:14px;">'

            # Profile card
            f'<div class="cb-card" style="display:flex;align-items:center;gap:18px;">'
            f'<div style="font-size:3.2rem;">{badge}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:1.4rem;font-weight:900;color:var(--c-text);">{name}</div>'
            f'<div style="font-size:0.83rem;color:var(--c-text-2);margin-top:2px;">'
            f'Level: <strong style="color:var(--c-indigo);">{level}</strong></div>'
            f'<div style="margin-top:8px;">'
            f'<div style="display:flex;justify-content:space-between;font-size:0.76rem;'
            f'font-weight:600;color:var(--c-text-2);margin-bottom:3px;">'
            f'<span>Overall Progress</span><span>{pct}%</span></div>'
            f'<div class="cb-bar-bg"><div class="cb-bar-fill emerald" style="width:{pct}%"></div></div>'
            f'</div>'
            f'</div>'
            f'</div>'

            # Stats
            f'<div class="cb-stat-grid">'
            f'<div class="cb-stat cb-s-indigo"><div class="cb-stat-val">{done}</div><div class="cb-stat-lbl">Completed</div></div>'
            f'<div class="cb-stat cb-s-emerald"><div class="cb-stat-val">{avg_str}</div><div class="cb-stat-lbl">Avg Score</div></div>'
            f'<div class="cb-stat cb-s-sky"><div class="cb-stat-val">{total}</div><div class="cb-stat-lbl">Attempted</div></div>'
            f'<div class="cb-stat cb-s-amber"><div class="cb-stat-val">{pct}%</div><div class="cb-stat-lbl">Completion</div></div>'
            f'</div>'

            # Exercise list
            f'<div class="cb-card">'
            f'<div class="cb-lbl" style="margin-bottom:12px;">Exercise Progress</div>'
            f'{rows}'
            f'</div>'

            f'</div>'
        )
    except httpx.HTTPStatusError as e:
        msg = "Student not found. Check the ID." if e.response.status_code == 404 else str(e)
        return alert("error", msg)
    except Exception as e:
        return alert("error", f"Request failed: {e}")


def h_dashboard():
    try:
        d    = run(_get("/api/teacher/dashboard"))
        r    = d.get("ringkasan", {})
        dist = d.get("distribusi_level", {})
        pop  = d.get("latihan_populer", [])
        stuck= d.get("siswa_stuck", [])
        errs = d.get("top_errors", [])
        sr   = r.get("success_rate_persen", 0)

        # Warna per level untuk distribusi
        warna_level = {"beginner": "#10B981", "intermediate": "#F59E0B", "advanced": "#8B5CF6"}
        dist_html = "".join(
            f'<div style="border-radius:0.5rem;padding:16px 10px;text-align:center;'
            f'background:#F8FAFC;border:1px solid #E2E8F0;">'
            f'<div style="font-size:2rem;font-weight:800;color:{warna_level.get(k,"#64748B")};">{v}</div>'
            f'<div style="font-size:0.75rem;font-weight:600;color:#64748B;'
            f'text-transform:uppercase;letter-spacing:0.05em;margin-top:4px;">{k.capitalize()}</div>'
            f'</div>'
            for k, v in dist.items()
        )
        col = max(1, len(dist))

        # Popular exercises bar chart
        max_att  = max((p["total_attempts"] for p in pop), default=1)
        pop_html = ""
        for p in pop[:5]:
            pct = int(p["total_attempts"] / max_att * 100)
            pop_html += (
                f'<div style="margin-bottom:10px;">'
                f'<div style="display:flex;justify-content:space-between;'
                f'font-size:0.82rem;font-weight:600;margin-bottom:3px;">'
                f'<span style="color:var(--c-text-2);">{p["exercise_id"]}</span>'
                f'<span style="color:var(--c-text-3);">{p["total_attempts"]}×</span>'
                f'</div>'
                f'<div class="cb-bar-bg"><div class="cb-bar-fill" style="width:{pct}%"></div></div>'
                f'</div>'
            )
        if not pop_html:
            pop_html = f'<div style="font-size:0.84rem;color:var(--c-text-3);">No data yet.</div>'

        # Stuck students
        stuck_html = "".join(
            f'<div class="cb-row stuck">'
            f'<div style="display:flex;align-items:center;gap:10px;">'
            f'<span style="font-size:1.05rem;">⚠️</span>'
            f'<div>'
            f'<div style="font-weight:700;font-size:0.88rem;">{s["nama"]}</div>'
            f'<div style="font-size:0.76rem;color:var(--c-text-3);">stuck on <code>{s["exercise_id"]}</code></div>'
            f'</div>'
            f'</div>'
            f'<span style="background:var(--c-rose-pale);color:#9F1239;padding:3px 9px;'
            f'border-radius:100px;font-size:0.72rem;font-weight:800;">{s["attempts"]}×</span>'
            f'</div>'
            for s in stuck[:5]
        ) or alert("success", "No students are currently stuck! 🎉")

        # Top errors
        err_html = ""
        for e in errs:
            err_html += (
                f'<div style="display:flex;align-items:center;justify-content:space-between;'
                f'padding:7px 12px;border-radius:var(--r-sm);margin-bottom:6px;'
                f'background:var(--c-rose-pale);border:1px solid #FECDD3;">'
                f'<code style="font-size:0.83rem;color:#9F1239;font-weight:700;">{e["type"]}</code>'
                f'<span style="background:#FEE2E2;color:#9F1239;padding:2px 9px;'
                f'border-radius:100px;font-size:0.72rem;font-weight:800;">{e["count"]}×</span>'
                f'</div>'
            )
        if not err_html:
            err_html = f'<div style="font-size:0.84rem;color:var(--c-text-3);">No error data yet.</div>'

        # Warna per metrik — pakai inline style agar selalu terlihat
        # meski CSS variable belum load di konteks gr.HTML()
        gaya_stat = (
            "border-radius:0.625rem;padding:24px 20px;text-align:center;"
            "background:#FFFFFF;border:1px solid #E2E8F0;"
            "box-shadow:0 2px 8px rgba(0,0,0,0.06);"
        )
        gaya_nilai = (
            "font-size:2.4rem;font-weight:800;line-height:1;"
            "letter-spacing:-0.02em;margin-bottom:6px;"
        )
        gaya_label = (
            "font-size:0.78rem;font-weight:600;color:#64748B;"
            "text-transform:uppercase;letter-spacing:0.05em;"
        )
        gaya_kartu = (
            "background:#FFFFFF;border:1px solid #E2E8F0;"
            "border-radius:0.625rem;padding:20px;"
        )
        gaya_judul_kartu = (
            "font-weight:700;font-size:0.95rem;color:#1E293B;"
            "margin-bottom:14px;display:block;"
        )

        def kotak_stat(nilai, label, warna):
            return (
                f'<div style="{gaya_stat}border-top:4px solid {warna};">'
                f'<div style="{gaya_nilai}color:{warna};">{nilai}</div>'
                f'<div style="{gaya_label}">{label}</div>'
                f'</div>'
            )

        return (
            f'<div style="display:flex;flex-direction:column;gap:16px;">'

            # Baris 1 — 4 kotak metrik utama
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;">'
            + kotak_stat(r.get("total_siswa", 0),       "Siswa",        "#8B5CF6")
            + kotak_stat(r.get("total_submission", 0),  "Submissions",  "#0EA5E9")
            + kotak_stat(r.get("submission_sukses", 0), "Lulus",        "#10B981")
            + kotak_stat(f'{sr:.0f}%',                  "Success Rate", "#F59E0B")
            + f'</div>'

            # Baris 2 — Distribusi level + Latihan populer
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'

            f'<div style="{gaya_kartu}">'
            f'<span style="{gaya_judul_kartu}">Level Siswa</span>'
            f'<div style="display:grid;grid-template-columns:repeat({col},1fr);gap:10px;">{dist_html}</div>'
            f'</div>'

            f'<div style="{gaya_kartu}">'
            f'<span style="{gaya_judul_kartu}">Latihan Paling Banyak Dicoba</span>'
            f'{pop_html}'
            f'</div>'

            f'</div>'

            # Baris 3 — Siswa butuh bantuan + Error terbanyak
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'

            f'<div style="{gaya_kartu}">'
            f'<span style="{gaya_judul_kartu}">⚠️ Siswa Butuh Bantuan</span>'
            f'{stuck_html}'
            f'</div>'

            f'<div style="{gaya_kartu}">'
            f'<span style="{gaya_judul_kartu}">❌ Error Paling Sering</span>'
            f'{err_html}'
            f'</div>'

            f'</div>'
            f'</div>'
        )
    except Exception as e:
        return alert("error", f"Failed to load dashboard: {e}")


def h_insight():
    try:
        d  = run(_get("/api/teacher/insights"))
        ai = d.get("ai_insight", {})

        sarans = ""
        for idx, s in enumerate(ai.get("saran_pengajaran", []), 1):
            sarans += (
                f'<div class="cb-saran">'
                f'<div class="cb-saran-num">{idx}</div>'
                f'<div>{s}</div>'
                f'</div>'
            )

        return (
            f'<div style="display:flex;flex-direction:column;gap:12px;">'

            f'<div class="cb-ib cb-ib-blue">'
            f'<div class="cb-ib-icon">📋</div>'
            f'<div><div class="cb-ib-title">Class Overview</div>'
            f'<p class="cb-ib-text">{ai.get("kondisi_kelas","—")}</p></div>'
            f'</div>'

            f'<div class="cb-ib cb-ib-yellow">'
            f'<div class="cb-ib-icon">🎯</div>'
            f'<div><div class="cb-ib-title">Topics Needing Attention</div>'
            f'<p class="cb-ib-text">{ai.get("topik_perhatian","—")}</p></div>'
            f'</div>'

            f'<div class="cb-card">'
            f'<div class="cb-lbl" style="margin-bottom:12px;">💡 Recommendations for Next Class</div>'
            f'{sarans or alert("info","Click the button above to generate AI insight.")}'
            f'</div>'

            f'<div class="cb-ib cb-ib-rose">'
            f'<div class="cb-ib-icon">🆘</div>'
            f'<div><div class="cb-ib-title">Students Requiring Special Attention</div>'
            f'<p class="cb-ib-text">{ai.get("siswa_butuh_bantuan","—")}</p></div>'
            f'</div>'

            f'</div>'
        )
    except Exception as e:
        return alert("error", f"Request failed: {e}")


# ============================================================================ #
# UI Layout                                                                    #
# ============================================================================ #

with gr.Blocks(title="CodeBuddy — AI Coding Tutor") as demo:

    # ── HERO ──────────────────────────────────────────────────────────────── #
    gr.HTML("""
    <div class="cb-hero">
      <div class="cb-hero-inner">
        <div class="cb-hero-top">
          <div class="cb-hero-logo">🤖</div>
          <div class="cb-hero-brand">
            <h1>CodeBuddy</h1>
            <p>Asisten AI Belajar Coding Pintar</p>
          </div>
        </div>
        <div class="cb-hero-badges">
          <span class="cb-badge">🤖 AI-Powered</span>
          <span class="cb-badge">🌍 5 Bahasa Daerah</span>
          <span class="cb-badge">📸 OCR Tulisan Tangan</span>
          <span class="cb-badge">🔒 100% Offline</span>
          <span class="cb-badge">🎤 Mode Suara</span>
          <span class="cb-badge">👨‍🏫 Dashboard Guru</span>
        </div>
        <div class="cb-hero-features">
          <div class="cb-feat">
            <span class="cb-feat-icon">📸</span>
            <p class="cb-feat-title">Vision OCR</p>
            <p class="cb-feat-desc">Ekstrak kode langsung dari foto tulisan tangan dengan akurasi tinggi</p>
          </div>
          <div class="cb-feat">
            <span class="cb-feat-icon">🤖</span>
            <p class="cb-feat-title">Agentic Tutoring</p>
            <p class="cb-feat-desc">Pipeline 4 tahap lengkap: syntax → eksekusi → analisis → feedback AI</p>
          </div>
          <div class="cb-feat">
            <span class="cb-feat-icon">🎤</span>
            <p class="cb-feat-title">Mode Suara</p>
            <p class="cb-feat-desc">Tanya jawab interaktif dengan suara untuk pengalaman belajar yang mudah</p>
          </div>
          <div class="cb-feat">
            <span class="cb-feat-icon">🌍</span>
            <p class="cb-feat-title">Bahasa Daerah</p>
            <p class="cb-feat-desc">Mendukung 5 bahasa daerah untuk jangkauan inklusif se-Indonesia</p>
          </div>
        </div>
      </div>
    </div>
    """)

    # ── ONBOARDING BANNER ─────────────────────────────────────────────────── #
    gr.HTML(f'''
    <div class="cb-alert cb-a-info" style="margin: 24px 0; background: linear-gradient(135deg, #EDE9FE 0%, #E0E7FF 100%); border: 2px solid var(--c-indigo);">
        <div class="cb-mascot" style="font-size: 2.5rem;">👋</div>
        <div class="cb-alert-body">
            <strong style="font-size: 1.1rem;">{ONBOARDING_MESSAGES["welcome"]["title"]}</strong>
            {ONBOARDING_MESSAGES["welcome"]["content"]}
        </div>
    </div>
    ''')
    
    # ── LANGUAGE SELECTOR & AUDIO TOGGLE ──────────────────────────────────── #
    
    with gr.Row(equal_height=True):
        with gr.Column(scale=1, elem_classes="cb-card-col"):
            gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">🌍 Pengaturan Bahasa</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Berlaku untuk semua fitur tutor AI</div>')
            lang_global = gr.Dropdown(
                list(LANGUAGE_OPTIONS.keys()),
                value="Indonesian",
                label="Pilih Bahasa Daerah",
                show_label=False
            )
        with gr.Column(scale=1, elem_classes="cb-card-col"):
            gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">🔊 Pengaturan Suara</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Efek suara untuk setiap interaksi</div>')
            gr.HTML("""
                <button onclick="CodeBuddyAudio.toggle(); this.innerHTML = CodeBuddyAudio.enabled ? '🔊 Suara CodeBot (ON)' : '🔇 Suara CodeBot (OFF)';" 
                        style="padding: 12px 18px; border-radius: var(--r-md); background: var(--c-indigo-pale); color: var(--c-indigo-dark);
                               border: 1px solid rgba(79,70,229,0.2); cursor: pointer; font-size: 0.95rem; font-weight: 700; width: 100%; transition: all 0.2s ease;">
                    🔊 Suara CodeBot (ON)
                </button>
            """)

    # ── TABS ──────────────────────────────────────────────────────────────── #
    with gr.Tabs():

        # ═══ TAB 1 — PHOTO SCAN ══════════════════════════════════════════════ #
        with gr.Tab("📸  Photo Scan"):
            gr.HTML(
                '<div class="cb-intro"><span style="font-size:1.1rem">📸</span>'
                '<div>Upload atau foto kode tulisan tangan Python — '
                '<strong>Vision AI</strong> akan membacanya langsung tanpa library OCR eksternal. '
                'Sempurna untuk mendigitalisasi catatan tulisan tangan.</div></div>'
            )
            
            # Demo button untuk OCR
            with gr.Row():
                btn_demo_ocr = gr.Button(f"📺 {DEMO_BUTTON_LABEL}", variant="secondary", size="sm", scale=1)
                demo_ocr_status = gr.HTML(value="", scale=3)
            
            # Visual guide untuk upload area
            gr.HTML("""
                <div class="cb-alert cb-a-info" style="margin-bottom: 16px;">
                    <span class="cb-alert-icon">💡</span>
                    <div class="cb-alert-body">
                        <strong>Tips untuk hasil terbaik:</strong>
                        <div class="upload-guide-tips" style="margin-top: 8px;">
                            <div class="upload-guide-tip">
                                <span>✓</span> Pastikan pencahayaan cukup terang
                            </div>
                            <div class="upload-guide-tip">
                                <span>✓</span> Tulisan terlihat jelas, tidak blur
                            </div>
                            <div class="upload-guide-tip">
                                <span>✓</span> Foto dari atas dengan posisi lurus
                            </div>
                        </div>
                    </div>
                </div>
            """)
            
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">📸 1. Input Foto</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Pilih atau ambil foto tulisan tangan</div>')
                    inp_img = gr.Image(
                        label="Foto Kode Tulisan Tangan",
                        show_label=False,
                        type="filepath",
                        sources=["upload", "webcam", "clipboard"],
                        height=320,
                        elem_classes="upload-area",
                    )
                    btn_ocr = gr.Button("✨ Ekstrak dengan Vision AI", variant="primary", size="lg")
                    out_ocr_info = gr.HTML()
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">📝 2. Hasil Ekstraksi</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Kode Python yang berhasil dibaca AI</div>')
                    out_ocr_code = gr.Code(
                        label="Kode Python",
                        show_label=False,
                        language="python",
                        lines=20,
                    )
            btn_ocr.click(h_ocr, [inp_img], [out_ocr_code, out_ocr_info])
            btn_demo_ocr.click(demo_load_ocr, [], [inp_img, demo_ocr_status])

        # ═══ TAB 2 — AI TUTOR ════════════════════════════════════════════════ #
        with gr.Tab("🎓  AI Tutor"):
            gr.HTML(
                '<div class="cb-intro"><span style="font-size:1.1rem">🎓</span>'
                '<div>Tulis atau tempel kode Python di sebelah kiri — AI akan menjalankannya, menganalisa, '
                'dan memberikan feedback yang actionable dalam bahasa pilihanmu. '
                '<strong>Bukan jawaban langsung</strong> — tutor akan membimbing kamu untuk berpikir sendiri.</div></div>'
            )
            
            # Demo buttons untuk AI Tutor
            with gr.Row():
                btn_demo_tutor_error = gr.Button("📺 Demo: Code with Error", variant="secondary", size="sm", scale=1)
                btn_demo_tutor_success = gr.Button("📺 Demo: Code Success", variant="secondary", size="sm", scale=1)
                demo_tutor_status = gr.HTML(value="", scale=2)
            
            # Tambah mascot intro
            gr.HTML("""
                <div class="cb-alert cb-a-info" style="margin-bottom: 16px; background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%);">
                    <div class="cb-mascot" style="font-size: 2.5rem;">🤖</div>
                    <div class="cb-alert-body">
                        <strong>Halo! Aku CodeBot, teman belajar coding-mu! 👋</strong>
                        <div style="margin-top: 6px; font-size: 0.9375rem;">
                            Aku akan membantu kamu memahami kode dan memperbaiki error. Yuk mulai belajar!
                        </div>
                    </div>
                </div>
            """)
            
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">💻 1. Ruang Kode</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Tulis atau tempel kode Python di sini</div>')
                    inp_code = gr.Code(
                        language="python", lines=13, label="Editor Kode", show_label=False,
                        value='nama = "Adik"\numur = 10\nprint("Halo " + nama + ", kamu berusia " + umur)',
                    )
                    with gr.Row():
                        inp_sid   = gr.Textbox(value="1", label="ID Siswa", scale=1)
                        inp_level = gr.Dropdown(
                            ["beginner", "intermediate", "advanced"],
                            value="beginner", label="Level", scale=2,
                        )
                    inp_ex_id = gr.Textbox(label="ID Latihan (opsional)", placeholder="contoh: hello_print")
                    btn_tutor = gr.Button("🚀 Analisa dengan AI Tutor", variant="primary", size="lg")

                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">🤖 2. Feedback CodeBot</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Hasil analisis, error, dan perbaikan</div>')
                    out_status = gr.HTML()
                    with gr.Tabs():
                        with gr.Tab("💬 Feedback AI"):
                            out_fb = gr.Markdown()
                        with gr.Tab("⚙️ Output Eksekusi"):
                            out_exec = gr.Textbox(lines=9, label="Output Program", show_label=False)
                        with gr.Tab("✅ Kode Diperbaiki"):
                            out_fix = gr.Code(language="python", lines=11, show_label=False)

            btn_tutor.click(
                h_tutor,
                [inp_code, inp_sid, inp_level, inp_ex_id, lang_global],
                [out_exec, out_fb, out_fix, out_status],
            )
            
            # Connect demo buttons
            btn_demo_tutor_error.click(
                demo_load_tutor_error,
                [],
                [inp_code, inp_sid, inp_level, inp_ex_id, demo_tutor_status]
            )
            btn_demo_tutor_success.click(
                demo_load_tutor_success,
                [],
                [inp_code, inp_sid, inp_level, inp_ex_id, demo_tutor_status]
            )

            gr.HTML('<div class="cb-divider"></div>')
            gr.HTML(
                '<div class="cb-intro"><span>💡</span>'
                '<div><strong>Sistem Hint Bertahap</strong> — '
                'AI tidak akan langsung memberikan jawaban. '
                'Pilih level hint: 1 = pertanyaan pemandu, 2 = lokasi error, 3 = solusi lengkap.</div></div>'
            )
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">❓ Masih Bingung?</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Tanya detail error yang terjadi</div>')
                    inp_err = gr.Textbox(label="Pesan Error", placeholder="Tempel error dari output di atas...", show_label=False)
                    inp_hint_lvl = gr.Slider(1, 3, step=1, value=1, label="Level Bantuan (1=Ringan, 3=Penuh)")
                    btn_hint = gr.Button("💡 Minta Hint", variant="primary", size="lg")
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">💡 Bantuan CodeBot</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Petunjuk sesuai level yang kamu minta</div>')
                    out_hint = gr.HTML()
            btn_hint.click(h_hint, [inp_code, inp_err, inp_hint_lvl, lang_global], [out_hint])

        # ═══ TAB 3 — VOICE MODE ══════════════════════════════════════════════ #
        with gr.Tab("🎤  Mode Suara"):
            gr.HTML(
                '<div class="cb-intro"><span style="font-size:1.1rem">🎤</span>'
                '<div>Untuk pengalaman belajar yang lebih mudah — '
                '<strong>rekam pertanyaan dengan suara</strong>, dan CodeBot akan menjawab dengan suara alami. '
                'Sepenuhnya dapat diproses secara offline.</div></div>'
            )
            
            # Tambah mascot intro untuk voice mode
            gr.HTML("""
                <div class="cb-alert cb-a-info" style="margin-bottom: 16px; background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);">
                    <div class="cb-mascot" style="font-size: 2.5rem;">🎤</div>
                    <div class="cb-alert-body">
                        <strong>Ayo ngobrol dengan CodeBot! 🗣️</strong>
                        <div style="margin-top: 6px; font-size: 0.9375rem;">
                            Tanya apa saja tentang coding, aku akan jawab dengan suara yang mudah dipahami.
                        </div>
                    </div>
                </div>
            """)
            
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">🎙️ 1. Tanya Langsung</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Gunakan mikrofonmu</div>')
                    inp_mic = gr.Audio(
                        sources=["microphone"], type="filepath", label="Rekam", show_label=False,
                    )
                    inp_voice_lvl = gr.Dropdown(
                        ["beginner", "intermediate", "advanced"],
                        value="beginner", label="Level Siswa",
                    )
                    btn_ask = gr.Button("🚀 Kirim Pertanyaan", variant="primary", size="lg")
                    out_ask_info = gr.HTML()
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">🔊 2. Jawaban CodeBot</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Audio akan otomatis diputar</div>')
                    out_ask_audio = gr.Audio(label="Audio", show_label=False, autoplay=True)

            btn_ask.click(
                h_voice_ask,
                inputs=[inp_mic, lang_global, inp_voice_lvl],
                outputs=[out_ask_audio, out_ask_info],
                show_progress="hidden",
            )

            gr.HTML('<div class="cb-divider"></div>')
            gr.HTML(
                '<div class="cb-intro"><span>🔊</span>'
                '<div><strong>Text-to-Speech</strong> — Ubah teks menjadi suara natural. '
                'Berguna untuk membacakan feedback AI kepada siswa yang lebih muda.</div></div>'
            )
            
            # Demo button untuk TTS
            with gr.Row():
                btn_demo_tts = gr.Button(f"📺 {DEMO_BUTTON_LABEL}", variant="secondary", size="sm", scale=1)
                demo_tts_status = gr.HTML(value="", scale=3)
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">📝 Teks ke Suara</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Ketik teks yang ingin dibacakan</div>')
                    inp_tts_txt = gr.Textbox(
                        lines=6, label="Teks yang Akan Dibacakan", show_label=False,
                        placeholder="Halo! Saya CodeBot, teman belajar coding kamu!",
                    )
                    with gr.Row():
                        inp_tts_gender = gr.Radio(
                            ["female", "male"],
                            value="female",
                            label="Suara",
                            scale=1,
                            elem_classes="cb-tts-suara",
                        )
                        btn_tts = gr.Button("🔊 Buat Audio", variant="primary", scale=1, size="lg")
                    
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">🔊 Hasil Audio</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Dapat langsung diputar</div>')
                    out_tts_info  = gr.HTML()
                    out_tts_audio = gr.Audio(label="Audio Output", show_label=False)

            btn_tts.click(
                h_tts, [inp_tts_txt, lang_global, inp_tts_gender], [out_tts_audio, out_tts_info],
            )
            
            # Connect demo TTS button
            btn_demo_tts.click(
                demo_load_voice_tts,
                [],
                [inp_tts_txt, inp_tts_gender, demo_tts_status]
            )

        # ═══ TAB 4 — EXERCISES ═══════════════════════════════════════════════ #
        with gr.Tab("📚  Latihan"):
            # Demo button untuk Exercise
            with gr.Row():
                btn_demo_exercise = gr.Button(f"📺 {DEMO_BUTTON_LABEL}", variant="secondary", size="sm", scale=1)
                demo_exercise_status = gr.HTML(value="", scale=3)
            
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes=["cb-card-col", "cb-pustaka-latihan"]):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">📚 Pustaka Latihan</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Pilih dari koleksi latihan kami</div>')
                    with gr.Row():
                        inp_diff = gr.Dropdown(
                            ["All", "Beginner", "Intermediate", "Advanced"],
                            value="All", label="Filter", scale=3,
                        )
                        btn_list = gr.Button("🔍 Tampilkan", variant="primary", scale=1)
                    out_list = gr.HTML()
                    btn_list.click(h_exercise_list, [inp_diff], [out_list])

                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">✨ Buat dengan AI</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Minta CodeBot membuat latihan baru</div>')
                    inp_topic = gr.Textbox(
                        label="Topik", placeholder="contoh: membuat daftar belanja",
                    )
                    with gr.Row():
                        inp_diff_g = gr.Dropdown(
                            ["Beginner", "Intermediate", "Advanced"],
                            value="Beginner", label="Kesulitan", scale=1,
                        )
                        btn_gen = gr.Button("🎲 Buat!", variant="primary", scale=1)
                    out_gen_status = gr.HTML()
                    out_gen_title  = gr.Textbox(label="Judul Latihan", interactive=False)
                    out_gen_instr  = gr.Textbox(label="Instruksi", lines=4, interactive=False)
                    out_gen_code   = gr.Code(label="Kode Awal", language="python", lines=7, interactive=True)

            btn_gen.click(
                h_generate_exercise,
                [inp_topic, inp_diff_g, lang_global],
                [out_gen_title, out_gen_instr, out_gen_code, out_gen_status],
            )

            # ── Mini IDE: tulis & cek kode latihan ──────────────────────────
            gr.HTML('<div class="cb-divider"></div>')
            gr.HTML(
                '<div class="cb-intro"><span>💻</span>'
                '<div><strong>IDE Mini</strong> — Edit kode di atas, lalu tekan '
                '<em>Jalankan &amp; Cek</em> untuk eksekusi dan feedback dari CodeBot.</div></div>'
            )
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML(
                        '<div class="cb-lbl" style="font-size:1.1rem;margin-bottom:4px;">▶ Jalankan Kode</div>'
                        '<div style="color:var(--c-text-3);font-size:0.85rem;margin-bottom:12px;">'
                        'Edit "Kode Awal" di atas, lalu klik tombol di bawah</div>'
                    )
                    with gr.Row():
                        inp_ex_level = gr.Dropdown(
                            ["beginner", "intermediate", "advanced"],
                            value="beginner", label="Level Siswa", scale=2,
                        )
                        btn_cek = gr.Button("▶ Jalankan & Cek", variant="primary", scale=2, size="lg")
                    out_ex_status = gr.HTML()
                    out_ex_output = gr.Textbox(
                        label="Output Kode", lines=5, interactive=False,
                        placeholder="Output program akan muncul di sini...",
                    )
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML(
                        '<div class="cb-lbl" style="font-size:1.1rem;margin-bottom:4px;">🤖 Feedback CodeBot</div>'
                        '<div style="color:var(--c-text-3);font-size:0.85rem;margin-bottom:12px;">'
                        'Penjelasan, kesalahan, dan saran perbaikan</div>'
                    )
                    out_ex_feedback = gr.Markdown(value="", label="Feedback AI")

            btn_cek.click(
                h_latihan_cek,
                inputs=[out_gen_code, out_gen_instr, inp_ex_level, lang_global],
                outputs=[out_ex_output, out_ex_feedback, out_ex_status],
            )
            
            # Connect demo exercise button
            btn_demo_exercise.click(
                demo_load_exercise,
                [],
                [inp_topic, inp_diff_g, demo_exercise_status]
            )

        # ═══ TAB 5 — STUDENTS ════════════════════════════════════════════════ #
        with gr.Tab("👤  Students"):
            # Demo buttons untuk Student
            with gr.Row():
                btn_demo_student = gr.Button("📺 Demo: Register Student", variant="secondary", size="sm", scale=1)
                btn_demo_progress = gr.Button("📺 Demo: Check Progress", variant="secondary", size="sm", scale=1)
                demo_student_status = gr.HTML(value="", scale=2)
            
            with gr.Row(equal_height=True):
                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">📝 Daftar Siswa Baru</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Daftarkan siswa untuk menyimpan kemajuan</div>')
                    inp_name = gr.Textbox(label="Nama Lengkap", placeholder="Budi Santoso")
                    with gr.Row():
                        inp_age     = gr.Textbox(label="Umur", placeholder="10", scale=1)
                        inp_lvl_reg = gr.Dropdown(
                            ["beginner", "intermediate", "advanced"],
                            value="beginner", label="Level Awal", scale=2,
                        )
                    btn_register = gr.Button("✅ Daftar Sekarang", variant="primary", size="lg")
                    out_register = gr.HTML()
                    btn_register.click(h_register_student, [inp_name, inp_age, inp_lvl_reg], [out_register])

                with gr.Column(scale=1, elem_classes="cb-card-col"):
                    gr.HTML('<div class="cb-lbl" style="font-size:1.1rem; margin-bottom: 4px;">📊 Progress Siswa</div><div style="color:var(--c-text-3); font-size:0.85rem; margin-bottom: 12px;">Cek pencapaian dan evaluasi</div>')
                    inp_sid_prog = gr.Textbox(label="ID Siswa", placeholder="contoh: 1")
                    btn_prog     = gr.Button("📈 Lihat Progress", variant="primary", size="lg")
                    out_prog     = gr.HTML()
                    btn_prog.click(h_progress, [inp_sid_prog], [out_prog])
            
            # Connect demo student buttons
            btn_demo_student.click(
                demo_load_student,
                [],
                [inp_name, inp_age, inp_lvl_reg, demo_student_status]
            )
            btn_demo_progress.click(
                demo_load_progress,
                [],
                [inp_sid_prog, demo_student_status]
            )

        # ═══ TAB 6 — TEACHER ═════════════════════════════════════════════════ #
        with gr.Tab("👨‍🏫  Teacher"):
            gr.HTML(
                '<div class="cb-intro"><span style="font-size:1.1rem">👨‍🏫</span>'
                '<div>Monitor the entire class in one view. '
                '<strong>AI</strong> analyzes learning patterns and provides '
                'concrete, actionable teaching recommendations.</div></div>'
            )
            with gr.Tabs():
                with gr.Tab("📊 Class Dashboard"):
                    btn_dash = gr.Button("🔄 Refresh Dashboard", variant="primary")
                    out_dash = gr.HTML()
                    btn_dash.click(h_dashboard, [], [out_dash])

                with gr.Tab("🤖 AI Insight"):
                    gr.HTML(
                        '<div class="cb-alert cb-a-warning" style="margin-bottom:16px;">'
                        '<span class="cb-alert-icon">⏱️</span>'
                        '<div class="cb-alert-body">The AI may take <strong>30–60 seconds</strong> '
                        'to analyze the class data and generate recommendations.</div>'
                        '</div>'
                    )
                    btn_insight = gr.Button("🧠 Generate AI Insight", variant="primary")
                    out_insight = gr.HTML()
                    btn_insight.click(h_insight, [], [out_insight])

    # ── FOOTER ────────────────────────────────────────────────────────────── #
    gr.HTML("""
    <div class="cb-footer">
      <div style="font-size:2rem;margin-bottom:8px;">🤖</div>
      <div style="font-size:1rem;font-weight:700;margin-bottom:6px;">
        CodeBuddy <span style="font-weight:400;">— AI Coding Tutor</span>
      </div>
      <div style="font-size:0.85rem;max-width:600px;margin:0 auto;color:var(--c-text-3);">
        Memberdayakan pelajar Indonesia melalui tutoring AI yang aksesibel dan cerdas.
      </div>
      <div class="cb-footer-links">
        <a class="cb-footer-link" href="http://localhost:8000/docs" target="_blank">📡 API Docs</a>
        <a class="cb-footer-link" href="https://github.com/adindamochamad/codebuddy" target="_blank">💻 GitHub Repo</a>
      </div>
      <div style="margin-top:16px;font-size:0.75rem;color:var(--c-text-3);">
        Dibuat dengan ❤️ untuk Pelajar Indonesia · Powered by Gemma 4
      </div>
    </div>
    """)


# ============================================================================ #
# Entry point                                                                  #
# ============================================================================ #

if __name__ == "__main__":
    tema = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="violet",
        neutral_hue="slate",
    )
    lebar_css = len(dapatkan_css_gradi())
    print(
        f"[CodeBuddy] CSS siap ({lebar_css} byte). "
        "Buka http://127.0.0.1:7860 — jika tampilan tidak berubah, hard refresh: Cmd+Shift+R (Mac) atau Ctrl+Shift+R."
    )
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=tema,
        css=dapatkan_css_gradi(),
        head=FORCE_LIGHT_JS,
    )
