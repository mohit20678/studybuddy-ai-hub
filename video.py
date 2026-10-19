import asyncio
import io
import json
import math
import os
import re
import subprocess
import tempfile
import time
import urllib.parse
import wave

import imageio_ffmpeg
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, FPS = 1280, 720, 24
SRC_W, SRC_H = 1600, 900          # size of the illustrations (extra room for camera moves)
RATE = 44100
LEAD, TAIL = 0.35, 0.7            # seconds of quiet before and after each narration
INTRO_FRAMES = FPS * 3
OUTRO_FRAMES = int(FPS * 3.2)
FADE = 10
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
RESAMPLE = Image.Resampling.BICUBIC

VOICES = {
    "Neerja (India, female)": "en-IN-NeerjaNeural",
    "Prabhat (India, male)": "en-IN-PrabhatNeural",
    "Aria (US, female)": "en-US-AriaNeural",
    "Guy (US, male)": "en-US-GuyNeural",
    "Sonia (UK, female)": "en-GB-SoniaNeural",
    "Ryan (UK, male)": "en-GB-RyanNeural",
}

PALETTES = [
    ((22, 12, 54), (4, 4, 12), (124, 58, 237), (6, 182, 212)),
    ((10, 22, 52), (3, 6, 14), (6, 182, 212), (236, 72, 153)),
    ((34, 12, 48), (6, 3, 12), (236, 72, 153), (124, 58, 237)),
    ((8, 30, 40), (3, 8, 12), (16, 185, 129), (6, 182, 212)),
]

# ------------------------------------------------------------------ helpers
_fonts = {}


def font(size):
    if size in _fonts:
        return _fonts[size]
    f = None
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf",
                 "Arial Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            f = ImageFont.truetype(name, size)
            break
        except Exception:
            continue
    if f is None:
        f = ImageFont.load_default(size=size)
    _fonts[size] = f
    return f


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_center(d, text, y, fnt, fill):
    w = d.textlength(text, font=fnt)
    d.text(((W - w) / 2, y), text, font=fnt, fill=fill)


def silence(sec):
    return b"\x00\x00" * max(0, int(RATE * sec))


def gradient(c1, c2):
    mask = Image.linear_gradient("L").resize((W, H))
    return Image.composite(Image.new("RGB", (W, H), c2), Image.new("RGB", (W, H), c1), mask)


def fancy_bg(seed):
    c1, c2, g1, g2 = PALETTES[seed % len(PALETTES)]
    base = gradient(c1, c2).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    d.ellipse((-150, -200, 550, 450), fill=g1 + (150,))
    d.ellipse((800, 300, 1400, 900), fill=g2 + (130,))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    return Image.alpha_composite(base, glow).convert("RGB")


_vig = None


def vignette():
    global _vig
    if _vig is None:
        vh = int(H * 0.5)
        a = Image.linear_gradient("L").resize((W, vh)).point(lambda v: int(v * 0.72))
        layer = Image.new("RGBA", (W, vh), (0, 0, 0, 0))
        layer.putalpha(a)
        _vig = layer
    return _vig


# ------------------------------------------------------------------ script, images, voice
def make_script(client, models, topic, n_scenes):
    prompt = (
        f"Write a short educational explainer video script about: {topic}.\n"
        f"Use exactly {n_scenes} scenes that flow like a good lesson: a hook, the key ideas, "
        "a real-life example, and a quick recap in the last scene.\n"
        "Each scene needs 'narration' (2 or 3 short, clear sentences, 30 to 45 words, easy "
        "language for a college student) and 'image_prompt' (a vivid description of ONE "
        "illustration that matches the narration).\n"
        'Reply with ONLY JSON like {"title": "Short catchy title", "scenes": '
        '[{"narration": "...", "image_prompt": "..."}]}. No other text.'
    )
    last = None
    for model in models:
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                reasoning_effort="low",
            )
            text = r.choices[0].message.content or ""
            data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
            scenes = [s for s in data.get("scenes", []) if s.get("narration")]
            if scenes:
                return (data.get("title") or topic).strip(), scenes[:n_scenes]
        except Exception as e:
            last = e
    raise RuntimeError(f"Could not write the script ({last})")


STYLE = (", flat vector educational illustration, vibrant colors, soft gradients, "
         "centered subject, wide 16:9, no text, no letters")


def get_image(prompt, i):
    """Return (PIL image, True) or a gradient fallback (image, False)."""
    url = (
        "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt + STYLE)
        + f"?width={SRC_W}&height={SRC_H}&nologo=true&seed={i + 11}"
    )
    for _ in range(2):
        try:
            r = requests.get(url, timeout=90)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                img = Image.open(io.BytesIO(r.content)).convert("RGB")
                return ImageOps.fit(img, (SRC_W, SRC_H), Image.Resampling.LANCZOS), True
        except Exception:
            pass
        time.sleep(2)
    return fancy_bg(i + 2).resize((SRC_W, SRC_H)), False


