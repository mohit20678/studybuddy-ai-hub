import io
import re
import urllib.parse
import requests
import streamlit as st
from groq import Groq
from video import make_video, VOICES
from pypdf import PdfReader
from style import (scroll_bottom, load_css, load_extras, hero, cards,
                   cursor_glow, IMG_PLACEHOLDER, VIDEO_CARD)

st.set_page_config(page_title="Study Buddy", page_icon="📚", layout="wide")
load_css()
load_extras()
cursor_glow()

# --- Simple password so only you and friends can use it ---
if "authed" not in st.session_state:
    st.session_state.authed = False
if not st.session_state.authed:
    pw = st.text_input("Password", type="password")
    if pw and pw == st.secrets["APP_PASSWORD"]:
        st.session_state.authed = True
        st.rerun()
    st.stop()

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
MODELS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]  # fast first, smarter as backup

MAX_PAGES = 30       # pages read from an uploaded PDF
MAX_CHARS = 20000    # most text sent to the AI per question (raise to 30000 if limits allow)
CHUNK = 1500

BASE = "You are a friendly college study assistant. "
MODES = {
    "🧠 Explain simply": BASE + (
        "Explain the topic step by step in simple language, like teaching a beginner. "
        "Use one everyday analogy and a small example. End with a 2-line recap."
    ),
    "📝 Revision notes": BASE + (
        "Turn the topic into exam revision notes: short headings, bullet points, key terms in bold, "
        "formulas or definitions where relevant, and one memory trick at the end. Keep it compact."
    ),
    "❓ Quiz me": BASE + (
        "Run a quiz on the topic. Ask ONE multiple-choice question at a time with options A to D. "
        "Wait for the student's answer, then say if it is right, explain briefly, and ask the next question. "
        "After 5 questions, give a score and the topics to revise."
    ),
    "⚡ Quick summary": BASE + (
        "Summarize the topic or text in under 120 words, then list 3 to 5 key points."
    ),
    "🎓 Exam answer": BASE + (
        "Write a well-structured university exam answer: a short introduction, numbered points with "
        "headings, an example or diagram description if useful, and a conclusion."
    ),
}

NOTES_INTRO = (
    "\n\nThe student uploaded study notes. Base your answer on these excerpts when relevant, "
    "and say clearly if something is not covered in them.\n\nNOTES:\n"
)


@st.cache_data(show_spinner=False)
def read_pdf(data: bytes, max_pages: int):
    """Return (text of the first max_pages pages, total pages). PyMuPDF first, pypdf as backup."""
    try:
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        total = len(doc)
        text = "\n".join(doc[i].get_text() for i in range(min(total, max_pages)))
        if text.strip():
            return text, total
    except Exception:
        pass
    try:
        reader = PdfReader(io.BytesIO(data))
        total = len(reader.pages)
        text = "\n".join(
            (reader.pages[i].extract_text() or "") for i in range(min(total, max_pages))
        )
        return text, total
    except Exception:
        return "", 0


@st.cache_resource(show_spinner=False)
def get_ocr():
    from rapidocr import RapidOCR
    return RapidOCR()


@st.cache_data(show_spinner=False)
def ocr_pdf(data: bytes, max_pages: int):
    """Read scanned pages by turning each page into an image and running OCR."""
    import fitz
    engine = get_ocr()
    doc = fitz.open(stream=data, filetype="pdf")
    total = len(doc)
    parts = []
    for i in range(min(total, max_pages)):
        png = doc[i].get_pixmap(dpi=150).tobytes("png")
        res = engine(png)
        txts = getattr(res, "txts", None)
        if txts:
            parts.append("\n".join(txts))
    return "\n\n".join(parts), total


def pick_context(text, question, limit):
    """Choose the parts of the notes that best match the question."""
    if len(text) <= limit:
        return text
    chunks = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)]
    n = max(1, limit // CHUNK)
    words = set(re.findall(r"\w{4,}", question.lower()))
    scores = [sum(c.lower().count(w) for w in words) for c in chunks]
    if max(scores) == 0:
        # General request (like "summarize"): sample evenly across the whole document
        step = len(chunks) / n
        picked = sorted({int(k * step) for k in range(n)})
    else:
        top = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:n]
        picked = sorted(top)
    return "\n...\n".join(chunks[i] for i in picked)


def stream_reply(messages):
    """Try each model in turn so one broken model name never kills the chat."""
    last_error = None
    for model in MODELS:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, stream=True,
                reasoning_effort="low",
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            last_error = e
    yield f"⚠️ Sorry, I couldn't reach the AI right now. ({last_error})"


hero()
tab_chat, tab_img, tab_vid = st.tabs(["💬 Chat", "🖼️ Images", "🎬 Video"])

