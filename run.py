"""category-product-tag-builder — herhangi bir marka için kategori & facet üretimi.

KULLANIM:
    python run.py init                              # marka profili sihirbazı
    python run.py collect --brand flormar           # veri toplama (input/urls.txt + Trendyol)
    python run.py taxonomy --brand flormar          # sektöre göre facet grubu önerisi
    python run.py pools --brand flormar             # havuz üretimi + kalite denetimi
    python run.py review --brand flormar            # HTML rapor üret + onay yönergesi
    python run.py tag --brand flormar               # ürünleri etiketle
    python run.py cross --brand flormar             # kombinasyon + hacim + eşik
    python run.py cross --brand flormar --import-volumes dosya.csv
    python run.py export --brand flormar --targets excel supabase
    python run.py continue --brand flormar          # son aşamayı kaldığı yerden sürdür
    python run.py retry-errors --brand flormar      # hatalı collect URL'lerini yeniden dene

LLM provider config.json'da seçilir (inline | claude-cli | anthropic | gemini | perplexity).
inline modda komut, LLM sonucu bekleyen görev dosyalarını listeleyip çıkar (exit 3);
sohbetteki Claude sonuçları yazınca aynı komut yeniden çalıştırılır.
"""
import argparse
import json
import os
import re
import sys

from core.brand_profile import load_brand
from core.pipeline import STAGES, run_stage
from core.state import Workspace
from llm.bridge import PendingLLMWork


def load_config() -> dict:
    if os.path.exists("config.json"):
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    return {"llm": {"provider": "inline"}}


def cmd_init(args):
    print("Yeni marka profili:")
    data = {
        "name": input("  Marka adı: ").strip(),
        "slug": input("  Slug (küçük harf, tire): ").strip(),
        "sector": input("  Sektör (moda/kozmetik/banyo/...): ").strip(),
        "site_domain": input("  Site domain [boş geçilebilir]: ").strip(),
        "trendyol_brand": input("  Trendyol marka adı [boş]: ").strip(),
        "language": input("  Dil [tr]: ").strip() or "tr",
    }
    if not re.fullmatch(r"[a-z0-9-]+", data["slug"]):
        print("✗ slug yalnız küçük harf, rakam ve tire içerebilir")
        return
    urls = input("  Trendyol kategori/marka URL'leri (virgülle) [boş]: ").strip()
    data["trendyol_urls"] = [u.strip() for u in urls.split(",") if u.strip()]
    os.makedirs("brands", exist_ok=True)
    path = os.path.join("brands", f"{data['slug']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    load_brand(data["slug"])
    Workspace(data["slug"]).ensure()
    print(f"✓ {path} oluşturuldu. Sonraki adım: workspace/{data['slug']}/input/urls.txt "
          f"dosyasına ürün URL'lerini koyup 'python run.py collect --brand {data['slug']}'")


def cmd_retry_errors(args):
    brand = load_brand(args.brand)
    ws = Workspace(brand.slug).ensure()
    errors = [e for e in ws.read_jsonl("errors.jsonl") if e.get("stage") == "collect"]
    if not errors:
        print("collect hatası yok.")
        return
    from sources.generic_scraper import collect_from_urls
    urls = [e["url"] for e in errors if e.get("url")]
    print(f"{len(urls)} hatalı URL yeniden deneniyor...")
    counts = collect_from_urls(urls, ws)
    print(f"✓ yeni: {counts['yeni']}, hata: {counts['hata']}")


def _print_result(stage, result, brand):
    if stage == "pools" and isinstance(result, dict):
        print(f"✓ pools tamamlandı: {len(result.get('built', []))} havuz üretildi: {', '.join(result.get('built', []))}")
        if result.get("onay_dustu"):
            print(f"⚠ Onayı düşen kategoriler (havuz yeniden üretildi, tekrar onay gerekir): "
                  f"{', '.join(result['onay_dustu'])}")
        return
    if stage == "cross" and isinstance(result, dict):
        print(f"✓ cross tamamlandı: {result['combos']} kombinasyon, hacim kaynağı: {result['volume_source']}")
        if result.get("volume_source") == "template":
            print(f"⚠ Hacim şablonu yazıldı: {result['template_path']}")
            print(f"  volume kolonunu doldurup tekrar çalıştırın: python run.py cross --brand {brand.slug}")
            print(f"  veya: python run.py cross --brand {brand.slug} --import-volumes <dosya.csv>")
        return
    print(f"✓ {stage} tamamlandı: {result}")


def main():
    parser = argparse.ArgumentParser(
        prog="run.py", description="Marka bağımsız kategori & facet üretim aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="marka profili sihirbazı")
    for stage in STAGES + ["continue"]:
        p = sub.add_parser(stage, help=f"'{stage}' aşamasını çalıştır")
        p.add_argument("--brand", required=True)
        if stage == "cross":
            p.add_argument("--import-volumes", dest="import_volumes")
        if stage == "export":
            p.add_argument("--targets", nargs="+", default=["excel"],
                           choices=["excel", "supabase", "json"])
        if stage == "collect":
            p.add_argument("--category", help="Trendyol facet'lerinin yazılacağı kategori adı")
    p_retry = sub.add_parser("retry-errors", help="hatalı collect URL'lerini yeniden dene")
    p_retry.add_argument("--brand", required=True)

    args = parser.parse_args()
    if args.cmd == "init":
        return cmd_init(args)

    try:
        if args.cmd == "retry-errors":
            return cmd_retry_errors(args)
        brand = load_brand(args.brand)
    except (FileNotFoundError, ValueError) as e:
        print(f"✗ {e}")
        sys.exit(1)

    config = load_config()
    stage = args.cmd
    if stage == "continue":
        ws = Workspace(brand.slug)
        state = ws.read_json("_stage.json", default=None)
        if not state:
            print("Sürdürülecek aşama yok.")
            return
        stage = state["stage"]
        print(f"Sürdürülüyor: {stage}")
    opts = {k: v for k, v in vars(args).items() if k not in ("cmd", "brand")}
    try:
        result = run_stage(stage, brand, config, **opts)
        _print_result(stage, result, brand)
    except PendingLLMWork as e:
        print(str(e))
        print(f"\nSonuçlar yazıldıktan sonra: python run.py {stage} --brand {brand.slug}")
        sys.exit(3)


if __name__ == "__main__":
    main()
