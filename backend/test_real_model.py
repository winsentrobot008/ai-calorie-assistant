"""
Real Model Test Script — calls the analyze-image endpoint and prints
model source, confidence, weight estimation, and calories for each item.
"""
import requests
import io
import os
from PIL import Image, ImageDraw

API = "http://localhost:8001"

def make_test_image(filename="test_food.jpg"):
    """Generate a realistic-looking food test image."""
    img = Image.new("RGB", (800, 600), (255, 240, 220))  # warm background
    draw = ImageDraw.Draw(img)
    # Main food blob
    draw.ellipse([200, 100, 600, 450], fill=(180, 80, 40))  # burger-like
    draw.ellipse([300, 250, 500, 420], fill=(60, 140, 60))   # veggie layer
    draw.rectangle([250, 80, 550, 120], fill=(200, 180, 140)) # bun top
    # Side items
    draw.ellipse([100, 400, 300, 550], fill=(240, 200, 60))  # fries
    draw.ellipse([500, 420, 700, 560], fill=(60, 120, 60))   # salad
    img.save(filename, "JPEG", quality=92)
    return filename

def test_real_model():
    """Main test flow."""
    print("=" * 60)
    print("  🧪 REAL MODEL TEST")
    print("  Verifying: VISION_MODE=real pipeline")
    print("=" * 60)

    # Check VISION_MODE from env
    vision_mode = os.getenv("VISION_MODE", "not set")
    ai_key = "✅ SET" if os.getenv("AI_API_KEY") and os.getenv("AI_API_KEY") != "你的大模型密钥" else "❌ placeholder"
    hf_key = "✅ SET" if os.getenv("HF_API_KEY") and os.getenv("HF_API_KEY") != "你的 HuggingFace 密钥" else "❌ placeholder"

    print(f"\n  ├─ VISION_MODE:    {vision_mode}")
    print(f"  ├─ AI_API_KEY:     {ai_key}")
    print(f"  ├─ HF_API_KEY:     {hf_key}")
    print(f"  └─ HF_MODEL:       {os.getenv('HF_MODEL', 'nateraw/food101')}")

    # Create test image
    filename = make_test_image()
    file_size = os.path.getsize(filename)
    print(f"\n  📸 Test image: {filename} ({file_size // 1024} KB)")

    # Upload and analyze
    print(f"\n  🚀 Sending to /api/v1/meals/analyze-image ...\n")

    with open(filename, "rb") as f:
        files = {"file": (filename, f, "image/jpeg")}
        data = {"meal_type": "lunch", "lang": "zh"}
        r = requests.post(f"{API}/api/v1/meals/analyze-image", files=files, data=data)

    # ── Results ──
    print(f"  {'─' * 56}")
    print(f"  HTTP Status: {r.status_code}")
    print(f"  {'─' * 56}")

    if not r.ok:
        print(f"\n  ❌ Error: {r.text[:300]}")
        return

    data = r.json()
    records = data.get("records", [])
    image_path = data.get("image_path", "")

    print(f"\n  📋 Recognized {len(records)} food items:\n")

    for i, rec in enumerate(records, 1):
        food = rec.get("food", "?")
        food_en = rec.get("food_en", "")
        grams = rec.get("grams", 0)
        calories = rec.get("calories", 0)
        confidence = rec.get("confidence", "N/A")
        source_model = rec.get("source_model", "unknown")
        lang = rec.get("lang", "zh")
        protein = rec.get("protein_g", 0)
        fat = rec.get("fat_g", 0)
        carbs = rec.get("carbs_g", 0)

        print(f"  ┌─ Item #{i}")
        print(f"  ├─ Food:       {food}", end="")
        if food_en:
            print(f" ({food_en})", end="")
        print()
        print(f"  ├─ Source:     {source_model}")
        print(f"  ├─ Confidence: {confidence}")
        print(f"  ├─ Weight:     {grams}g")
        print(f"  ├─ Calories:   {calories} kcal")
        print(f"  ├─ Nutrition:  P{protein}g · F{fat}g · C{carbs}g")
        print(f"  └─ Lang:       {lang}")
        print()

    # Summary
    total_cal = sum(r["calories"] for r in records)
    models_used = set(r.get("source_model", "?") for r in records)
    print(f"  {'─' * 56}")
    print(f"  📊 SUMMARY")
    print(f"  {'─' * 56}")
    print(f"  Total items:     {len(records)}")
    print(f"  Total calories:  {total_cal:.0f} kcal")
    print(f"  Models used:     {', '.join(sorted(models_used))}")
    print(f"  Image saved at:  {image_path}")
    print(f"  {'─' * 56}")

    # Clean up test image
    os.remove(filename)
    print(f"\n  🧹 Cleaned up {filename}")
    print(f"\n  ✅ Test complete!")


if __name__ == "__main__":
    test_real_model()
