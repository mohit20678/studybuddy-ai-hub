import urllib.parse
import requests
import streamlit as st
from groq import Groq
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
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]  # second one is the backup

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

hero()
tab_chat, tab_img, tab_vid = st.tabs(["💬 Chat", "🖼️ Images", "🎬 Video"])


def stream_reply(messages):
    """Try each model in turn so one broken model name never kills the chat."""
    last_error = None
    for model in MODELS:
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, stream=True
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            return
        except Exception as e:
            last_error = e
    yield f"⚠️ Sorry, I couldn't reach the AI right now. ({last_error})"


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

        with st.chat_message("assistant"):
            reply = st.write_stream(
                stream_reply(
                    [{"role": "system", "content": MODES[mode]}]
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
    st.markdown(VIDEO_CARD, unsafe_allow_html=True)
