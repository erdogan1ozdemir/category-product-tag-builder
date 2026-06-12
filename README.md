# Category Product Tag Builder

Herhangi bir e-ticaret markası için kategori taksonomisi, facet havuzu, ürün etiketleme
ve SEO anahtar kelime kombinasyonları üreten marka-bağımsız bir pipeline. Proje,
başlangıçta Özdilek için geliştirilen dahili bir araçtan genelleştirilerek yeniden
yazılmıştır; artık `brands/<slug>.json` profil dosyası tanımlanan her marka için
aynı pipeline çalışır. Çıktılar JSON, Excel (3 sayfa) ve Supabase olarak dışa aktarılır.

---

## Kurulum

```bash
git clone <repo-url>
cd category-product-tag-builder

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config.example.json config.json
# config.json'u düzenle: LLM sağlayıcı, Supabase, DataForSEO vb.
```

JavaScript ağır sitelerde Playwright render fallback için bir kez çalıştır:

```bash
playwright install chromium
```

---

## Hızlı Başlangıç

```bash
# 1. Marka profilini oluştur
python run.py init

# 2. Ürün URL'lerini gir
# workspace/flormar/input/urls.txt dosyasını düzenle
# Her satıra bir URL; isteğe bağlı olarak boşlukla ayırarak kategori belirt:
#   https://site.com/ruj-01  Ruj
#   https://site.com/fondoten-02  Fondöten
# Kategori belirtilmezse ürün JSON-LD/breadcrumb'dan okunur; bulunamazsa "Genel" havuzuna düşer.

# 3. Ürünleri topla (scraping)
python run.py collect --brand flormar

# 4. Taksonomi / kategori grupları oluştur
python run.py taxonomy --brand flormar

# 5. Facet havuzlarını oluştur
python run.py pools --brand flormar

# 6. Havuzları gözden geçir ve onayla
python run.py review --brand flormar
# veya: streamlit run review/streamlit_app.py
# veya: workspace/flormar/exports/report.html dosyasını aç

# 7. Ürünleri etiketle
python run.py tag --brand flormar

# 8. SEO kombinasyonları + hacim
python run.py cross --brand flormar

# 9. Dışa aktar
python run.py export --brand flormar --targets excel supabase
```

---

## LLM Sağlayıcı Seçenekleri

`config.json` içinde `llm.provider` alanıyla yapılandırılır.

| Sağlayıcı     | Mekanizma                                         | Gereksinim                          |
|---------------|---------------------------------------------------|-------------------------------------|
| `inline`      | Pipeline exit 3 ile durur, pending_llm dosyaları üretir; Claude Code görevleri yapar | Yok (varsayılan) |
| `claude-cli`  | Yerel Claude Code CLI'ya subprocess çağrısı       | Claude Code kurulu; `llm.timeout_seconds` ayarlanabilir |
| `anthropic`   | Anthropic HTTP API                                | `llm.anthropic_api_key`             |
| `gemini`      | Google Gemini API                                 | `llm.gemini_api_key`                |
| `perplexity`  | Perplexity API                                    | `llm.perplexity_api_key`            |

### Inline mod nasıl çalışır?

Pipeline bir LLM görevi oluşturduğunda komut **exit kodu 3** ile çıkar ve stdout'ta
`workspace/<slug>/pending_llm/<id>.json` dosya yollarını listeler (argparse hataları
exit 2 ile çıkar; ikisini karıştırma). Her pending dosyasında `prompt` (görev), `schema`
(beklenen JSON yapısı) ve `_talimat` alanları bulunur. Görevi tamamlayıp sonucu saf JSON
olarak `<id>.result.json` dosyasına yazdıktan sonra aynı komutu yeniden çalıştırırsın.

---

## Claude Code & claude.ai/code Kullanımı

Repoyu Claude Code'da açıp şunu yazmak yeterli:

> "flormar için facet havuzu üret"

`tag-builder` skill'i devreye girerek profil oluşturma, URL toplama, tüm pipeline
aşamalarını çalıştırma ve inline LLM görevlerini bizzat tamamlama işlemlerini yönetir.
API anahtarı veya ek kurulum gerekmez.

---

## Onay Seçenekleri

| Yöntem              | Açıklama                                                                                     |
|---------------------|----------------------------------------------------------------------------------------------|
| Sohbet içi          | Claude havuzları tablo olarak gösterir; sil/birleştir/ekle komutlarını uygular, `"reviewed": true` ekler |
| Streamlit (lokal)   | `streamlit run review/streamlit_app.py` — hesap gerekmez; "Kaydet" onayı düşürür, "Kaydet ve Onayla" onaylar |
| Streamlit (online)  | Streamlit Community Cloud'a deploy + GitHub girişi ile ekiple paylaşılabilir                |
| Statik HTML rapor   | `workspace/<slug>/exports/report.html` — tarayıcıda açılır, hesap gerekmez                 |

**Dikkat:** `pools` aşaması yeniden çalıştırılırsa tüm onaylar düşer (CLI uyarır).
`cross` aşamasından önce yeniden onay gerekir.

---

## Çıktılar

| Format  | Konum                                        | İçerik                                                        |
|---------|----------------------------------------------|---------------------------------------------------------------|
| JSON    | `workspace/<slug>/exports/export.json`       | Her zaman üretilir; tüm verileri içerir                       |
| Excel   | `workspace/<slug>/exports/<slug>.xlsx`       | 3 sayfa: Ürünler (dinamik facet sütunları) / Havuz Özeti / Kombinasyonlar |
| Supabase | Yapılandırılan proje                        | `pools`, `product_tags`, `combos` tabloları; şema: `docs/supabase_schema.sql`; 500 satır chunks |

Supabase için `config.json`'da `supabase.url` ve `supabase.service_key` gereklidir.

---

## Trendyol URL'lerine Kategori Ekleme

`brands/<slug>.json` dosyasında `trendyol_urls` listesi iki formatı destekler:

```json
"trendyol_urls": [
  "https://www.trendyol.com/ruj-x-c123",
  {"url": "https://www.trendyol.com/fondoten-x-c456", "category": "Fondöten"}
]
```

- **String** (eski format): kategori `--category` opsiyonundan veya marka adından alınır.
- **Dict** formatı: `"category"` alanı varsa o kategori kullanılır (her URL için ayrı kategori tanımlanabilir).

---

## Klasör Yapısı

```
category-product-tag-builder/
├── brands/               # Marka profil JSON dosyaları (<slug>.json)
├── core/                 # Pipeline motoru, brand_profile, state
├── facets/               # Normalizer, pool_builder, quality_checker, taxonomy
├── llm/                  # LLM köprüsü, inline_skill, provider istemcileri
├── outputs/              # Excel, JSON, Supabase sink'leri
├── review/               # Streamlit app, HTML rapor oluşturucu
├── seo/                  # Cross-join, hacim entegrasyonu
├── sources/              # Generic scraper, Trendyol adaptörü
├── tagger/               # Ürün etiketleme, batch işleme
├── tests/                # pytest test paketi
├── docs/
│   ├── supabase_schema.sql
│   └── superpowers/
│       ├── specs/        # Proje spec dokümanı
│       └── plans/        # İmplementasyon planı
├── .claude/skills/tag-builder/SKILL.md
├── config.example.json
├── requirements.txt
└── run.py                # CLI giriş noktası
```

---

## Bağlantılar

- Spec: `docs/superpowers/specs/`
- Plan: `docs/superpowers/plans/`
- Supabase şema: `docs/supabase_schema.sql`
