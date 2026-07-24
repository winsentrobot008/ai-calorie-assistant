"""
AI Vision Service — multi-language food recognition with HuggingFace fallback.

Pipeline:
  1. Full-image pass (Vision API)  —  returns zh labels + confidence
  2. Grid-crop 2×2 + per-region    —  same format
  3. HuggingFace food-classifier    —  maps Food-101 en labels → 5 languages
  4. Mock fallback

Output format per item:
  {"food": "包子", "food_en": "Steamed Bun", "estimated_grams": 200,
   "description": "baozi", "notes": "HF confidence: 0.95", "confidence": 0.95,
   "source_model": "food101-vit-base", "lang": "zh"}
"""
import os
import asyncio
import base64
import json
import logging
import io
from PIL import Image
import httpx

logger = logging.getLogger(__name__)

def _env(key: str, default: str = "") -> str:
    """Read env var dynamically (not cached at module import)."""
    return os.getenv(key, default)

def AI_API_BASE_URL(): return _env("AI_API_BASE_URL", "https://api.lk888.ai")
def AI_API_KEY(): return _env("AI_API_KEY", "")
def AI_MODEL(): return _env("AI_MODEL", "gpt-4o")
def HF_API_KEY(): return _env("HF_API_KEY", "")
def HF_MODEL(): return _env("HF_MODEL", "nateraw/food101")
def VISION_MODE(): return _env("VISION_MODE", "fallback")

# ── Prompts ──
FULL_IMAGE_PROMPT = (
    "You are a food recognition assistant. Identify ALL visible foods in this image, "
    "each as a SEPARATE item. Do NOT combine them into one entry. "
    "Return ONLY valid JSON array with NO markdown formatting, NO code fences:\n"
    '[{"food": "food name in Chinese", "food_en": "English name", '
    '"description": "brief appearance", "estimated_grams": number}]\n'
    "Include food_en for every item. "
    "Estimate grams: 一个汉堡≈200g, 一份薯条≈120g, 一杯饮料≈250ml, "
    "一碗饭≈200g, 一块肉≈150g, 一盘菜≈200g."
)

REGION_PROMPT = (
    "Identify the main food visible in this image region. "
    "Return ONLY a JSON array:\n"
    '[{"food": "food name in Chinese", "food_en": "English name", '
    '"description": "appearance", "estimated_grams": number}]\n'
    "If no food is visible, return []."
)