def synth(text, voice, path):
    """Natural voice first (edge-tts), basic Google voice as a backup."""
    try:
        import edge_tts

        async def go():
            await edge_tts.Communicate(text, voice, rate="-4%").save(path)

        asyncio.run(go())
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return "edge"
    except Exception:
        pass
    from gtts import gTTS
    gTTS(text=text, lang="en").save(path)
    return "gtts"


def to_wav(src, dst):
    subprocess.run(
        [FFMPEG, "-y", "-i", src, "-ar", str(RATE), "-ac", "1", "-sample_fmt", "s16", dst],
        check=True, capture_output=True,
    )


def read_wav(path):
    with wave.open(path, "rb") as w:
        return w.readframes(w.getnframes())


# ------------------------------------------------------------------ drawing
def kb_box(style, t):
    """Camera move: zoom in, zoom out, pan right, pan left."""
    e = ease(t)
    if style == 0:
        z, fx = 1.0 + 0.16 * e, 0.5
    elif style == 1:
        z, fx = 1.16 - 0.16 * e, 0.5
    elif style == 2:
        z, fx = 1.14, e
    else:
        z, fx = 1.14, 1 - e
    bw, bh = SRC_W / z, SRC_H / z
    x0 = fx * (SRC_W - bw)
    y0 = (SRC_H - bh) / 2
    return (max(0.0, x0), max(0.0, y0), min(float(SRC_W), x0 + bw), min(float(SRC_H), y0 + bh))


def card_frame(bg, f, nf, label, title, sub, fade_out=False):
    z = 1 + 0.06 * (f / nf)
    bw, bh = W / z, H / z
    frame = bg.resize((W, H), RESAMPLE, box=(max(0.0, (W - bw) / 2), max(0.0, (H - bh) / 2), min(float(W), (W + bw) / 2), min(float(H), (H + bh) / 2)))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    e1 = ease(f / (FPS * 0.5))
    e2 = ease((f - 5) / (FPS * 0.8))
    e3 = ease((f - 16) / (FPS * 0.7))
    lines = wrap(d, title, font(78), W - 260)
    y = (H - len(lines) * 96) // 2 - 20 + (1 - e2) * 28
    if label:
        draw_center(d, label, y - 62, font(26), (103, 232, 249, int(255 * e1)))
    for ln in lines:
        draw_center(d, ln, y, font(78), (255, 255, 255, int(255 * e2)))
        y += 96
    bar = int(260 * e3)
    d.rounded_rectangle(((W - bar) / 2, y + 10, (W + bar) / 2, y + 16), radius=3, fill=(139, 92, 246, 255))
    if sub:
        draw_center(d, sub, y + 34, font(32), (200, 200, 225, int(255 * e3)))
    frame.paste(layer, (0, 0), layer)
    if fade_out and f > nf - 12:
        frame = Image.blend(frame, Image.new("RGB", (W, H)), (f - (nf - 12)) / 12)
    return frame


def build_layout(text):
    """Caption layout: words with positions inside a rounded box (stable while words appear)."""
    scratch = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    fnt = font(38)
    lines = wrap(scratch, text, fnt, W - 320)
    line_h, pad_x, pad_y = 54, 36, 28
    widths = [scratch.textlength(l, font=fnt) for l in lines]
    box_w = int(max(widths) + 2 * pad_x)
    box_h = len(lines) * line_h + 2 * pad_y
    items = []
    for li, line in enumerate(lines):
        x = (box_w - widths[li]) / 2
        prefix = ""
        for w in line.split():
            items.append((w, x + scratch.textlength(prefix, font=fnt), pad_y + li * line_h))
            prefix += w + " "
    return items, (box_w, box_h), ((W - box_w) // 2, H - 56 - box_h)


def make_overlay(items, size, k):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=26, fill=(8, 8, 18, 205))
    fnt = font(38)
    for j, (w, x, y) in enumerate(items[:k]):
        col = (103, 232, 249, 255) if j == k - 1 else (245, 245, 255, 255)
        d.text((x, y), w, font=fnt, fill=col)
    return layer


def make_chips(i, n):
    chips = []
    for text, right in ((f"SCENE {i + 1} / {n}", False), ("STUDY BUDDY", True)):
        fnt = font(24)
        tw = ImageDraw.Draw(Image.new("RGB", (5, 5))).textlength(text, font=fnt)
        w, h = int(tw + 44), 46
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=23, fill=(8, 8, 18, 190))
        d.text((22, 8), text, font=fnt, fill=(220, 220, 255, 255))
        chips.append((layer, (W - 36 - w) if right else 36, 30))
    return chips


def word_times(words, dur):
    weights = [len(w) + 2 for w in words]
    tot, acc, times = sum(weights), 0, []
    for wgt in weights:
        times.append(LEAD + acc / tot * dur * 0.95)
        acc += wgt
    return times


