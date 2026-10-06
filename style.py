import random
import streamlit as st
import streamlit.components.v1 as components

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }

.stApp { background: #000; overflow-x: hidden; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMainBlockContainer"] { position: relative; z-index: 3; padding-top: 3rem; }

/* Grid */
.stApp::before {
    content: ""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image:
        linear-gradient(rgba(139,92,246,0.14) 1px, transparent 1px),
        linear-gradient(90deg, rgba(139,92,246,0.14) 1px, transparent 1px);
    background-size: 56px 56px;
    -webkit-mask-image: radial-gradient(ellipse at 50% 30%, #000 5%, transparent 70%);
    mask-image: radial-gradient(ellipse at 50% 30%, #000 5%, transparent 70%);
    animation: gridMove 10s linear infinite;
}
@keyframes gridMove { to { background-position: 56px 56px, 56px 56px; } }

/* Glow orbs */
.orb { position: fixed; border-radius: 50%; filter: blur(80px); z-index: 0; pointer-events: none; }
.orb.o1 { width: 520px; height: 520px; background: #7c3aed; opacity: .65; top: -160px; left: -140px;
          animation: drift1 14s ease-in-out infinite; }
.orb.o2 { width: 480px; height: 480px; background: #06b6d4; opacity: .5; bottom: -160px; right: -120px;
          animation: drift2 18s ease-in-out infinite; }
.orb.o3 { width: 380px; height: 380px; background: #ec4899; opacity: .4; top: 40%; left: 60%;
          animation: drift1 22s ease-in-out infinite reverse; }
@keyframes drift1 { 0%,100% { transform: translate(0,0) scale(1); }
                    50% { transform: translate(160px,110px) scale(1.25); } }
@keyframes drift2 { 0%,100% { transform: translate(0,0) scale(1); }
                    50% { transform: translate(-180px,-120px) scale(1.2); } }

/* Floating particles */
.pt { position: fixed; bottom: -12px; width: var(--s); height: var(--s); border-radius: 50%;
      background: #c4b5fd; box-shadow: 0 0 12px 2px rgba(167,139,250,.9);
      z-index: 1; pointer-events: none; opacity: 0; animation: rise linear infinite; }
@keyframes rise { 0% { transform: translateY(0) translateX(0); opacity: 0; }
                  10% { opacity: .9; }
                  90% { opacity: .7; }
                  100% { transform: translateY(-105vh) translateX(40px); opacity: 0; } }

/* Hero */
.hero-wrap { text-align: center; }
.badge { display: inline-block; padding: 6px 18px; border-radius: 999px; font-size: .78rem;
         font-weight: 600; letter-spacing: .12em; color: #ddd6fe;
         background: rgba(139,92,246,.12); border: 1px solid rgba(167,139,250,.5);
         animation: badgePulse 2.5s ease-in-out infinite; }
@keyframes badgePulse { 0%,100% { box-shadow: 0 0 0 0 rgba(139,92,246,.55); }
                        50% { box-shadow: 0 0 22px 4px rgba(139,92,246,.45); } }
.hero-title { font-size: 4.4rem; font-weight: 800; line-height: 1.15; margin: .8rem 0 0 0; }
.hero-icon { display: inline-block; animation: floaty 3s ease-in-out infinite; }
.hero-text {
    background: linear-gradient(90deg, #c4b5fd, #22d3ee, #f472b6, #fbbf24, #c4b5fd);
    background-size: 300% auto;
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
    animation: shine 5s linear infinite, glowPulse 3s ease-in-out infinite;
}
@keyframes shine { to { background-position: 300% center; } }
@keyframes glowPulse { 0%,100% { filter: drop-shadow(0 0 14px rgba(139,92,246,.5)); }
                       50% { filter: drop-shadow(0 0 34px rgba(34,211,238,.8)); } }
@keyframes floaty { 0%,100% { transform: translateY(0) rotate(-5deg); }
                    50% { transform: translateY(-12px) rotate(5deg); } }

.typing { display: inline-block; overflow: hidden; white-space: nowrap; width: 47ch; max-width: 100%;
          border-right: 2px solid #22d3ee; color: #d4d4f0; font-size: 1.05rem;
          animation: typing 3.2s steps(47) .4s both, caret .8s step-end infinite; }
@keyframes typing { from { width: 0; } to { width: 47ch; } }
@keyframes caret { 50% { border-color: transparent; } }

/* Pill tabs */
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }
.stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
.stTabs [data-baseweb="tab"] {
    height: 46px; padding: 0 22px; border-radius: 999px;
    background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12);
    transition: transform .25s ease, background .25s ease, box-shadow .25s ease;
}
.stTabs [data-baseweb="tab"]:hover { transform: translateY(-4px) scale(1.05);
    background: rgba(139,92,246,.2); box-shadow: 0 8px 24px rgba(139,92,246,.4); }
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #7c3aed, #06b6d4) !important;
    border-color: transparent !important; color: #fff !important;
    box-shadow: 0 0 26px rgba(124,58,237,.7); }

/* Feature cards */
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
         gap: 16px; margin: 1.8rem 0 1.2rem 0; }
