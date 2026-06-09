import requests
import json
import subprocess
import os
import time
from datetime import datetime

# ========== تنظیمات با کلیدی که کار می‌کرد ==========
GEMINI_API_KEY = "AQ.Ab8RN6LeFukS_hT6DuONe8rg36Ci0JNhOftjLLItyePKYPSrnA"
MODEL_NAME = "gemini-2.0-flash-lite"
TOPIC = "چرا انسان‌ها به موسیقی نیاز دارند؟"

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_DIR = f"output_{RUN_ID}"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def log_message(message, type="info"):
    prefix = {"info": "📝", "success": "✅", "error": "❌", "warning": "⚠️", "video": "🎬", "image": "🎨", "audio": "🔊"}.get(type, "📌")
    print(f"{prefix} {message}")

def call_gemini_api_with_retry(prompt, max_retries=5):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024
        }
    }
    
    for attempt in range(max_retries):
        try:
            log_message(f"ارسال درخواست (تلاش {attempt + 1}/{max_retries})...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [429, 503]:
                wait_time = (2 ** attempt)
                log_message(f"خطای {response.status_code}: انتظار {wait_time} ثانیه...", "warning")
                time.sleep(wait_time)
            else:
                log_message(f"خطای {response.status_code}: {response.text}", "error")
                return None
                
        except requests.exceptions.RequestException as e:
            log_message(f"خطای شبکه: {e}", "error")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None
    
    return None

def get_script_from_gemini(topic):
    prompt = f"""یک فیلمنامه کوتاه ۳۰ ثانیه‌ای برای یوتیوب شورت درباره '{topic}' بنویس.
    فیلمنامه را به ۳ بخش (صحنه) تقسیم کن. هر بخش شامل:
    1. متن گفتار (حداکثر ۱۵ کلمه)
    2. توضیح صحنه برای ساخت تصویر
    
    خروجی دقیقاً به این فرمت JSON باشه (فقط همین JSON):
    {{"scenes": [
        {{"text": "متن گفتار صحنه ۱", "image_prompt": "توضیح صحنه ۱"}},
        {{"text": "متن گفتار صحنه ۲", "image_prompt": "توضیح صحنه ۲"}},
        {{"text": "متن گفتار صحنه ۳", "image_prompt": "توضیح صحنه ۳"}}
    ]}}
    """
    
    result = call_gemini_api_with_retry(prompt)
    
    if result is None:
        return None
        
    if "candidates" not in result or not result["candidates"]:
        log_message("پاسخ API فاقد محتوای معتبر است", "error")
        return None
        
    raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

def generate_image(prompt, scene_num):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    response = requests.get(url)
    filename = os.path.join(OUTPUT_DIR, f"img_{scene_num}.jpg")
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

def generate_audio(text, scene_num):
    filename = os.path.join(OUTPUT_DIR, f"audio_{scene_num}.mp3")
    try:
        subprocess.run([
            "edge-tts", "--text", text, "--voice", "ir-IR-DilaraNeural",
            "--write-media", filename
        ], check=True, capture_output=True)
    except:
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration=3",
            filename
        ], capture_output=True)
    return filename

def create_video(image_files, audio_files):
    clips = []
    
    for i, (img, aud) in enumerate(zip(image_files, audio_files), 1):
        clip_file = os.path.join(OUTPUT_DIR, f"clip_{i}.mp4")
        
        try:
            result = subprocess.run(["ffprobe", "-i", aud, "-show_entries", "format=duration",
                                   "-v", "quiet", "-of", "csv=%s"], capture_output=True, text=True)
            duration = result.stdout.strip()
            if not duration or float(duration) <= 0:
                duration = "4"
        except:
            duration = "4"
        
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", img, "-i", aud,
            "-vf", "scale=1080:1920,format=yuv420p",
            "-c:v", "libx264", "-c:a", "aac", "-shortest",
            "-t", duration, clip_file
        ], capture_output=True)
        clips.append(clip_file)
    
    list_file = os.path.join(OUTPUT_DIR, "concat_list.txt")
    with open(list_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip}'\n")
    
    output_file = os.path.join(OUTPUT_DIR, "final_video.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output_file
    ], capture_output=True)
    
    return output_file

if __name__ == "__main__":
    log_message(f"شروع ساخت ویدیو - {RUN_ID}", "video")
    
    script = get_script_from_gemini(TOPIC)
    
    if script is None:
        log_message("خطا در دریافت فیلمنامه، خروج از برنامه", "error")
        exit(1)
    
    log_message(f"فیلمنامه دریافت شد - {len(script['scenes'])} صحنه", "success")
    
    images = []
    audios = []
    
    for i, scene in enumerate(script["scenes"], 1):
        log_message(f"ساخت صحنه {i}: {scene['text'][:50]}...")
        
        img = generate_image(scene["image_prompt"], i)
        images.append(img)
        
        aud = generate_audio(scene["text"], i)
        audios.append(aud)
    
    log_message("ترکیب نهایی ویدیو...")
    video_file = create_video(images, audios)
    
    if os.path.exists(video_file):
        file_size = os.path.getsize(video_file) / (1024 * 1024)
        log_message(f"ویدیو با موفقیت ساخته شد: {video_file}", "success")
        log_message(f"حجم فایل: {file_size:.2f} MB", "info")
    else:
        log_message("خطا در ساخت ویدیو", "error")
        exit(1)