# ------------------------------------------------------------------ main
def make_video(client, models, topic, n_scenes, voice="en-IN-NeerjaNeural", progress=None):
    """Return (mp4 bytes, scenes, info)."""
    def step(frac, msg):
        if progress:
            progress(min(max(frac, 0.0), 1.0), msg)

    step(0.02, "Writing the script...")
    title, scenes = make_script(client, models, topic, n_scenes)
    n = len(scenes)
    info = {"title": title, "fallback_images": 0, "voice_engine": "edge"}

    with tempfile.TemporaryDirectory() as tmp:
        assets = []
        for i, sc in enumerate(scenes):
            base = 0.05 + 0.5 * i / n
            step(base, f"Scene {i + 1} of {n}: drawing the illustration...")
            img, ok = get_image(sc.get("image_prompt") or topic, i)
            if not ok:
                info["fallback_images"] += 1
            step(base + 0.25 / n, f"Scene {i + 1} of {n}: recording the voice...")
            mp3 = os.path.join(tmp, f"s{i}.mp3")
            wav_path = os.path.join(tmp, f"s{i}.wav")
            if synth(sc["narration"], voice, mp3) != "edge":
                info["voice_engine"] = "basic"
            to_wav(mp3, wav_path)
            speech = read_wav(wav_path)
            assets.append((img, speech, len(speech) / 2 / RATE, sc["narration"]))

        step(0.57, "Mixing the audio...")
        audio = bytearray(silence(INTRO_FRAMES / FPS))
        frames_per = []
        for img, speech, dur, _ in assets:
            nf = int(math.ceil((LEAD + dur + TAIL) * FPS))
            audio += silence(LEAD) + speech + silence(nf / FPS - LEAD - dur)
            frames_per.append(nf)
        audio += silence(OUTRO_FRAMES / FPS)
        audio_path = os.path.join(tmp, "audio.wav")
        with wave.open(audio_path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(bytes(audio))

        total = INTRO_FRAMES + sum(frames_per) + OUTRO_FRAMES
        out = os.path.join(tmp, "final.mp4")
        log = os.path.join(tmp, "ffmpeg.log")
        logf = open(log, "wb")
        proc = subprocess.Popen(
            [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-framerate", str(FPS), "-i", "-", "-i", audio_path,
             "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", "-shortest", out],
            stdin=subprocess.PIPE, stderr=logf, stdout=subprocess.DEVNULL,
        )
        counter = {"n": 0}
        state = {"last": None}
        black = Image.new("RGB", (W, H))

        def emit(frame):
            d = ImageDraw.Draw(frame)
            d.rectangle((0, H - 6, int(W * counter["n"] / total), H), fill=(139, 92, 246))
            try:
                proc.stdin.write(frame.tobytes())
            except Exception:
                raise RuntimeError("The video encoder stopped unexpectedly.")
            counter["n"] += 1
            state["last"] = frame
            if counter["n"] % 12 == 0:
                pct = int(100 * counter["n"] / total)
                step(0.58 + 0.40 * counter["n"] / total, f"Rendering the video... {pct}%")

        try:
            # intro
            bg0 = fancy_bg(0)
            for f in range(INTRO_FRAMES):
                fr = card_frame(bg0, f, INTRO_FRAMES, "EXPLAINER VIDEO", title, "Made with Study Buddy")
                if f < FADE:
                    fr = Image.blend(black, fr, ease((f + 1) / FADE))
                emit(fr)

            # scenes
            for i, (img, speech, dur, text) in enumerate(assets):
                nf = frames_per[i]
                words = text.split()
                times = word_times(words, dur)
                items, size, pos = build_layout(text)
                chips = make_chips(i, n)
                cache = {}
                vig = vignette()
                for f in range(nf):
                    t = f / FPS
                    frame = img.resize((W, H), RESAMPLE, box=kb_box(i % 4, f / max(1, nf - 1)))
                    frame.paste(vig, (0, H - vig.size[1]), vig)
                    k = sum(1 for tt in times if tt <= t)
                    if k > 0:
                        if k not in cache:
                            cache[k] = make_overlay(items, size, k)
                        frame.paste(cache[k], pos, cache[k])
                    for layer, cx, cy in chips:
                        frame.paste(layer, (cx, cy), layer)
                    if f < FADE and state["last"] is not None:
                        frame = Image.blend(state["last"], frame, ease((f + 1) / FADE))
                    emit(frame)

            # outro
            bg1 = fancy_bg(1)
            for f in range(OUTRO_FRAMES):
                fr = card_frame(bg1, f, OUTRO_FRAMES, "", "Thanks for watching!",
                                "Keep learning with Study Buddy", fade_out=True)
                if f < FADE and state["last"] is not None:
                    fr = Image.blend(state["last"], fr, ease((f + 1) / FADE))
                emit(fr)
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            code = proc.wait()
            logf.close()

        if code != 0:
            with open(log, "rb") as lf:
                tail = lf.read()[-300:].decode("utf-8", "ignore")
            raise RuntimeError("Video encoder failed: " + tail)

        with open(out, "rb") as f:
            data = f.read()

    step(1.0, "Done!")
    return data, scenes, info