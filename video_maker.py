import requests
import json
import subprocess
import os
import base64

GEMINI_API_KEY = "AQ.Ab8RN6LYeHoRBstrchXminjQYiv9lI85SPdFY4-hh98ATdzO6g"
TOPIC = "چرا انسان‌ها به موسیقی نیاز دارند؟"

def get_script_from_gemini(topic):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""یک فیلمنامه کوتاه ۳۰ ثانیه‌ای برای یوتیوب شورت درباره '{topic}' بنویس.
    فیلمنامه را به ۳ بخش (صحنه) تقسیم کن. هر بخش شامل:
    1. متن گفتار (حداکثر ۱۵ کلمه)
    2. توضیح صحنه برای ساخت تصویر
    خروجی دقیقاً به این فرمت JSON باشه:
    {{"scenes": [
        {{"text": "متن گفتار صحنه ۱", "image_prompt": "توضیح صحنه ۱"}},
        {{"text": "متن گفتار صحنه ۲", "image_prompt": "توضیح صحنه ۲"}},
        {{"text": "متن گفتار صحنه ۳", "image_prompt": "توضیح صحنه ۳"}}
    ]}}
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=payload)
    result = response.json()
    raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
    clean_json = raw_text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

def generate_image(prompt, scene_num):
    url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
    response = requests.get(url)
    filename = f"scene_{scene_num}.jpg"
    with open(filename, "wb") as f:
        f.write(response.content)
    return filename

def generate_audio(text, scene_num):
    filename = f"audio_{scene_num}.mp3"
    # روش جایگزین بدون edge-tts برای گیت‌هاب
    # موقتاً یه فایل صوتی خالی می‌سازیم (برای تست)
    subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "sine=frequency=1000:duration=3", filename], capture_output=True)
    return filename

def create_video(image_files, audio_files, output_name="final_video.mp4"):
    with open("concat_list.txt", "w") as f:
        for img, aud in zip(image_files, audio_files):
            # با ffprobe duration رو بگیر
            result = subprocess.run(["ffprobe", "-i", aud, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=%s"], capture_output=True, text=True)
            duration = result.stdout.strip()
            if not duration:
                duration = "3"
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration}\n")
    
    subprocess.run([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", "concat_list.txt",
        "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", output_name
    ], capture_output=True)
    return output_name

def upload_to_github(file_path):
    """ذخیره ویدیو در گیت‌هاب (به عنوان یک فایل معمولی)"""
    # فقط فایل رو به گیت اضافه می‌کنیم (توی workflow بعداً commit می‌کنیم)
    print(f"✅ ویدیو ساخته شد: {file_path}")
    return file_path

if __name__ == "__main__":
    print("📝 گرفتن فیلمنامه از Gemini...")
    script = get_script_from_gemini(TOPIC)
    
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
    
    # ذخیره در مخزن
    upload_to_github(video_file)
    print(f"✅ همه چیز تموم! فایل {video_file} توی مخزن ذخیره شد.")
    
    # نمایش لینک فایل
    import os
    print(f"\n🔗 فایل رو می‌تونی اینجا ببینی: {os.path.abspath(video_file)}")
