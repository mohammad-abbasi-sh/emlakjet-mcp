# emlakjet-mcp 🇹🇷

Türkiye'nin emlak portalı **emlakjet.com** için resmi olmayan, **salt okunur** MCP sunucusu — canlı ilan arama (satılık / kiralık, şehir ve ilçeye göre), açıklama ve 14 özellik alanıyla tam ilan detayı, ilçe tarama ve piyasa fiyat istatistikleri (m² başına ortanca fiyat dahil).

> Mohammad Abbasi tarafından "Turkey MCP factory" (Sepehr tarzı hat) kapsamında geliştirildi. emlakjet.com ile bağlantısı yoktur.

## Yapay zekâ ajanları için

MCP istemci yapılandırmanıza (stdio) ekleyin:

```json
{
  "mcpServers": {
    "emlakjet": {
      "command": "uvx",
      "args": ["emlakjet-mcp"]
    }
  }
}
```

Veya yerelde çalıştırın: `python -m emlakjet_mcp.server` (`mcp<2`, `httpx` gerekir).

## Araçlar

| Araç | Açıklama |
|------|----------|
| `emlakjet_search` | İlan arama — `listing_type` "satilik"/"kiralik", `property_type` "daire"/"konut"/"villa", `city` ("istanbul"), `district` ("kadikoy"), `rooms` ("2+1"), `min_price`/`max_price` (TL), `min_m2`, `page` 1..50 |
| `emlakjet_listing_detail` | Tek ilanın tam detayı (arama sonucundaki URL veya sayısal id): fiyat, açıklama, adres, oda sayısı, m², 14 özellik alanı, fotoğraflar |
| `emlakjet_list_districts` | Bir şehrin ilçeleri: kısaltma + görünen ad |
| `emlakjet_price_stats` | Piyasa istatistiği: adet, en düşük/en yüksek/ortanca/ortalama fiyat (TL) + m² başına ortanca fiyat, N sayfa üzerinden |

Örnek çıktı (`emlakjet_search` / satılık daire, İstanbul):

```json
{"listing_type": "satilik", "property_type": "daire", "city": "istanbul",
 "page": 1, "count": 50, "listings": [
  {"id": "20062034", "title": "Yıldırım Yapı'dan Metrobüsün Dibinde …",
   "price_try": 1349000, "rooms": "Stüdyo", "area_m2": 60,
   "location": "Cumhuriyet Mahallesi, Esenyurt", "floor": "3. Kat",
   "url": "https://www.emlakjet.com/ilan/…-20062034"}],
 "summary": {"total_listings": 21024, "cheapest_price_try": 310000}}
```

Örnek çıktı (`emlakjet_listing_detail` / id 20044346):

```json
{"id": "20044346", "title": "Aciliyetten Sancaktepede Site İçi İskanlı Daire",
 "price_try": 5950000, "price_currency": "TRY", "rooms_count": 3, "area_m2": 95,
 "address": {"neighbourhood": "Merve Mahallesi", "district": "Sancaktepe",
  "city": "İstanbul", "country": "TR"},
 "specs": {"Isıtma Tipi": "Kombi Doğalgaz", "Otopark": "Açık & Kapalı Otopark",
  "Kullanım Durumu": "Mülk Sahibi Oturuyor", "Krediye Uygunluk": "Krediye Uygun",
  "Site İçerisinde": "Evet", "Tapu Durumu": "Kat Mülkiyeti", …}}
```

Örnek çıktı (`emlakjet_price_stats` / İstanbul Kadıköy, 1 sayfa):

```json
{"count": 50, "currency": "TRY", "min": 5650000, "max": 48000000,
 "median": 17100000.0, "average": 18228800.0,
 "median_price_per_m2_try": 162792.21, "pages_scanned": 1}
```

Notlar:
- Veriler emlakjet.com'un herkese açık sunucu taraflı sayfalarından gelir (schema.org RealEstateListing/Product JSON-LD) — anahtar yok, giriş yok, salt okunur.
- Oda/fiyat/alan filtreleri çekilen sayfaya uygulanır (sitenin sunucu taraflı oda/fiyat filtresi yok); arama sayfa başına en fazla 50 ilan döndürür.
- Sitenin sıralama anahtarları canlı test edildi ve sunucu taraflı listeyi yeniden sıralamıyor; bu yüzden sıralama parametresi sunulmuyor — dönen ilanları kendiniz sıralayın.
- Özellik etiketleri Türkçedir (Isıtma Tipi, Otopark, Kullanım Durumu, Krediye Uygunluk, Site İçerisinde, Tapu Durumu, Takas, Asansör, Mutfak, Eşya Durumu, Balkon…).
- İstekler arasında ~0,8 sn beklenir (nazik kullanım).
- MITM proxy arkasındaki ortamlar: `SSL_CERT_FILE` ile proxy'ye güvenen bir CA paketi gösterin.

## Geliştirme

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_listings.py` — çevrimdışı, gerçek yakalanmış örneklerle
- `tests/test_live.py` — emlakjet.com'a karşı 6 temkinli canlı istek

## Lisans

MIT