# ── Food-101 → Multi-language Mapping (101 classes, 5 languages) ──
# Format: label: (zh, ja, hi, es, default_grams)
FOOD101_MULTILANG: dict[str, tuple] = {
    # Western fast-food
    "hamburger":          ("汉堡", "ハンバーガー", "हैमबर्गर", "Hamburguesa", 200),
    "cheeseburger":       ("芝士汉堡", "チーズバーガー", "चीज़बर्गर", "Hamburguesa con queso", 220),
    "hot_dog":            ("热狗", "ホットドッグ", "हॉट डॉग", "Perro caliente", 180),
    "pizza":              ("披萨", "ピザ", "पिज़्ज़ा", "Pizza", 250),
    "french_fries":       ("薯条", "フライドポテト", "फ्रेंच फ्राइज़", "Papas fritas", 120),
    # Asian
    "fried_rice":         ("炒饭", "チャーハン", "फ्राइड राइस", "Arroz frito", 250),
    "rice":               ("米饭", "ご飯", "चावल", "Arroz", 200),
    "sushi":              ("寿司", "寿司", "सुशी", "Sushi", 180),
    "spring_rolls":       ("春卷", "春巻き", "स्प्रिंग रोल", "Rollitos de primavera", 150),
    "dumplings":          ("饺子", "餃子", "पकौड़े", "Empanadillas", 200),
    "samosa":             ("咖喱角", "サモサ", "समोसा", "Samosa", 150),
    "ramen":              ("拉面", "ラーメン", "रामेन", "Ramen", 350),
    "pho":                ("越南河粉", "フォー", "फ़ो", "Pho", 400),
    "noodles":            ("面条", "麺類", "नूडल्स", "Fideos", 300),
    "wontons":            ("馄饨", "ワンタン", "वॉन्टन", "Wantán", 250),
    "chicken_curry":      ("咖喱鸡", "チキンカレー", "चिकन करी", "Curry de pollo", 250),
    "chicken_wings":      ("鸡翅", "手羽先", "चिकन विंग्स", "Alitas de pollo", 200),
    "fried_chicken":      ("炸鸡", "フライドチキン", "फ्राइड चिकन", "Pollo frito", 200),
    "chicken_quesadilla": ("鸡肉卷", "チキンケサディーヤ", "चिकन क्यूसडिला", "Quesadilla de pollo", 200),
    "beef_tartare":       ("牛肉塔塔", "ビフテキタルタル", "बीफ़ टार्टारे", "Tártara de res", 150),
    "steak":              ("牛排", "ステーキ", "स्टेक", "Bistec", 250),
    "bbq_ribs":           ("烤排骨", "バーベキューリブ", "बीबीक्यू रिब्स", "Costillas BBQ", 250),
    "pork_chop":          ("猪排", "ポークチョップ", "पोर्क चॉप", "Chuleta de cerdo", 200),
    "grilled_salmon":     ("烤三文鱼", "サーモングリル", "ग्रिल्ड सैल्मन", "Salmón a la parrilla", 200),
    "fish_and_chips":     ("炸鱼薯条", "フィッシュアンドチップス", "फिश ऐंड चिप्स", "Pescado con papas", 300),
    # Salads
    "caesar_salad":       ("凯撒沙拉", "シーザーサラダ", "सीज़र सलाद", "Ensalada César", 200),
    "greek_salad":        ("希腊沙拉", "ギリシャサラダ", "ग्रीक सलाद", "Ensalada griega", 200),
    "fruit_salad":        ("水果沙拉", "フルーツサラダ", "फलों का सलाद", "Ensalada de frutas", 200),
    "coleslaw":           ("卷心菜沙拉", "コールスロー", "कोलस्ला", "Ensalada de col", 150),
    "beet_salad":         ("甜菜沙拉", "ビートサラダ", "चुकंदर सलाद", "Ensalada de remolacha", 180),
    # Breakfast
    "french_toast":       ("法式吐司", "フレンチトースト", "फ्रेंच टोस्ट", "Tostada francesa", 150),
    "pancakes":           ("松饼", "パンケーキ", "पैनकेक", "Panqueques", 200),
    "waffles":            ("华夫饼", "ワッフル", "वफ़ल", "Gofres", 180),
    "omelette":           ("煎蛋卷", "オムレツ", "ऑमलेट", "Tortilla francesa", 200),
    "fried_egg":          ("煎蛋", "目玉焼き", "तला हुआ अंडा", "Huevo frito", 100),
    "scrambled_eggs":     ("炒蛋", "スクランブルエッグ", "स्क्रैम्बल्ड एग", "Huevos revueltos", 150),
    "eggs_benedict":      ("班尼迪克蛋", "エッグベネディクト", "एग्स बेनेडिक्ट", "Huevos Benedictinos", 250),
    # Desserts & bakery
    "ice_cream":          ("冰淇淋", "アイスクリーム", "आइसक्रीम", "Helado", 150),
    "cup_cakes":          ("纸杯蛋糕", "カップケーキ", "कपकेक", "Pastelito", 100),
    "donuts":             ("甜甜圈", "ドーナツ", "डोनट", "Dona", 100),
    "apple_pie":          ("苹果派", "アップルパイ", "एप्पल पाई", "Pastel de manzana", 180),
    "creme_brulee":       ("焦糖布丁", "クレームブリュレ", "क्रेम ब्रूली", "Crema quemada", 150),
    "cheese_plate":       ("芝士拼盘", "チーズ盛り合わせ", "चीज़ प्लेट", "Tabla de quesos", 200),
    "bread_pudding":      ("面包布丁", "ブレッドプディング", "ब्रेड पुडिंग", "Budín de pan", 200),
    "chocolate_cake":     ("巧克力蛋糕", "チョコレートケーキ", "चॉकलेट केक", "Pastel de chocolate", 180),
    "cheesecake":         ("芝士蛋糕", "チーズケーキ", "चीज़केक", "Pastel de queso", 200),
    "tiramisu":           ("提拉米苏", "ティラミス", "तिरामिसु", "Tiramisú", 200),
    "brownies":           ("布朗尼", "ブラウニー", "ब्राउनी", "Brownie", 120),
    "churros":            ("西班牙油条", "チュロス", "चुरोस", "Churros", 150),
    "macarons":           ("马卡龙", "マカロン", "मैकरून", "Macarons", 100),
    # Soups
    "miso_soup":          ("味噌汤", "味噌汁", "मिसो सूप", "Sopa de miso", 200),
    "tomato_soup":        ("番茄汤", "トマトスープ", "टमाटर का सूप", "Sopa de tomate", 250),
    "clam_chowder":       ("蛤蜊浓汤", "クラムチャウダー", "क्लैम चाउडर", "Sopa de almejas", 250),
    "lobster_bisque":     ("龙虾浓汤", "ロブスタービスク", "लॉबस्टर बिस्क", "Bisque de langosta", 200),
    "hot_and_sour_soup":  ("酸辣汤", "酸辣湯", "खट्टी-मीठी सूप", "Sopa agripicante", 200),
    "egg_drop_soup":      ("蛋花汤", "卵スープ", "एग ड्रॉप सूप", "Sopa de huevo", 200),
    # Chinese
    "baozi":              ("包子", "包子", "बाओज़ी", "Baozi", 200),
    "spring_rolls_cn":    ("春卷", "春巻き", "स्प्रिंग रोल", "Rollitos de primavera", 150),
    "wonton_soup":        ("馄饨汤", "ワンタンスープ", "वॉन्टन सूप", "Sopa de wantán", 250),
    "hotpot":             ("火锅", "火鍋", "हॉटपॉट", "Olla caliente", 500),
    "mapo_tofu":          ("麻婆豆腐", "麻婆豆腐", "मापो टोफू", "Tofu mapo", 200),
    "kung_pao_chicken":   ("宫保鸡丁", "カンパオチキン", "कुंग पाओ चिकन", "Pollo Kung Pao", 200),
    "sweet_sour_pork":    ("糖醋里脊", "酢豚", "स्वीट एंड सावर पोर्क", "Cerdo agridulce", 200),
    "dim_sum":            ("点心", "点心", "डिम सम", "Dim sum", 150),
    # Japanese
    "takoyaki":           ("章鱼烧", "たこ焼き", "टेकोयाकी", "Takoyaki", 150),
    "okonomiyaki":        ("大阪烧", "お好み焼き", "ओकोनोमियाकी", "Okonomiyaki", 200),
    "tempura":            ("天妇罗", "天ぷら", "टेंपुरा", "Tempura", 150),
    "tonkatsu":           ("炸猪排", "とんかつ", "टोंकात्सु", "Tonkatsu", 200),
    "teriyaki":           ("照烧", "照り焼き", "टेरियाकी", "Teriyaki", 200),
    "gyoza":              ("煎饺", "餃子", "ग्योज़ा", "Gyoza", 150),
    "unagi":              ("鳗鱼", "うなぎ", "उनागी", "Unagi", 200),
    "edamame":            ("毛豆", "枝豆", "एडामेम", "Edamame", 150),
    # Indian
    "naan":               ("馕饼", "ナン", "नान", "Naan", 150),
    "biryani":            ("印度香饭", "ビリヤニ", "बिरयानी", "Biryani", 300),
    "tandoori_chicken":   ("坦都里烤鸡", "タンドリーチキン", "तंदूरी चिकन", "Pollo tandoori", 200),
    "butter_chicken":     ("黄油鸡", "バターチキン", "बटर चिकन", "Pollo con mantequilla", 250),
    "dal":                ("扁豆汤", "ダール", "दाल", "Dal", 200),
    "roti":               ("印度饼", "ロティ", "रोटी", "Roti", 100),
    "masala_dosa":        ("马萨拉多萨", "マサラドーサ", "मसाला डोसा", "Dosa masala", 200),
    # Latin American
    "taco":               ("墨西哥卷饼", "タコス", "टैको", "Taco", 150),
    "burrito":            ("墨西哥卷", "ブリトー", "बुरिटो", "Burrito", 300),
    "nachos":             ("玉米片", "ナチョス", "नाचोस", "Nachos", 200),
    "guacamole":          ("牛油果酱", "ワカモレ", "गुआकामोल", "Guacamole", 150),
    "tamales":            ("玉米粽", "タマレス", "तमालेस", "Tamales", 200),
    "ceviche":            ("酸橘汁腌鱼", "セビーチェ", "सेविचे", "Ceviche", 200),
    # Mediterranean
    "falafel":            ("法拉费", "ファラフェル", "फलाफ़ेल", "Falafel", 150),
    "hummus":             ("鹰嘴豆泥", "フムス", "हुमस", "Hummus", 150),
    "pita":               ("皮塔饼", "ピタ", "पीटा", "Pan pita", 100),
    "gyros":              ("希腊烤肉", "ギロス", "गाइरोस", "Gyros", 250),
    "baklava":            ("果仁蜜饼", "バクラヴァ", "बकलवा", "Baklava", 100),
    # Pasta & Italian
    "spaghetti_bolognese":("意大利肉酱面", "スパゲッティボロネーゼ", "स्पघेटी बोलोग्नीज़", "Espaguetis a la boloñesa", 350),
    "carbonara":          ("奶油培根面", "カルボナーラ", "कार्बोनारा", "Carbonara", 350),
    "lasagna":            ("千层面", "ラザニア", "लज़ानिया", "Lasaña", 300),
    "risotto":            ("意大利烩饭", "リゾット", "रिसोट्टो", "Risotto", 250),
    "bruschetta":         ("意式烤面包", "ブルスケッタ", "ब्रुशेट्टा", "Bruschetta", 150),
    # American
    "mac_and_cheese":     ("芝士通心粉", "マカロニチーズ", "मैक एंड चीज़", "Macarrones con queso", 250),
    "corn_dog":           ("玉米热狗", "コーンドッグ", "कॉर्न डॉग", "Perro de maíz", 180),
    "club_sandwich":      ("俱乐部三明治", "クラブサンドイッチ", "क्लब सैंडविच", "Sándwich club", 250),
    "lobster_roll":       ("龙虾卷", "ロブスターロール", "लॉबस्टर रोल", "Rollo de langosta", 200),
}


