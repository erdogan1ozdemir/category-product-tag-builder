# Category Product Tag Builder — Tasarım Dokümanı

**Tarih:** 2026-06-12
**Durum:** Onaylandı (kullanıcı onayı: 2026-06-12)
**Kaynak ilham:** [Category-generator-v5](https://github.com/emrekaynar26/Category-generator-v5) (Özdilek'e özel sürüm)

## 1. Amaç ve kapsam

Herhangi bir marka/sektör için (Boyner, Turkcell, Flormar, Vitra...) e-ticaret kategori ve facet (filtre) yapılarını üreten, ürünleri etiketleyen ve SEO odaklı atomik kategori adayları çıkaran genel bir araç. Özdilek'e özel Category-generator-v5'in marka bağımsız, Claude-yerel yeniden kurulumudur.

**Kapsama dahil (kullanıcı onaylı dört modül):**
1. Facet havuzu üretimi (marka/kategori başına filtre havuzları)
2. Ürün etiketleme (tek/toplu, havuzlara göre)
3. Kategori çaprazlama + SEO aranma hacmi filtresi (v5'te eksik olan adım dahil yazılacak)
4. İnsan onay arayüzü (birden çok varyasyon)

**Kapsam dışı:**
- SAP Spartacus veya herhangi bir e-ticaret platformuna doğrudan aktarım (çıktılar Excel/Supabase/JSON; aktarım alıcı sistemin işi)
- Marka başına özel adaptör kodu (veri girişi genel scraping + Trendyol ile sınırlı)
- Görsel tabanlı etiketleme için özel vision pipeline (LLM görevlerinde görsel URL'leri bağlam olarak geçilir, ayrı bir CLIP/embedding altyapısı kurulmaz)

## 2. Temel tasarım kararları (kullanıcı ile netleştirildi)

| Karar | Seçim |
|---|---|
| Veri girişi | URL listesi + genel scraping **ve** Trendyol/pazaryeri. Excel/CSV ürün listesi girişi ikincil kolaylık olarak desteklenir (URL kolonu okunur). |
| LLM çalıştırma | Üçü birden: `inline` skill (varsayılan, anahtarsız), `claude -p` subprocess, API anahtarlı sağlayıcılar (Anthropic/Gemini/Perplexity) |
| Onay akışı | Birkaç varyasyon birlikte: sohbet içi onay + Streamlit ekranı + statik HTML rapor (GitHub Pages/Vercel'e konabilir) |
| Çıktı | JSON/JSONL her zaman; Excel (genel şablon) ve Supabase opsiyonel |
| Çalışma ortamı | Claude Code (lokal) ve claude.ai/code (web-app) — skill repo içine gömülür |

## 3. Mimari

Üç değiştirilebilir katman (kaynak, LLM, çıktı) + sabit çekirdek.

```
category-product-tag-builder/
├── run.py                        # CLI girişi: interaktif menü + alt komutlar
├── requirements.txt
├── config.example.json           # tüm anahtarlar OPSİYONEL; boş = inline Claude
├── .claude/skills/tag-builder/
│   └── SKILL.md                  # sohbetten pipeline'ı yöneten skill
├── brands/
│   ├── _template.json            # marka profili şablonu
│   └── (kullanıcı profilleri: boyner.json, vitra.json...)
├── core/
│   ├── brand_profile.py          # profil yükleme + doğrulama
│   ├── pipeline.py               # aşama orkestrasyonu
│   └── state.py                  # workspace durum yönetimi, resume
├── sources/
│   ├── base.py                   # SourceAdapter arayüzü
│   ├── generic_scraper.py        # URL → ürün verisi (JSON-LD/OG öncelikli)
│   └── trendyol.py               # v5'ten taşınır: aggregation + SEO landing
├── llm/
│   ├── bridge.py                 # LLMBridge arayüzü + provider fabrikası
│   ├── tasks.py                  # görev tipleri + JSON şemaları
│   ├── inline_skill.py           # pending_llm/ iş dosyası üret/oku
│   ├── claude_cli.py             # claude -p subprocess
│   ├── anthropic_api.py
│   ├── gemini_api.py
│   └── perplexity_api.py
├── facets/
│   ├── taxonomy.py               # sektöre göre facet grubu önerisi (LLM görevi)
│   ├── pool_builder.py           # havuz birleştirme (v5 gap_analyzer'ın genel hali)
│   ├── normalizer.py             # v5'ten taşınır (TR-aware normalize)
│   └── quality_checker.py        # v5'ten taşınır
├── tagger/
│   ├── product_tagger.py         # deterministik + LLM boşluk doldurma
│   └── batch.py                  # paralel toplu işleme, hata toleransı
├── seo/
│   ├── cross_join.py             # kategori × facet kombinasyon türetme
│   └── volume.py                 # DataForSEO (anahtar varsa) / manuel CSV import
├── outputs/
│   ├── json_sink.py              # her zaman
│   ├── excel_sink.py             # genel şablon
│   └── supabase_sink.py          # kimlik varsa upsert
├── review/
│   ├── streamlit_app.py          # görsel onay ekranı (v5'ten sadeleştirilmiş)
│   └── html_report.py            # statik HTML rapor üretici
├── docs/
│   ├── supabase_schema.sql
│   └── superpowers/specs/        # bu doküman
├── tests/
└── workspace/                    # gitignored, marka başına çalışma alanı
    └── <marka>/
        ├── input/                # URL listeleri, manuel hacim CSV'leri
        ├── products/             # toplanan ham ürün verisi (JSONL)
        ├── pools/                # facet havuzları (JSON)
        ├── pending_llm/          # inline modda LLM iş kuyruğu
        ├── tagged/               # etiketlenmiş ürünler (JSONL)
        ├── combos/               # kombinasyon + hacim verileri
        ├── exports/              # Excel çıktıları
        └── errors.jsonl          # başarısız işler
```

### Marka profili (`brands/<marka>.json`)

```json
{
  "name": "Flormar",
  "slug": "flormar",
  "sector": "kozmetik",
  "site_domain": "flormar.com.tr",
  "trendyol_brand": "Flormar",
  "language": "tr",
  "notes": "isteğe bağlı serbest metin: özel kurallar, hariç tutulacak gruplar"
}
```

Yeni marka = yeni JSON dosyası. Kod değişikliği gerekmez. `sector` alanı taxonomy aşamasında LLM'e bağlam olur — facet grupları sabit liste değil, sektöre göre önerilir.

## 4. Pipeline — 8 aşama

Her aşama `python run.py <aşama> --brand <marka>` ile bağımsız çalıştırılabilir; skill aynı komutları sohbetten çağırır. Tüm aşamalar idempotent ve `continue` ile kaldığı yerden sürer.

1. **`init`** — Marka profili sihirbazı. Sohbette skill soru-cevapla, CLI'da interaktif prompt'la `brands/<marka>.json` üretir.
2. **`collect`** — Veri toplama:
   - `generic_scraper`: kullanıcının verdiği URL listesini gezer. Ayıklama önceliği: ① JSON-LD `Product` şeması → ② OpenGraph/microdata → ③ sezgisel HTML ayıklama (başlık, özellik tabloları, görseller). Çıktı: `products/*.jsonl`.
   - `trendyol`: marka/kategori araması ile facet aggregation'ları + SEO landing linkleri (v5 kodu taşınır). Trendyol'da olmayan markalarda bu adım atlanır, akış durmaz.
3. **`taxonomy`** — LLM görevi: sektör + toplanan ham özellik adlarından facet grubu önerisi (ör. kozmetik → Cilt Tipi, Bitiş, Ton; banyo → Montaj Tipi, Boyut, Malzeme). Kullanıcı onayına sunulur.
4. **`pools`** — Havuz üretimi: kaynak verileri grup bazında birleştirir, `normalizer` temizler, LLM kalite denetimi (eşanlamlı birleştirme, yazım, grup-dışı değer ayıklama) uygulanır → `pools/<kategori>.json` (v5'teki `Abiye.json` formatının genel hali, format korunur: `arama_kelimesi` + grup → değer listesi).
5. **`review`** — Üç varyasyon, hepsi aynı havuz dosyalarını okuyup yazar:
   - **Sohbet içi (varsayılan):** skill havuzu özet tablo olarak gösterir; "X grubunu sil, Y'yi Z'yle birleştir" komutlarıyla düzenlenir; onayda `reviewed: true` damgalanır.
   - **Streamlit:** lokal görsel ekran (`streamlit run review/streamlit_app.py`). Hesap gerekmez; online paylaşım istenirse Streamlit Community Cloud'a GitHub hesabıyla bağlanır.
   - **HTML rapor:** `html_report.py` salt-okunur statik rapor üretir; GitHub Pages/Vercel'de paylaşılabilir, geri bildirim sohbet üzerinden işlenir.
6. **`tag`** — Ürün etiketleme: önce deterministik eşleme (ürün metninde havuz değeri birebir/normalize geçiyorsa), kalan boşlukları LLM görevi doldurur. Boşluk kalırsa boş bırakılır — tahmin uydurulmaz. Çıktı: `tagged/*.jsonl` (ürün başına: facet → değer + güven + kaynak [deterministik/llm]).
7. **`cross`** — Kombinasyon: onaylı havuz × kategori çaprazlaması (`Kırmızı Abiye`, `Mat Ruj` gibi). Hacim verisi:
   - DataForSEO anahtarı varsa otomatik çekilir,
   - yoksa kombinasyon listesi Excel/CSV'ye yazılır, kullanıcı hacim kolonunu doldurup `--import-volumes dosya.csv` ile geri verir.
   - Eşik (`threshold`) config'te; eşik üstü "kategori adayı", altı "sadece filtre" işaretlenir.
8. **`export`** — Sink'lere yazım. JSON her zaman; Excel ve Supabase config'e göre. Hepsi aynı anda seçilebilir.

## 5. LLM köprüsü

Tek arayüz: `LLMBridge.run(task) -> result`. Görevler `llm/tasks.py`'de tipli ve JSON şemalı tanımlanır (taxonomy önerisi, havuz kalite denetimi, ürün etiketleme, grup filtreleme).

| Provider | Mekanizma | Gereksinim |
|---|---|---|
| `inline` (varsayılan) | Görevler `pending_llm/<id>.json` dosyalarına yazılır; sohbetteki Claude (skill talimatıyla) okur, sonucu `<id>.result.json` olarak yazar, `run.py continue` çağırır | Yok — abonelik dahilinde |
| `claude-cli` | `claude -p --output-format json` subprocess | Lokal Claude Code kurulumu |
| `anthropic` | Messages API | `anthropic_api_key` |
| `gemini` | generateContent API | `gemini_api_key` |
| `perplexity` | Chat Completions API | `perplexity_api_key` |

Ortak kurallar:
- **Gruplama:** inline ve CLI modlarında görevler batch'lenir (ör. 50 ürün tek görev dosyasında) — token verimi ve daha az gidiş-geliş.
- **Şema doğrulama:** her sonuç görevin JSON şemasıyla doğrulanır; geçemeyen görev `pending` durumuna geri düşer ve hata notu eklenir.
- **Provider düşmesi:** seçili provider çalışamazsa (anahtar yok, CLI yok) akış hata mesajıyla durur ve `inline` moda geçiş önerilir; sessiz fallback yapılmaz.

## 6. Çıktılar

- **JSON/JSONL (her zaman):** havuzlar, etiketli ürünler, kombinasyonlar — diğer sink'lerin kaynağı.
- **Excel (genel şablon):** Sayfa 1 "Ürünler" (sabit kolonlar: ürün adı/URL/kategori + dinamik facet kolonları), Sayfa 2 "Havuz Özeti" (grup → değer sayısı → değerler), Sayfa 3 "Kombinasyonlar" (kombinasyon, hacim, eşik kararı). Özdilek'e özel "E-Com İçerik Şablonu" taşınmaz.
- **Supabase:** `config.json → supabase.url + service_key`. Şema `docs/supabase_schema.sql` (markalar, havuzlar, ürün etiketleri, kombinasyonlar tabloları; marka slug'ı ile çok-kiracılı). Sink upsert yapar; kimlik yoksa sink atlanır ve kullanıcı bilgilendirilir.

## 7. Hata yönetimi

- Scraping hatası ürün bazında `errors.jsonl`'a düşer; akış durmaz; `run.py retry-errors --brand <marka>` ile yeniden denenir.
- Trendyol erişilemezse (Cloudflare vb.) o kaynak atlanır, uyarı loglanır; generic scraper verisiyle devam edilir.
- LLM sonucu şemaya uymazsa görev yeniden kuyruğa alınır (en fazla 2 tekrar), sonra `errors.jsonl`.
- Tüm yazımlar append-only JSONL veya atomik dosya değişimi — yarıda kesilme veri bozmaz.
- Resume: her aşama mevcut çıktıları kontrol eder, işlenmiş öğeleri atlar (v5'in `--yeniden-baslat` deseni korunur, varsayılan davranış devam etmektir).

## 8. Test stratejisi

- **Birim (pytest, LLM'siz):** normalizer (TR karakter, eşanlamlı, junk temizliği), pool_builder birleştirme mantığı, cross_join kombinasyon üretimi, excel_sink kolon üretimi, brand_profile doğrulama.
- **Fixture tabanlı:** `generic_scraper` gerçek e-ticaret sayfalarından alınmış statik HTML fixture'larıyla (JSON-LD'li, OG'li, düz HTML'li üç örnek) test edilir — ağ erişimi yok.
- **Mock provider:** `llm/bridge.py` için sabit cevap dönen `mock` provider; pipeline uçtan uca LLM'siz ve ağsız test edilebilir.
- **Şema testleri:** tüm LLM görev şemaları örnek geçerli/geçersiz yüklerle doğrulanır.

## 9. v5'ten taşınacak kod

| v5 kaynağı | Yeni yeri | Not |
|---|---|---|
| `product_tagger/normalization/normalizer.py` | `facets/normalizer.py` | TR-aware normalize, olduğu gibi |
| `pool_creator/scripts/pool_quality_checker.py` | `facets/quality_checker.py` | Gemini bağımlılığı LLMBridge'e çevrilir |
| `pool_creator/scripts/trendyol_seo_landing_enricher.py` + `trendyol_enricher.py`'nin aggregation kısmı | `sources/trendyol.py` | Özdilek marka-kodu eşleme mantığı atılır |
| `tools/jsonl_to_excel.py` | `outputs/excel_sink.py` | Şablon genelleştirilir |
| `product_tagger/db/supabase_sink.py` | `outputs/supabase_sink.py` | Şema genelleştirilir |
| JSONL append + resume deseni | `core/state.py` | Desen korunur |

Taşınmayanlar: Özdilek `product_fetcher`, 6 enricher (yerine LLMBridge), CLIP benzerlik scripti, D1 sink, Özdilek Excel şablonu.

## 10. Açık riskler

- **Genel scraping kırılganlığı:** JSON-LD'siz, ağır JavaScript'li sitelerde ayıklama zayıf kalabilir. Hafifletme: üç katmanlı ayıklama + hatalı ürünlerin raporlanması; gerekirse ileride Playwright render desteği eklenir (ilk sürümde yok).
- **Trendyol Cloudflare:** v5'te de mevcut risk; kaynak opsiyonel olduğu için akışı kırmaz.
- **Inline mod insan-döngüsü:** çok büyük batch'lerde sohbet üzerinden işlem yavaş olabilir; hafifletme: görev gruplama + kullanıcıya `claude-cli`/API modu önerisi.
