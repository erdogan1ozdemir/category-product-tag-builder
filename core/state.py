"""Marka başına workspace/: dizinler, JSONL append/okuma, atomik JSON yazımı."""
import json
import os

SUBDIRS = ("input", "products", "pools", "pending_llm", "tagged", "combos", "exports")


class Workspace:
    def __init__(self, brand_slug: str, root: str = "workspace"):
        self.root = os.path.join(root, brand_slug)

    def ensure(self):
        for d in SUBDIRS:
            os.makedirs(os.path.join(self.root, d), exist_ok=True)
        return self

    def path(self, relpath: str) -> str:
        return os.path.join(self.root, relpath)

    def append_jsonl(self, relpath: str, obj: dict):
        p = self.path(relpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def read_jsonl(self, relpath: str) -> list:
        p = self.path(relpath)
        if not os.path.exists(p):
            return []
        out = []
        with open(p, encoding="utf-8") as f:
            lines = f.readlines()
        # Find indices of non-empty lines
        nonempty = [(i, ln.strip()) for i, ln in enumerate(lines) if ln.strip()]
        for idx, (i, line) in enumerate(nonempty):
            lineno = i + 1  # 1-based line number
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                is_last = idx == len(nonempty) - 1
                if is_last:
                    # Truncated write on last line — skip silently
                    break
                raise ValueError(
                    f"Bozuk JSONL satırı: {p} satır {lineno}"
                ) from exc
        return out

    def processed_ids(self, relpath: str, key: str = "id") -> set:
        return {r[key] for r in self.read_jsonl(relpath) if key in r}

    def write_json(self, relpath: str, obj):
        p = self.path(relpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)

    def read_json(self, relpath: str, default=None):
        p = self.path(relpath)
        if not os.path.exists(p):
            return default
        with open(p, encoding="utf-8") as f:
            return json.load(f)