def _encode_image(image_bytes: bytes) -> str:
    return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"


async def _call_vision_api(image_bytes: bytes, prompt: str) -> list[dict]:
    """Single raw call to the vision API. Returns list of food items or empty list."""
    api_key = AI_API_KEY()
    if not api_key:
        return []

    payload = {
        "model": AI_MODEL(),
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _encode_image(image_bytes)}},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{AI_API_BASE_URL()}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code != 200:
                logger.error(f"Vision API HTTP {resp.status_code}")
                return []

            content = (resp.json().get("choices") or [{}])[0].get("message", {}).get("content", "")
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            result = json.loads(content)
            if isinstance(result, list):
                # Enrich with source info
                for item in result:
                    item["source_model"] = "vision-api"
                    item["confidence"] = 1.0
                    item["lang"] = "zh"
                return result
            return []
    except Exception as e:
        logger.error(f"Vision API call error: {e}")
        return []


async def _call_hf_food_classifier(image_bytes: bytes) -> list[dict]:
    """
    Call HuggingFace Inference API with a Food-101 classification model.
    Returns multi-language food items using the FOOD101_MULTILANG mapping.
    """
    headers = {"Content-Type": "application/json"}
    if HF_API_KEY():
        headers["Authorization"] = f"Bearer {HF_API_KEY()}"

    payload = {"inputs": _encode_image(image_bytes)}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://api-inference.huggingface.co/models/{HF_MODEL()}",
                headers=headers,
                json=payload,
            )
            if resp.status_code == 503:
                logger.info("HF model loading, waiting 15s...")
                await asyncio.sleep(15)
                resp = await client.post(
                    f"https://api-inference.huggingface.co/models/{HF_MODEL()}",
                    headers=headers,
                    json=payload,
                )

            if resp.status_code != 200:
                logger.error(f"HF API HTTP {resp.status_code}: {resp.text[:200]}")
                return []

            results = resp.json()
            if isinstance(results, list) and len(results) > 0:
                predictions = results[0] if isinstance(results[0], list) else results
                top = [p for p in predictions if isinstance(p, dict) and p.get("score", 0) > 0.1][:3]
                if top:
                    items = []
                    for p in top:
                        label = p.get("label", "").lower().replace(" ", "_")
                        score = p.get("score", 0.5)
                        if label in FOOD101_MULTILANG:
                            zh, ja, hi, es, default_g = FOOD101_MULTILANG[label]
                            items.append({
                                "food": zh,
                                "food_en": p["label"],
                                "estimated_grams": default_g,
                                "description": p["label"],
                                "notes": f"HF confidence: {score:.2f}",
                                "confidence": round(score, 3),
                                "source_model": HF_MODEL().split("/")[-1],
                                "lang": "zh",
                                "_translations": {"ja": ja, "hi": hi, "es": es},
                            })
                        else:
                            items.append({
                                "food": p["label"],
                                "food_en": p["label"],
                                "estimated_grams": 150,
                                "description": p["label"],
                                "notes": f"HF confidence: {score:.2f}",
                                "confidence": round(score, 3),
                                "source_model": HF_MODEL().split("/")[-1],
                                "lang": "en",
                                "_translations": {},
                            })
                    if items:
                        logger.info(f"HF ({HF_MODEL()}): {[i['food'] for i in items]}")
                        return items
            return []
    except Exception as e:
        logger.error(f"HF Inference error: {e}")
        return []