# ---------------- CHAT ----------------
with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    top_l, top_r = st.columns([6, 1])
    with top_l:
        mode = st.pills(
            "Study mode", list(MODES.keys()), default="🧠 Explain simply",
            label_visibility="collapsed",
        )
    with top_r:
        if st.button("🗑️ Clear chat"):
            st.session_state.messages = []
            st.rerun()

    mode = mode or "🧠 Explain simply"

    pdf_text = ""
    with st.expander(f"📎 Upload study notes (PDF, first {MAX_PAGES} pages are read)"):
        pdf = st.file_uploader("Choose a PDF", type="pdf", label_visibility="collapsed")
        if pdf:
            text, total = read_pdf(pdf.getvalue(), MAX_PAGES)
            if not text.strip():
                try:
                    with st.spinner("Scanned PDF detected. Reading the pages with OCR (this can take a minute)..."):
                        text, total = ocr_pdf(pdf.getvalue(), MAX_PAGES)
                except Exception as e:
                    st.error(f"OCR failed: {e}")
            if text.strip():
                used = min(total, MAX_PAGES)
                st.success(f"Loaded {used} of {total} pages.")
                if total > MAX_PAGES:
                    st.info(f"This PDF has {total} pages. Only the first {MAX_PAGES} are used.")
                pdf_text = text
            else:
                st.warning("I couldn't read any text from this PDF. It may be a scanned image.")

    st.caption(f"Mode: **{mode}**. Pick a mode, then ask your question below.")

    if not st.session_state.messages:
        cards()

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Ask anything about your subjects..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        notes_context = ""
        if pdf_text:
            query = " ".join(
                m["content"] for m in st.session_state.messages if m["role"] == "user"
            )[-1500:]
            notes_context = NOTES_INTRO + pick_context(pdf_text, query, MAX_CHARS)

        with st.chat_message("assistant"):
            reply = st.write_stream(
                stream_reply(
                    [{"role": "system", "content": MODES[mode] + notes_context}]
                    + st.session_state.messages
                )
            )
        st.session_state.messages.append({"role": "assistant", "content": reply})
        scroll_bottom()

# ---------------- IMAGES ----------------
with tab_img:
    st.markdown(
        '<div class="studio-title">🎨 Image Studio</div>'
        '<p class="studio-sub">Turn ideas into diagrams, mind maps and posters.</p>',
        unsafe_allow_html=True,
    )
    style_choice = st.selectbox(
        "Style",
        ["Clean diagram", "Colorful mind map", "Poster", "Realistic photo", "Cartoon"],
    )
    img_prompt = st.text_input("Describe the image")
    go = st.button("✨ Generate image")
    slot = st.empty()

    if go and img_prompt:
        with st.spinner("Creating your image..."):
            full_prompt = f"{img_prompt}, {style_choice} style"
            url = "https://image.pollinations.ai/prompt/" + urllib.parse.quote(full_prompt)
            r = requests.get(url, timeout=120)
        if r.ok:
            slot.image(r.content)
            st.download_button("⬇️ Download image", r.content, "study-buddy.png", "image/png")
        else:
            slot.error("Image service failed. Try again in a bit.")
    else:
        slot.markdown(IMG_PLACEHOLDER, unsafe_allow_html=True)

# ---------------- VIDEO ----------------
with tab_vid:
    st.markdown(
        '<div class="studio-title">🎬 Video Studio</div>'
        '<p class="studio-sub">Type a topic and get a narrated, animated explainer video.</p>',
        unsafe_allow_html=True,
    )
    v_topic = st.text_input("Video topic", placeholder="e.g. How photosynthesis works")
    vc1, vc2 = st.columns(2)
    with vc1:
        v_voice = st.selectbox("Voice", list(VOICES.keys()))
    with vc2:
        v_scenes = st.slider("Number of scenes", 3, 6, 4)

    if st.button("🎬 Create video") and v_topic:
        bar = st.progress(0.0, text="Starting...")
        try:
            data, scenes, info = make_video(
                client, MODELS, v_topic, v_scenes, VOICES[v_voice],
                lambda f, t: bar.progress(f, text=t),
            )
            st.session_state.video = (data, scenes, info)
        except Exception as e:
            st.error(f"Video failed: {e}")
        bar.empty()

    vid = st.session_state.get("video")
    if vid and len(vid) == 3:
        data, scenes, info = vid
        st.video(data)
        st.download_button("⬇️ Download video", data, "study-buddy-video.mp4", "video/mp4")
        if info.get("fallback_images"):
            st.info(f"{info['fallback_images']} scene(s) used a plain background because the image service was busy.")
        if info.get("voice_engine") != "edge":
            st.info("The natural voice was unavailable, so a basic voice was used.")
        with st.expander("📜 Script"):
            for i, sc in enumerate(scenes, 1):
                st.markdown(f"**Scene {i}.** {sc['narration']}")
