import json
import random
import re
import sys
from pathlib import Path
from verifier import extract_claims, check_claim, verify_report

random.seed(1)
p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
body, _, _ = text.partition("## Sources")
data = json.loads(p.with_suffix(".sources.json").read_text(encoding="utf-8"))
by_n = {int(k): v["text"] for k, v in data.items()}

CITE = r"(\[\d+(?:\s*,\s*\d+)*\])"
NUM = re.compile(r"\d+(?:\.\d+)?")
SWAPS = [
    ("reduces", "increases"), ("reduce", "increase"), ("reducing", "increasing"),
    ("increases", "reduces"), ("increase", "reduce"), ("higher", "lower"),
    ("lower", "higher"), ("more", "less"), ("less", "more"),
    ("improves", "worsens"), ("prevents", "causes"), ("prevent", "cause"),
    ("significant", "negligible"), ("mandates", "prohibits"),
    ("requires", "forbids"), ("benefits", "harms"), ("positive", "negative"),
    ("growth", "decline"), ("expanded", "shrank"), ("expansion", "contraction"),
]

def alter(claim):
    parts = re.split(CITE, claim)
    for i, part in enumerate(parts):
        if re.fullmatch(CITE, part):
            continue
        for m in NUM.finditer(part):
            v = float(m.group())
            if 1900 <= v <= 2100:
                continue
            if v == 50:
                nv = 17
            elif v <= 100:
                nv = 100 - v
            else:
                nv = v * 3
            s = str(int(nv)) if float(nv).is_integer() else str(round(nv, 2))
            parts[i] = part[:m.start()] + s + part[m.end():]
            return "".join(parts), "number"
    for i, part in enumerate(parts):
        if re.fullmatch(CITE, part):
            continue
        for a, b in SWAPS:
            m = re.search(r"\b" + a + r"\b", part)
            if m:
                parts[i] = part[:m.start()] + b + part[m.end():]
                return "".join(parts), "word swap"
    return None

def verdict(claim, nums):
    res = verify_report(claim, by_n, log=lambda m: None)
    return bool(res) and all(r[2] for r in res)

claims = [(c, n) for c, n in extract_claims(body) if alter(c)]
random.shuffle(claims)
print("Claims that can be altered:", len(claims))
print()

tested = caught = 0
by_kind = {}
for claim, nums in claims[:20]:
    if not verdict(claim, nums):
        print("SKIPPED (original not supported):", claim[:90])
        print()
        continue
    fake, kind = alter(claim)
    ok = verdict(fake, nums)
    tested += 1
    by_kind.setdefault(kind, [0, 0])
    by_kind[kind][1] += 1
    if not ok:
        caught += 1
        by_kind[kind][0] += 1
    print("ORIGINAL:", claim[:150])
    print("PLANTED (" + kind + "):", fake[:150], "->", "MISSED" if ok else "caught")
    print()

print("Planted errors caught:", caught, "of", tested)
for k, (c, t) in by_kind.items():
    print("  " + k + ":", c, "of", t)