def _crop_grid(image_bytes: bytes, rows: int = 2, cols: int = 2) -> list[bytes]:
    """Split image into grid crops. Returns list of JPEG bytes per region."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    cell_w, cell_h = w // cols, h // rows
    crops = []
    for r in range(rows):
        for c in range(cols):
            left = c * cell_w
            upper = r * cell_h
            right = (c + 1) * cell_w if c < cols - 1 else w
            lower = (r + 1) * cell_h if r < rows - 1 else h
            crop = img.crop((left, upper, right, lower))
            buf = io.BytesIO()
            crop.save(buf, "JPEG", quality=80)
            crops.append(buf.getvalue())
    return crops


def _deduplicate(items: list[dict]) -> list[dict]:
    """Merge items by food name, keeping the first occurrence's values."""
    seen = {}
    for item in items:
        name = item.get("food") or item.get("name", "")
        if not name:
            continue
        key = name.strip().lower()
        if key not in seen:
            seen[key] = item
    return list(seen.values())


def _apply_language(items: list[dict], lang: str) -> list[dict]:
    """
    Apply the user's language preference to food recognition results.
    Translates the 'food' field based on '_translations' dict if available.
    Preserves the original Chinese name in '_food_zh' for nutrition lookup.
    Supported languages: zh, en, ja, hi, es
    """
    for item in items:
        translations = item.pop("_translations", {})
        if lang in translations:
            # Preserve original Chinese for nutrition DB lookup
            if "_food_zh" not in item:
                item["_food_zh"] = item.get("food", "")
            item["food"] = translations[lang]
            item["lang"] = lang
    return items


