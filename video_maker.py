import requests
import json
import subprocess
import os

# ========== تنظیمات با کلید جدید و مدل درست ==========
GEMINI_API_KEY = "AQ.Ab8RN6LeFukS_hT6DuONe8rg36Ci0JNhOftjLLItyePKYPSrnA"  # کلید جدید
TOPIC = "چرا انسان‌ها به موسیقی نیاز دارند؟"

def get_script_from_gemini(topic):
    """گرفتن فیلمنامه از Gemini با کلید جدید و مدل درست"""
    # استفاده از مدلی که در curl کار کرد
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY  # کلید در هدر
    }
    
    prompt = f"""یک فیلمنامه کوتاه ۳۰ ثانیه‌ای برای یوتیوب شورت درباره '{topic}' بنویس.
    فیلمنامه را به ۳ بخش (صحنه) تقسیم کن. هر بخش شامل:
    1. متن گفتار (حداکثر ۱۵ کلمه)
    2. توضیح صحنه برای ساخت تصویر
    
    خروجی دقیقاً به این فرمت JSON باشه (فقط همین JSON، هیچ توضیح اضافه‌ای قبل و بعدش نباشه):
    {{"scenes": [
        {{"text": "متن گفتار صحنه ۱", "image_prompt": "توضیح صحنه ۱"}},
        {{"text": "متن گفتار صحنه ۲", "image_prompt": "توضیح صحنه ۲"}},
        {{"text": "متن گفتار صحنه ۳", "image_prompt": "توضیح صحنه ۳"}}
    ]}}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    print(f"📤 ارسال درخواست به {url}")
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"📥 وضعیت پاسخ: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ خطا: {response.text}")
        return None
    
    result = response.json()
    print(f"📄 پاسخ دریافت شد: {json.dumps(result, indent=2)[:500]}...")
    
    # بررسی وجود candidates
    if "candidates" not in result:
        print(f"❌ کلید 'candidates' در پاسخ وجود ندارد")
        print(f"پاسخ کامل: {json.dumps(result, indent=2)}")
        return None
    
    raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
    # پاک کردن markdown و استخراج JSON
    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

def generate_image(prompt, scene_num):
    """ساخت تصویر با Pollinations AI"""
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    response = requests.get(url)
    filename = f"scene_{scene_num}.jpg"
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

def generate_audio(text, scene_num):
    """ساخت صدا با استفاده از فرضی (در GitHub Actions نیاز به نصب edge-tts دارد)"""
    filename = f"audio_{scene_num}.mp3"
    try:
        subprocess.run(["edge-tts", "--text", text, "--voice", "ir-IR-DilaraNeural", "--write-media", filename], check=True, capture_output=True)
    except:
        # اگر edge-tts نصب نیست، یک فایل صوتی خالی بساز
        subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "sine=frequency=1000:duration=3", filename], capture_output=True)
    return filename

def create_video(image_files, audio_files, output_name="final_video.mp4"):
    """ترکیب تصاویر و صداها"""
    with open("concat_list.txt", "w") as f:
        for img, aud in zip(image_files, audio_files):
            try:
                result = subprocess.run(["ffprobe", "-i", aud, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=%s"], capture_output=True, text=True)
                duration = result.stdout.strip()
                if not duration:
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
    print("📝 گرفتن فیلمنامه از Gemini...")
    script = get_script_from_gemini(TOPIC)
    
    if script is None:
        print("❌ خطا در دریافت فیلمنامه، خروج...")
        exit(1)
    
    images = []
    audios = []
    
    for i, scene in enumerate(script["scenes"]):
        print(f"🎨 ساخت تصویر صحنه {i+1}...")
        img = generate_image(scene["image_prompt"], i+1)
        images.append(img)
        
        print(f"🔊 ساخت صدا صحنه {i+1}...")
        aud = generate_audio(scene["text"], i+1)
        audios.append(aud)
    
    print("🎬 ساخت ویدیو نهایی...")
    video_file = create_video(images, audios)
    print(f"✅ ویدیو ساخته شد: {video_file}")
