import requests
import json

# ========== تنظیمات ==========
GEMINI_API_KEY = "AQ.Ab8RN6LYeHoRBstrchXminjQYiv9lI85SPdFY4-hh98ATdzO6g"

# روش 1: استفاده از HEADER (مطابق مستندات رسمی گوگل)
def test_with_header():
    print("\n" + "="*50)
    print("روش 1: ارسال کلید در HEADER (X-goog-api-key)")
    print("="*50)
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Say exactly this: Hello World"
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nFull Response Text:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# روش 2: استفاده از ?key= در URL (روش قدیمی)
def test_with_url_param():
    print("\n" + "="*50)
    print("روش 2: ارسال کلید در URL (?key=)")
    print("="*50)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Say exactly this: Hello World"
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"\nFull Response Text:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# روش 3: با مدل gemini-1.5-flash (پایدارتر)
def test_with_stable_model():
    print("\n" + "="*50)
    print("روش 3: استفاده از مدل gemini-1.5-flash (پایدارتر)")
    print("="*50)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": "Say exactly this: Hello World"
                    }
                ]
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"\nFull Response Text:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))

# روش 4: بدون API (تست اینترنت)
def test_internet():
    print("\n" + "="*50)
    print("روش 4: تست اتصال اینترنت و DNS")
    print("="*50)
    
    try:
        response = requests.get("https://generativelanguage.googleapis.com", timeout=5)
        print(f"✅ اتصال به سرور گوگل برقرار است. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ خطای اتصال: {e}")

if __name__ == "__main__":
    print(f"🔑 کلید API: {GEMINI_API_KEY[:20]}... (بخش اول)")
    print(f"📏 طول کلید: {len(GEMINI_API_KEY)} کاراکتر")
    
    test_internet()
    test_with_header()
    test_with_url_param()
    test_with_stable_model()
