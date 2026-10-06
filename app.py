import urllib.parse
import requests
import streamlit as st
from groq import Groq
from style import (scroll_bottom, load_css, load_extras, hero, cards, cursor_glow,
                   IMG_PLACEHOLDER, VIDEO_CARD)

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
MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = (
    "You are a friendly college study assistant. Explain concepts step by step "
    "with simple examples. When asked, create summaries, quizzes, and revision notes."
)

hero()
tab_chat, tab_img, tab_vid = st.tabs(["💬 Chat", "🖼️ Images", "🎬 Video"])

# ---------------- CHAT ----------------
with tab_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

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
            stream = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}]
                + st.session_state.messages,
                stream=True,
            )
            reply = st.write_stream(
                chunk.choices[0].delta.content or "" for chunk in stream
            )
        st.session_state.messages.append({"role": "assistant", "content": reply})
        scroll_bottom()
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
