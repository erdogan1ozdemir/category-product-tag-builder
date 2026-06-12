---
name: tag-builder
description: >
  Herhangi bir marka için kategori & facet üretimi: veri toplama, facet havuzu,
  ürün etiketleme, SEO kombinasyon + hacim, Excel/Supabase çıktısı. Kullanıcı bir
  marka adı verip kategori/facet/etiketleme isterse, "facet havuzu", "kategori üret",
  "ürün etiketle", "tag builder" derse bu skill'i kullan. LLM işlerini (taksonomi,
  kalite denetimi, etiketleme) pending_llm dosyaları üzerinden BİZZAT sen yaparsın —
  API anahtarı gerekmez.
---

# Tag Builder

Pipeline: collect → taxonomy → pools → review → tag → cross → export
Her aşama: `python run.py <aşama> --brand <slug>` (repo kökünden, .venv aktifken).

## Akış

1. **Profil yoksa**: kullanıcıya marka adı/sektör/Trendyol URL'lerini sor,
   `brands/<slug>.json` dosyasını kendin yaz (şablon: `brands/_template.json`;
   slug küçük harf-rakam-tire ve dosya adıyla aynı olmalı).
2. **Ürün URL'leri**: kullanıcıdan al, `workspace/<slug>/input/urls.txt`'e yaz
   (her satıra bir URL; # ile yorum). urls.txt satırlarına kategori ekle
   (`https://... Ruj`); kategorisiz ürünler "Genel" havuzuna düşer — pools'tan
   önce products.jsonl'daki category alanlarını kontrol et.
3. Aşamaları sırayla çalıştır. Komut **exit 3** ile çıkar VE çıktıda
   `pending_llm/` dosyaları listelenirse → "LLM görevi işleme" bölümünü uygula,
   komutu tekrar çalıştır. (exit 2 = argparse kullanım hatası, karıştırma.)

Kesinti/yarım kalma durumunda: `python run.py continue --brand <slug>` kaldığı aşamayı sürdürür; collect hataları için `python run.py retry-errors --brand <slug>`. Exit 1 = profil/doğrulama hatası — mesajdaki yönergeyi uygula.

## LLM görevi işleme (inline mod — SEN YAPARSIN)

1. Listelenen her `workspace/<slug>/pending_llm/<id>.json` dosyasını oku.
2. `prompt` alanındaki görevi uygula. Cevabın `schema` alanına uymalı
   (ör. `{"groups": "list"}` → sonuçta "groups" anahtarı liste olmalı).
3. Sonucu SAF JSON olarak `pending_llm/<id>.result.json` dosyasına Write ile yaz
   (kod bloğu işareti, açıklama metni YOK).
4. Tüm görevler bitince aynı run.py komutunu yeniden çalıştır.

## Onay (review aşaması)

Havuzları sohbette özet tablo olarak göster (grup → değer sayısı → ilk değerler).
Kullanıcının "sil/birleştir/ekle" taleplerini havuz JSON'una uygula
(`workspace/<slug>/pools/<Kategori>.json`). Onay gelince dosyaya `"reviewed": true`
ekle. DİKKAT: pools aşaması yeniden çalışırsa onaylar düşer (CLI uyarır) — cross
öncesi yeniden onay gerekir. Alternatifler: `streamlit run review/streamlit_app.py`
veya `exports/report.html` paylaşımı.

## Hacim (cross aşaması)

Çıktıda `hacim kaynağı: template` görürsen `input/volumes.csv` yazılmıştır:
kullanıcıdan doldurmasını iste veya DataForSEO MCP bağlıysa hacimleri oradan çekip
CSV'ye yaz, komutu tekrar çalıştır. Hacimleri ASLA tahmin etme. Kalıcı çözüm:
config.json'a dataforseo.login/password.

## Çıktı

`python run.py export --brand <slug> --targets excel supabase`
Excel her zaman güvenli seçenek; Supabase için config.json'da url+service_key olmalı
(şema: docs/supabase_schema.sql). JS-ağır sitelerde scraping için bir kez
`playwright install chromium` gerekir.
