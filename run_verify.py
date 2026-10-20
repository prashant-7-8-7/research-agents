import json
import sys
from pathlib import Path
from verifier import verify_report
p = Path(sys.argv[1])
body = p.read_text(encoding="utf-8").partition("## Sources")[0]
d = json.loads(p.with_suffix(".sources.json").read_text(encoding="utf-8"))
by_n = {int(k): v["text"] for k, v in d.items()}
res = verify_report(body, by_n)
print("Supported:", sum(1 for r in res if r[2]), "of", len(res))
