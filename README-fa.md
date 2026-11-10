# emlakjet-mcp 🇹🇷

سرور MCP غیررسمی و **فقط‌خواندنی** برای **emlakjet.com**، پورتال املاک ترکیه — جست‌وجوی زندهٔ آگهی‌ها (فروش / اجاره، بر اساس شهر و منطقه)، جزئیات کامل هر آگهی با توضیحات و ۱۴ فیلد مشخصات، مرور مناطق شهر و آمار قیمت بازار (از جمله میانهٔ قیمت هر متر مربع).

> ساختهٔ محمد عباسی در قالب «کارخانهٔ Turkey MCP» (خط تولید به سبک سپهر). وابستگی به emlakjet.com ندارد.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP خود (stdio) اضافه کنید:

```json
{
  "mcpServers": {
    "emlakjet": {
      "command": "uvx",
      "args": ["emlakjet-mcp==0.1.1"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m emlakjet_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `emlakjet_search` | جست‌وجوی آگهی‌ها — `listing_type` برابر «satilik» (فروش) یا «kiralik» (اجاره)، `property_type` برابر «daire»/«konut»/«villa»، `city` مثل «istanbul»، `district` مثل «kadikoy»، `rooms` مثل «2+1»، `min_price`/`max_price` (لیر)، `min_m2`، `page` از ۱ تا ۵۰ |
| `emlakjet_listing_detail` | جزئیات کامل یک آگهی (آدرس از خروجی جست‌وجو، یا شناسهٔ عددی): قیمت، توضیحات، آدرس، تعداد اتاق، متراژ، ۱۴ فیلد مشخصات، عکس‌ها |
| `emlakjet_list_districts` | مناطق یک شهر با نام کوتاه و نام نمایشی |
| `emlakjet_price_stats` | آمار بازار: تعداد، کمینه/بیشینه/میانه/میانگین قیمت (لیر) + میانهٔ قیمت هر متر مربع، روی N صفحه |

خروجی نمونه (`emlakjet_search` / آپارتمان فروشی، استانبول):

```json
{"listing_type": "satilik", "property_type": "daire", "city": "istanbul",
 "page": 1, "count": 50, "listings": [
  {"id": "20062034", "title": "Yıldırım Yapı'dan Metrobüsün Dibinde …",
   "price_try": 1349000, "rooms": "Stüdyo", "area_m2": 60,
   "location": "Cumhuriyet Mahallesi, Esenyurt", "floor": "3. Kat",
   "url": "https://www.emlakjet.com/ilan/…-20062034"}],
 "summary": {"total_listings": 21024, "cheapest_price_try": 310000}}
```

خروجی نمونه (`emlakjet_listing_detail` / شناسهٔ 20044346):

```json
{"id": "20044346", "title": "Aciliyetten Sancaktepede Site İçi İskanlı Daire",
 "price_try": 5950000, "price_currency": "TRY", "rooms_count": 3, "area_m2": 95,
 "address": {"neighbourhood": "Merve Mahallesi", "district": "Sancaktepe",
  "city": "İstanbul", "country": "TR"},
 "specs": {"Isıtma Tipi": "Kombi Doğalgaz", "Otopark": "Açık & Kapalı Otopark",
  "Kullanım Durumu": "Mülk Sahibi Oturuyor", "Krediye Uygunluk": "Krediye Uygun",
  "Site İçerisinde": "Evet", "Tapu Durumu": "Kat Mülkiyeti", …}}
```

خروجی نمونه (`emlakjet_price_stats` / استانبول، کادیکوی، ۱ صفحه):

```json
{"count": 50, "currency": "TRY", "min": 5650000, "max": 48000000,
 "median": 17100000.0, "average": 18228800.0,
 "median_price_per_m2_try": 162792.21, "pages_scanned": 1}
```

نکته‌ها:
- داده‌ها از صفحات عمومی سمت‌سرور emlakjet.com می‌آیند (JSON-LD از نوع RealEstateListing/Product در schema.org) — بدون کلید، بدون ورود، فقط خواندنی.
- فیلترهای اتاق/قیمت/متراژ روی صفحهٔ دریافت‌شده اعمال می‌شوند (سایت فیلتر سمت‌سرور برای اتاق و قیمت ندارد)؛ هر صفحه حداکثر ۵۰ آگهی برمی‌گرداند.
- کلیدهای مرتب‌سازی سایت به‌صورت زنده آزمایش شدند و فهرست سمت‌سرور را دوباره مرتب نمی‌کنند؛ به همین دلیل پارامتر مرتب‌سازی ارائه نمی‌شود — آگهی‌های برگشتی را خودتان مرتب کنید.
- برچسب‌های مشخصات ترکی‌اند (Isıtma Tipi، Otopark، Kullanım Durumu، Krediye Uygunluk، Site İçerisinde، Tapu Durumu، Takas، Asansör، Mutfak، Eşya Durumu، Balkon…).
- بین درخواست‌ها حدود ۰٫۸ ثانیه فاصله گذاشته می‌شود تا به سایت فشار نیاید.
- پشت پروکسی MITM: متغیر `SSL_CERT_FILE` را به بستهٔ CA مورد اعتماد پروکسی بدهید.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" curl-cffi pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_listings.py` — آفلاین، با نمونه‌های واقعی ذخیره‌شده
- `tests/test_live.py` — ۶ درخواست محتاطانهٔ زنده به emlakjet.com

## مجوز

MIT
