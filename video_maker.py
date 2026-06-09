import requests
import json
import subprocess
import os
import re
import glob
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# ========== CONFIG ==========
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"
TOPIC = "چرا انسان‌ها به موسیقی نیاز دارند؟"

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = f"output_{RUN_ID}"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ========== LOG ==========
def log(msg):
    print("📝", msg)


# ========== CLEAN OLD RUNS (optional safe mode) ==========
def clean_old_outputs(keep_last=3):
    folders = sorted(glob.glob("output_*"))

    if len(folders) <= keep_last:
        return

    for folder in folders[:-keep_last]:
        try:
            subprocess.run(["rm", "-rf", folder])
            print(f"🧹 حذف شد: {folder}")
        except:
            pass


# ========== GEMINI ==========
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(min=2, max=30),
    retry=retry_if_exception(lambda e: isinstance(e, requests.exceptions.RequestException)),
    reraise=True
)
def gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1200
        }
    }

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()


def extract_json(text):
    match = re.search(r'\{.*\}', text, re.S)
    if not match:
        raise ValueError("JSON not found")
    return json.loads(match.group())


def get_script(topic):
    prompt = f"""
یک ویدیو 30 ثانیه‌ای درباره "{topic}" بساز.
3 صحنه.

فقط JSON:
{{
"scenes":[
{{"text":"کوتاه و جذاب","image_prompt":"تصویر سینمایی"}},
{{"text":"کوتاه و جذاب","image_prompt":"تصویر سینمایی"}},
{{"text":"کوتاه و جذاب","image_prompt":"تصویر سینمایی"}}
]
}}
"""

    res = gemini(prompt)
    txt = res["candidates"][0]["content"]["parts"][0]["text"]

    txt = txt.replace("```json","").replace("```","").strip()
    return extract_json(txt)


# ========== IMAGE ==========
def make_image(prompt, i):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    r = requests.get(url, timeout=60)
    r.raise_for_status()

    file_path = os.path.join(OUTPUT_DIR, f"img_{i}.jpg")

    with open(file_path, "wb") as f:
        f.write(r.content)

    return file_path


# ========== AUDIO ==========
def make_audio(text, i):
    file_path = os.path.join(OUTPUT_DIR, f"audio_{i}.mp3")

    try:
        subprocess.run([
            "edge-tts",
            "--text", text,
            "--voice", "en-US-AriaNeural",
            "--write-media", file_path
        ], check=True)

    except:
        subprocess.run([
            "ffmpeg","-y",
            "-f","lavfi",
            "-i","sine=frequency=500:duration=3",
            file_path
        ])

    return file_path


# ========== CLIP ==========
def make_clip(img, aud, i):
    out = os.path.join(OUTPUT_DIR, f"clip_{i}.mp4")

    subprocess.run([
        "ffmpeg","-y",
        "-loop","1",
        "-i", img,
        "-i", aud,
        "-vf","scale=1080:1920,format=yuv420p",
        "-c:v","libx264",
        "-c:a","aac",
        "-shortest",
        out
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return out


# ========== CONCAT ==========
def concat_clips(clips):
    list_file = os.path.join(OUTPUT_DIR, "list.txt")

    with open(list_file, "w") as f:
        for c in clips:
            f.write(f"file '{c}'\n")

    output = os.path.join(OUTPUT_DIR, "temp.mp4")

    subprocess.run([
        "ffmpeg","-y",
        "-f","concat",
        "-safe","0",
        "-i", list_file,
        "-c","copy",
        output
    ])

    return output


# ========== FINAL ==========
def finalize(video):
    out = os.path.join(OUTPUT_DIR, "final_short.mp4")

    music = "music.mp3"

    if not os.path.exists(music):
        subprocess.run([
            "ffmpeg","-y",
            "-f","lavfi",
            "-i","sine=frequency=0:duration=10",
            music
        ])

    subprocess.run([
        "ffmpeg","-y",
        "-i", video,
        "-i", music,
        "-filter_complex",
        "[1:a]volume=0.08[a1];[0:a][a1]amix=inputs=2:duration=first",
        "-c:v","copy",
        "-c:a","aac",
        out
    ])

    return out


# ========== MAIN ==========
if __name__ == "__main__":
    log(f"شروع اجرا: {RUN_ID}")

    clean_old_outputs()

    script = get_script(TOPIC)

    clips = []

    for i, scene in enumerate(script["scenes"], 1):
        log(f"صحنه {i}")

        img = make_image(scene["image_prompt"], i)
        aud = make_audio(scene["text"], i)

        clip = make_clip(img, aud, i)
        clips.append(clip)

    video = concat_clips(clips)
    final = finalize(video)

    log(f"ویدیو ساخته شد: {final}")
    log(f"پوشه خروجی: {OUTPUT_DIR}")