async def recognize_food_from_image(image_bytes: bytes, lang: str = "zh") -> list[dict]:
    """
    Multi-pass multi-language food recognition.
    
    VISION_MODE=real (production):
      1. HuggingFace food101 classifier  → source="hf"
      2. Vision API (full-image)         → source="ai_model"
      3. Fallback mock                    → source="fallback"
    
    VISION_MODE=fallback (default/test):
      1. Vision API full-image
      2. Grid-crop 2×2 + per-region
      3. HuggingFace food101
      4. Mock fallback
    """
    if VISION_MODE() == "real":
        return await _real_pipeline(image_bytes, lang)
    else:
        return await _fallback_pipeline(image_bytes, lang)


async def _real_pipeline(image_bytes: bytes, lang: str) -> list[dict]:
    """Production pipeline: HF → Vision API → fallback."""
    # ── Pass 1: HuggingFace food101 classifier ──
    try:
        hf_items = await _call_hf_food_classifier(image_bytes)
        if hf_items:
            # Tag with "hf" source
            for item in hf_items:
                item["source_model"] = "hf"
            logger.info(f"Real-pass HF: {len(hf_items)} food(s): "
                        f"{[i['food'] for i in hf_items]}")
            return _apply_language(hf_items, lang)
    except Exception as e:
        logger.error(f"Real HF pass error: {e}")

    # ── Pass 2: Vision API (full image) ──
    try:
        vision_items = await _call_vision_api(image_bytes, FULL_IMAGE_PROMPT)
        if vision_items:
            for item in vision_items:
                item["source_model"] = "ai_model"
            logger.info(f"Real-pass Vision API: {len(vision_items)} food(s)")
            return _apply_language(vision_items, lang)
    except Exception as e:
        logger.error(f"Real Vision API error: {e}")

    # ── Pass 3: Fallback mock ──
    logger.warning("Real pipeline all failed, using fallback mock")
    return _mock_food_list(lang)


