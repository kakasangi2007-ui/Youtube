import requests
import json
import subprocess
import os
import time
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# ========== تنظیمات بهینه ==========
GEMINI_API_KEY = "AQ.Ab8RN6LeFukS_hT6DuONe8rg36Ci0JNhOftjLLItyePKYPSrnA"
# استفاده از بهینه‌ترین مدل برای لایه رایگان
MODEL_NAME = "gemini-2.5-flash-lite"
TOPIC = "چرا انسان‌ها به موسیقی نیاز دارند؟"

def log_message(message, type="info"):
    """چاپ پیام با فرمت مناسب"""
    prefix = {"info": "📝", "success": "✅", "error": "❌", "warning": "⚠️"}.get(type, "📌")
    print(f"{prefix} {message}")

# دکوراتور retry برای مدیریت خودکار خطاهای 429 و 503
@retry(
    stop=stop_after_attempt(5),  # حداکثر 5 بار تلاش
    wait=wait_exponential(multiplier=1, min=2, max=30),  # فاصله افزایشی: 2، 4، 8، 16، 30 ثانیه
    retry=retry_if_exception(lambda e: isinstance(e, requests.exceptions.RequestException) and 
                             e.response is not None and e.response.status_code in [429, 503]),
    reraise=True
)
def call_gemini_api(prompt):
    """ارسال درخواست به Gemini API با مدیریت خودکار خطا"""
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
    
    log_message(f"ارسال درخواست به {MODEL_NAME}...")
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code in [429, 503]:
        log_message(f"خطای {response.status_code}: ازدحام سرور. تلاش مجدد...", "warning")
        response.raise_for_status()
    else:
        log_message(f"خطای ناشناخته {response.status_code}: {response.text}", "error")
        response.raise_for_status()

def get_script_from_gemini(topic):
    """گرفتن فیلمنامه با مدیریت خطا"""
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
    
    try:
        result = call_gemini_api(prompt)
        
        if "candidates" not in result or not result["candidates"]:
            log_message("پاسخ API فاقد محتوای معتبر است", "error")
            return None
            
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
        clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
        
    except requests.exceptions.RequestException as e:
        log_message(f"خطا در ارتباط با API: {e}", "error")
        return None
    except json.JSONDecodeError as e:
        log_message(f"خطا در پردازش JSON: {e}", "error")
        return None
    except Exception as e:
        log_message(f"خطای پیش‌بینی‌نشده: {e}", "error")
        return None

def generate_image(prompt, scene_num):
    """ساخت تصویر با Pollinations AI"""
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    response = requests.get(url)
    filename = f"scene_{scene_num}.jpg"
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

def generate_audio(text, scene_num):
    """ساخت صدا با استفاده از edge-tts"""
    filename = f"audio_{scene_num}.mp3"
    try:
        subprocess.run(["edge-tts", "--text", text, "--voice", "ir-IR-DilaraNeural", "--write-media", filename], 
                      check=True, capture_output=True)
        log_message(f"صدای صحنه {scene_num} ساخته شد", "success")
    except:
        log_message(f"عدم دسترسی به edge-tts، استفاده از صدای پیش‌فرض", "warning")
        subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", filename], capture_output=True)
    return filename

def create_video(image_files, audio_files, output_name="final_video.mp4"):
    """ترکیب تصاویر و صداها با FFmpeg"""
    with open("concat_list.txt", "w") as f:
        for img, aud in zip(image_files, audio_files):
            try:
                result = subprocess.run(["ffprobe", "-i", aud, "-show_entries", "format=duration", 
                                       "-v", "quiet", "-of", "csv=%s"], capture_output=True, text=True)
                duration = result.stdout.strip()
                if not duration or float(duration) <= 0:
                    duration = "3"
            except:
                duration = "3"
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration}\n")
    
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", output_name
    ], capture_output=True)
    return output_name

if __name__ == "__main__":
    log_message(f"شروع ساخت ویدیو با مدل {MODEL_NAME}")
    log_message(f"گرفتن فیلمنامه از Gemini API...")
    
    script = get_script_from_gemini(TOPIC)
    
    if script is None:
        log_message("خطا در دریافت فیلمنامه، خروج از برنامه", "error")
        exit(1)
    
    log_message("فیلمنامه با موفقیت دریافت شد", "success")
    
    images = []
    audios = []
    
    for i, scene in enumerate(script["scenes"]):
        log_message(f"ساخت صحنه {i+1} از {len(script['scenes'])}")
        
        log_message(f"ساخت تصویر برای: {scene['image_prompt'][:50]}...")
        img = generate_image(scene["image_prompt"], i+1)
        images.append(img)
        
        log_message(f"ساخت صدا برای: {scene['text'][:50]}...")
        aud = generate_audio(scene["text"], i+1)
        audios.append(aud)
    
    log_message("ترکیب نهایی ویدیو...")
    video_file = create_video(images, audios)
    
    log_message(f"ویدیو با موفقیت ساخته شد: {video_file}", "success")
    log_message("فایل‌های ساخته شده:", "info")
    for file in images + audios + [video_file]:
        if os.path.exists(file):
            size = os.path.getsize(file) / 1024
            log_message(f"  - {file} ({size:.1f} KB)", "info")