.card { padding: 20px 18px; border-radius: 20px; cursor: default;
        background: linear-gradient(160deg, rgba(255,255,255,.08), rgba(255,255,255,.02));
        border: 1px solid rgba(255,255,255,.12); backdrop-filter: blur(10px);
        animation: cardIn .7s ease both;
        transition: transform .3s ease, border-color .3s ease, box-shadow .3s ease; }
.card:nth-child(2) { animation-delay: .12s; } .card:nth-child(3) { animation-delay: .24s; }
.card:nth-child(4) { animation-delay: .36s; }
.card:hover { transform: translateY(-10px) scale(1.04); border-color: #a78bfa;
              box-shadow: 0 18px 44px rgba(139,92,246,.5), 0 0 0 1px rgba(167,139,250,.6); }
.card .ic { font-size: 2rem; display: inline-block; transition: transform .35s ease; }
.card:hover .ic { transform: scale(1.35) rotate(-10deg); }
.card h4 { margin: 10px 0 4px 0; font-size: 1.05rem; color: #fff; }
.card p { margin: 0; font-size: .85rem; color: #b8b8d8; line-height: 1.4; }
@keyframes cardIn { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }

/* Chat bubbles */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.12);
    border-radius: 20px; backdrop-filter: blur(10px); animation: slideUp .45s ease;
    transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease; }
[data-testid="stChatMessage"]:hover { transform: translateY(-4px); border-color: rgba(167,139,250,.8);
    box-shadow: 0 12px 34px rgba(139,92,246,.35); }
@keyframes slideUp { from { opacity: 0; transform: translateY(18px); } to { opacity: 1; transform: translateY(0); } }

/* Chat input pulse */
[data-testid="stChatInput"] { border-radius: 18px !important; animation: inputPulse 3s ease-in-out infinite;
    transition: transform .3s ease; }
