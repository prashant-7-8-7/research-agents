import json
import random
import re
import sys
from pathlib import Path
from verifier import extract_claims, verify_report

random.seed(2)
p = Path(sys.argv[1])
body = p.read_text(encoding="utf-8").partition("## Sources")[0]
d = json.loads(p.with_suffix(".sources.json").read_text(encoding="utf-8"))
by_n = {int(k): v["text"] for k, v in d.items()}

CITE = r"(\[\d+(?:\s*,\s*\d+)*\])"
NEG = [(" is ", " is not "), (" are ", " are not "), (" has ", " has not "),
       (" have ", " have not "), (" will ", " will not ")]
ENT = ["Gujarat", "Punjab", "Kerala", "Assam", "Odisha", "Bihar"]

def variants(claim):
    out = []
    parts = re.split(CITE, claim)
    for i, part in enumerate(parts):
        if re.fullmatch(CITE, part):
            continue
        for a, b in NEG:
            if a in part and " not " not in part:
                q = list(parts)
                q[i] = part.replace(a, b, 1)
                out.append(("".join(q), "negation"))
                break
        m = re.search(r"(?<=[a-z,] )[A-Z][a-z]{3,}", part)
        if m:
            new = next((e for e in ENT if e not in claim), None)
            if new:
                q = list(parts)
                q[i] = part[:m.start()] + new + part[m.end():]
                out.append(("".join(q), "entity swap"))
    return out

def verdict(claim):
    res = verify_report(claim, by_n, log=lambda m: None)
    return bool(res) and all(r[2] for r in res)

cases = []
for claim, nums in extract_claims(body):
    for fake, kind in variants(claim):
        cases.append((claim, fake, kind))
random.shuffle(cases)
print("Alterable cases:", len(cases))
print()

tested = caught = 0
by_kind = {}
for claim, fake, kind in cases[:16]:
    if not verdict(claim):
        print("SKIPPED (original not supported):", claim[:90])
        continue
    ok = verdict(fake)
    tested += 1
    by_kind.setdefault(kind, [0, 0])
    by_kind[kind][1] += 1
    if not ok:
        caught += 1
        by_kind[kind][0] += 1
    print("PLANTED (" + kind + "):", fake[:150], "->", "MISSED" if ok else "caught")
    print()
print("Held-out caught:", caught, "of", tested)
for k, (c, t) in by_kind.items():
    print("  " + k + ":", c, "of", t)