async def _fallback_pipeline(image_bytes: bytes, lang: str) -> list[dict]:
    """Fallback pipeline: Vision API → Grid → HF → Mock."""
    # ── Pass 1: Full image (Vision API) ──
    results = await _call_vision_api(image_bytes, FULL_IMAGE_PROMPT)
    logger.info(f"Fallback-pass full-image: {len(results)} food(s)")

    if len(results) >= 2:
        return _apply_language(results, lang)

    # ── Pass 2: Grid-crop 2×2 ──
    try:
        crops = _crop_grid(image_bytes, rows=2, cols=2)
        grid_results = []
        for i, crop_bytes in enumerate(crops):
            items = await _call_vision_api(crop_bytes, REGION_PROMPT)
            if items:
                logger.info(f"  Region {i}: {[r.get('food','?') for r in items]}")
            grid_results.extend(items)

        all_items = results + grid_results
        merged = _deduplicate(all_items)

        if len(merged) >= 2:
            logger.info(f"Fallback-pass grid-merge: {len(merged)} food(s)")
            return _apply_language(merged, lang)
        elif merged:
            results = merged
        else:
            results = []
    except Exception as e:
        logger.error(f"Grid-crop error: {e}")

    # ── Pass 3: HuggingFace food classifier ──
    try:
        hf_items = await _call_hf_food_classifier(image_bytes)
        if hf_items:
            all_items = results + hf_items
            merged = _deduplicate(all_items)
            if merged:
                logger.info(f"Fallback-pass HF: {len(merged)} food(s)")
                return _apply_language(merged, lang)
    except Exception as e:
        logger.error(f"HF pass error: {e}")

    if results:
        logger.info(f"Fallback to vision: {len(results)} food(s)")
        return _apply_language(results, lang)

    logger.warning("All passes failed, using mock")
    return _mock_food_list(lang)


def _mock_food_list(lang: str = "zh") -> list[dict]:
    """Fallback when all APIs are unavailable."""
    mock_items = [
        {"food": "包子", "food_en": "Steamed Bun", "estimated_grams": 200,
         "confidence": 0.85, "source_model": "fallback", "lang": "zh",
         "_translations": {"en": "Steamed Bun", "ja": "包子", "hi": "बाओज़ी", "es": "Baozi"}},
        {"food": "豆浆", "food_en": "Soy Milk", "estimated_grams": 250,
         "confidence": 0.85, "source_model": "fallback", "lang": "zh",
         "_translations": {"en": "Soy Milk", "ja": "豆乳", "hi": "सोया दूध", "es": "Leche de soja"}},
    ]
    return _apply_language(mock_items, lang)


# ── Safe wrapper with model_router integration ──

async def recognize_food_safe(
    image_bytes: bytes,
    db_session,
    lang: str = "zh",
    user_id: str = "",
) -> tuple[list[dict], str, bool]:
    """
    AI food recognition with automatic model failover.
    
    Uses model_router.call_with_fallback to try providers in order with health checks + retry.
    
    Returns:
        (food_items, provider_used, switched)
        - food_items: list of recognized food dicts
        - provider_used: "deepseek" | "huggingface" | "fallback" | "none"
        - switched: True if a fallback was triggered
    """
    from app.services.model_router import call_with_fallback

    async def _vision_call():
        """Call primary vision API."""
        items = await _call_vision_api(image_bytes, FULL_IMAGE_PROMPT)
        if items:
            for item in items:
                item["source_model"] = "ai_model"
            return _apply_language(items, lang)
        return []

    async def _hf_call():
        """Call HuggingFace food classifier."""
        items = await _call_hf_food_classifier(image_bytes)
        if items:
            for item in items:
                item["source_model"] = "hf"
            return _apply_language(items, lang)
        return []

    async def _fallback_call():
        """Return mock fallback data."""
        logger.warning("All providers failed, using fallback mock")
        return _mock_food_list(lang)

    # Build provider chain
    providers = []
    if VISION_MODE() == "real":
        # Real mode: HF first, then Vision API, then fallback
        providers = [
            {"provider": "huggingface", "call": _hf_call},
            {"provider": "deepseek", "call": _vision_call},
            {"provider": "fallback", "call": _fallback_call},
        ]
    else:
        # Fallback mode: Vision API first, then HF, then fallback
        providers = [
            {"provider": "deepseek", "call": _vision_call},
            {"provider": "huggingface", "call": _hf_call},
            {"provider": "fallback", "call": _fallback_call},
        ]

    result, provider_used, switched, error_info = await call_with_fallback(
        db_session=db_session,
        provider_calls=providers,
        user_id=user_id,
        endpoint="/api/v1/meals/analyze-image",
    )

    if result is None:
        logger.error("All vision providers failed: %s", error_info)
        return _mock_food_list(lang), "fallback", True

    return result, provider_used, switched