[data-testid="stChatInput"]:focus-within { transform: translateY(-3px);
    box-shadow: 0 0 0 1px #a78bfa, 0 0 40px rgba(139,92,246,.7); animation: none; }
@keyframes inputPulse { 0%,100% { box-shadow: 0 0 0 1px rgba(139,92,246,.35), 0 0 12px rgba(139,92,246,.2); }
                        50% { box-shadow: 0 0 0 1px rgba(139,92,246,.7), 0 0 30px rgba(139,92,246,.45); } }

.stTextInput > div > div { border-radius: 14px !important; transition: box-shadow .3s ease; }
.stTextInput > div > div:focus-within { box-shadow: 0 0 0 1px #a78bfa, 0 0 26px rgba(139,92,246,.55); }

/* Buttons */
.stButton > button { position: relative; overflow: hidden; border-radius: 14px; color: #fff; font-weight: 600;
    border: 1px solid rgba(255,255,255,.2); background: linear-gradient(135deg, #7c3aed, #06b6d4);
    transition: transform .25s ease, box-shadow .25s ease; }
.stButton > button::after { content: ""; position: absolute; top: 0; left: -80%; width: 50%; height: 100%;
    background: linear-gradient(120deg, transparent, rgba(255,255,255,.5), transparent); transform: skewX(-20deg); }
.stButton > button:hover { transform: translateY(-4px) scale(1.05); box-shadow: 0 14px 34px rgba(6,182,212,.5); color: #fff; }
.stButton > button:hover::after { left: 130%; transition: left .7s ease; }
.stButton > button:active { transform: scale(.96); }

::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: #3b2a7a; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #8b5cf6; }

@media (prefers-reduced-motion: reduce) {
    * { animation: none !important; transition: none !important; }
    .typing { width: auto; } .pt { display: none; }
}
@media (max-width: 640px) { .hero-title { font-size: 2.6rem; } }
</style>
"""

ORBS = '<div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div>'


def _particles():
    random.seed(7)
    out = []
    for _ in range(24):
        x = random.randint(0, 100)
        s = random.randint(2, 5)
        d = random.randint(10, 22)
        delay = random.randint(0, 15)
        out.append(
            f'<span class="pt" style="left:{x}%;--s:{s}px;'
            f'animation-duration:{d}s;animation-delay:-{delay}s"></span>'
        )
    return "".join(out)


def load_css():
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(ORBS + _particles(), unsafe_allow_html=True)


def cursor_glow():
    # A soft spotlight that follows the mouse
    components.html(
        """<script>
        const d = window.parent.document;
        if (!d.getElementById('cursor-glow')) {
          const g = d.createElement('div');
          g.id = 'cursor-glow';
          g.style.cssText = 'position:fixed;width:420px;height:420px;border-radius:50%;'
            + 'pointer-events:none;z-index:1;left:50%;top:35%;'
            + 'background:radial-gradient(circle, rgba(139,92,246,.30), transparent 65%);'
            + 'transform:translate(-50%,-50%);transition:left .12s ease-out, top .12s ease-out;';
          d.body.appendChild(g);
          d.addEventListener('mousemove', function(e) {
            g.style.left = e.clientX + 'px';
            g.style.top = e.clientY + 'px';
          });
        }
        </script>""",
        height=0,
    )


def hero():
    st.markdown(
        '<div class="hero-wrap">'
        '<div class="badge">✨ 100% FREE · AI POWERED</div>'
        '<div class="hero-title"><span class="hero-icon">📚</span> '
        '<span class="hero-text">Study Buddy</span></div>'
        '<div style="margin:.7rem 0 1.4rem 0;">'
        '<span class="typing">Ask. Learn. Create. Your free AI study partner.</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def cards():
    items = [
        ("🧠", "Explain Anything", "Hard topics broken into simple steps"),
        ("📝", "Revision Notes", "Quick summaries of any chapter"),
        ("❓", "Make a Quiz", "Test yourself before the exam"),
        ("🎨", "Create Visuals", "Diagrams, mind maps and posters"),
    ]
    html = "".join(
        f'<div class="card"><span class="ic">{i}</span><h4>{t}</h4><p>{p}</p></div>'
        for i, t, p in items
    )
    st.markdown(f'<div class="cards">{html}</div>', unsafe_allow_html=True)


EXTRAS = """
<style>
@property --ang { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
@keyframes ringSpin { to { --ang: 360deg; } }

/* Tagline: blink while typing, then hide the cursor */
.typing { animation: typing 3.2s steps(47) .4s both, caret .8s step-end 6 forwards !important; }
@keyframes caret { 0%,49% { border-color: #22d3ee; } 50%,100% { border-color: transparent; } }

/* Real pill tabs inside a glass bar */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px !important; padding: 8px !important; width: fit-content !important;
    margin: 0 auto 1.2rem auto !important; border-radius: 999px !important;
    background: rgba(255,255,255,.05) !important; border: 1px solid rgba(255,255,255,.12) !important;
    backdrop-filter: blur(14px); box-shadow: 0 10px 40px rgba(0,0,0,.5);
}
.stTabs button[data-baseweb="tab"], .stTabs [data-baseweb="tab"] {
    border-radius: 999px !important; border: none !important; background: transparent !important;
    height: 46px !important; padding: 0 28px !important; font-weight: 600 !important;
    transition: transform .25s ease, background .25s ease, box-shadow .25s ease !important;
}
.stTabs [data-baseweb="tab"]:hover { background: rgba(139,92,246,.25) !important;
    transform: translateY(-3px) scale(1.06); box-shadow: 0 8px 22px rgba(139,92,246,.45); }
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #7c3aed, #06b6d4) !important; color: #fff !important;
    animation: pillGlow 2.5s ease-in-out infinite;
}
@keyframes pillGlow { 0%,100% { box-shadow: 0 0 14px rgba(124,58,237,.6); }
                      50% { box-shadow: 0 0 34px rgba(6,182,212,.8); } }

/* Spinning rainbow border on inputs */
[data-testid="stChatInput"], .stTextInput > div > div {
    border: 2px solid transparent !important; border-radius: 18px !important;
    background: linear-gradient(#0a0a12, #0a0a12) padding-box,
                conic-gradient(from var(--ang), #7c3aed, #06b6d4, #ec4899, #fbbf24, #7c3aed) border-box !important;
    animation: ringSpin 4s linear infinite !important;
}
[data-testid="stChatInput"] > div, .stTextInput input { background: transparent !important; }

/* Select box */
[data-baseweb="select"] > div { border-radius: 14px !important; background: rgba(255,255,255,.05) !important;
    border: 1px solid rgba(255,255,255,.15) !important; transition: box-shadow .3s ease; }
[data-baseweb="select"] > div:hover { box-shadow: 0 0 22px rgba(139,92,246,.5); }

/* Cards: rainbow line on hover */
.card { position: relative; overflow: hidden; }
.card::before { content: ""; position: absolute; top: 0; left: 0; height: 3px; width: 0;
    background: linear-gradient(90deg, #7c3aed, #22d3ee, #ec4899); transition: width .45s ease; }
.card:hover::before { width: 100%; }

/* Studio headings */
.studio-title { font-size: 1.9rem; font-weight: 800; margin: .2rem 0 0 0;
    background: linear-gradient(90deg, #c4b5fd, #22d3ee); -webkit-background-clip: text;
    background-clip: text; -webkit-text-fill-color: transparent; }
.studio-sub { color: #b8b8d8; margin: 0 0 1rem 0; }

/* Image placeholder frame */
.img-frame { margin-top: 1rem; padding: 3rem 1rem; text-align: center; border-radius: 22px;
    border: 2px dashed rgba(167,139,250,.5); background: rgba(139,92,246,.05);
    animation: frameGlow 3s ease-in-out infinite; }
.img-frame .ph { font-size: 3.2rem; display: inline-block; animation: floaty 3s ease-in-out infinite; }
.img-frame p { margin: .6rem 0 0 0; color: #c4c4e0; }
@keyframes frameGlow { 0%,100% { border-color: rgba(167,139,250,.35); box-shadow: 0 0 0 rgba(139,92,246,0); }
                       50% { border-color: rgba(34,211,238,.8); box-shadow: 0 0 34px rgba(34,211,238,.25); } }

/* Generated image glow */
[data-testid="stImage"] img { border-radius: 20px; box-shadow: 0 0 44px rgba(139,92,246,.55);
    animation: slideUp .6s ease; }

/* Video card */
.vid-card { margin-top: 1rem; padding: 2.6rem 1.4rem; text-align: center; border-radius: 26px;
    border: 2px solid transparent;
    background: linear-gradient(#0a0a12, #0a0a12) padding-box,
                conic-gradient(from var(--ang), #7c3aed, #06b6d4, #ec4899, #7c3aed) border-box;
    animation: ringSpin 6s linear infinite; }
.vid-card .reel { font-size: 4rem; display: inline-block; animation: floaty 2.6s ease-in-out infinite; }
.vid-card h3 { margin: .4rem 0; font-size: 1.7rem; color: #fff; }
.vid-card p { color: #b8b8d8; margin: 0 0 1.2rem 0; }
.vid-card .bar { width: min(420px, 80%); height: 10px; margin: 0 auto 1.4rem auto; border-radius: 999px;
    background: rgba(255,255,255,.1); overflow: hidden; }
.vid-card .bar span { display: block; height: 100%; width: 65%; border-radius: 999px;
    background: linear-gradient(90deg, #7c3aed, #22d3ee, #ec4899, #7c3aed); background-size: 300% 100%;
    animation: shine 3s linear infinite; }
.vid-card .chips span { display: inline-block; margin: 5px; padding: 8px 16px; border-radius: 999px;
    font-size: .85rem; color: #ddd6fe; background: rgba(139,92,246,.15);
    border: 1px solid rgba(167,139,250,.4); transition: transform .25s ease, box-shadow .25s ease; }
.vid-card .chips span:hover { transform: translateY(-4px) scale(1.07); box-shadow: 0 8px 22px rgba(139,92,246,.5); }

.stDownloadButton > button { border-radius: 14px; border: 1px solid rgba(34,211,238,.6);
    background: rgba(34,211,238,.1); color: #a5f3fc; transition: transform .25s ease, box-shadow .25s ease; }
.stDownloadButton > button:hover { transform: translateY(-3px); box-shadow: 0 10px 26px rgba(34,211,238,.4); color: #fff; }
</style>
"""

IMG_PLACEHOLDER = (
    '<div class="img-frame"><div class="ph">🖼️</div>'
    '<p>Your creation will appear here</p></div>'
)

VIDEO_CARD = (
    '<div class="vid-card"><div class="reel">🎬</div><h3>Video Studio</h3>'
    '<p>Coming soon: turn your notes into short explainer clips.</p>'
    '<div class="bar"><span></span></div>'
    '<div class="chips"><span>🎞️ Text to video</span><span>🗣️ Voice narration</span>'
    '<span>📽️ Slide explainers</span></div></div>'
)


def load_extras():
    st.markdown(EXTRAS, unsafe_allow_html=True)


FIX = """
<style>
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
    z-index: 50 !important; background: transparent !important;
}
[data-testid="stChatInput"] {
    position: relative; z-index: 60 !important; pointer-events: auto !important;
}
[data-testid="stChatInput"] * { pointer-events: auto !important; }
[data-testid="stChatInput"] textarea {
    color: #ffffff !important; caret-color: #22d3ee !important;
    background: transparent !important;
}
</style>
"""


def load_extras():
    st.markdown(EXTRAS + FIX, unsafe_allow_html=True)


WIDE = """
<style>
/* Use almost the full screen on every tab */
[data-testid="stMainBlockContainer"], [data-testid="stAppViewBlockContainer"], .block-container {
    max-width: 1600px !important; width: 96% !important;
    padding-left: 2rem !important; padding-right: 2rem !important;
}
/* Question box at the bottom matches the same width */
[data-testid="stBottomBlockContainer"] {
    max-width: 1600px !important; width: 96% !important;
    padding-left: 2rem !important; padding-right: 2rem !important;
}

/* Chat messages: no colored line, no glow */
[data-testid="stChatMessage"], [data-testid="stChatMessage"]:hover {
    border: none !important; box-shadow: none !important;
    background: rgba(255,255,255,0.045) !important;
}
[data-testid="stChatMessage"]:hover { transform: none !important; }
</style>
"""


def load_extras():
    st.markdown(EXTRAS + FIX + WIDE, unsafe_allow_html=True)


PIN = """
<style>
/* Question box pinned to the bottom of the screen */
[data-testid="stChatInput"] {
    position: fixed !important; bottom: 24px !important; left: 0 !important; right: 0 !important;
    margin: 0 auto !important; width: min(94%, 1500px) !important; z-index: 100 !important;
    transform: none !important;
}

/* Plain border: no rainbow, no glow, no animation */
[data-testid="stChatInput"], [data-testid="stChatInput"]:hover, [data-testid="stChatInput"]:focus-within {
    border: 1px solid rgba(255,255,255,0.18) !important;
    background: #0d0d14 !important;
    animation: none !important; box-shadow: none !important; transform: none !important;
    border-radius: 18px !important;
}
[data-testid="stChatInput"]:focus-within { border-color: rgba(255,255,255,0.45) !important; }

/* Soft dark fade under the box so messages don't clash with it */
.stApp::after {
    content: ""; position: fixed; left: 0; right: 0; bottom: 0; height: 120px;
    background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.9) 65%);
    z-index: 90; pointer-events: none;
}

/* Space at the bottom so the last message is never hidden */
[data-testid="stMainBlockContainer"], .block-container { padding-bottom: 150px !important; }
</style>
"""


def load_extras():
    st.markdown(EXTRAS + FIX + WIDE + PIN, unsafe_allow_html=True)


def scroll_bottom():
    components.html(
        """<script>
        const m = window.parent.document.querySelector('[data-testid="stMain"]');
        if (m) { m.scrollTo({ top: m.scrollHeight, behavior: 'smooth' }); }
        </script>""",
        height=0,
    )


VISIBLE = """
<style>
/* Remove the fade that was covering the box */
.stApp::after { display: none !important; content: none !important; }

/* Bottom bar sits above everything */
[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
    z-index: 999 !important; background: transparent !important;
}

/* A clear, bright chat box like ChatGPT */
[data-testid="stChatInput"] {
    z-index: 1000 !important; opacity: 1 !important;
    bottom: 28px !important;
    background: #17171f !important;
    border: 1px solid rgba(255,255,255,0.28) !important;
    border-radius: 26px !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.6) !important;
}
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] div {
    background: transparent !important;
}
[data-testid="stChatInput"] textarea {
    color: #ffffff !important; font-size: 1rem !important;
    min-height: 34px !important; padding-top: 10px !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #a1a1b5 !important; opacity: 1 !important;
}
[data-testid="stChatInput"] button {
    background: #ffffff !important; color: #000000 !important; border-radius: 50% !important;
}
[data-testid="stChatInput"] button svg { fill: #000000 !important; }
</style>
"""


def load_extras():
    st.markdown(EXTRAS + FIX + WIDE + PIN + VISIBLE, unsafe_allow_html=True)
