import random
import re
import sys
from pathlib import Path
from verifier import extract_claims

text = Path(sys.argv[1]).read_text(encoding="utf-8")
body, _, srcs = text.partition("## Sources")
urls = {}
for m in re.finditer(r"^\[(\d+)\] .* - (https?://\S+)\s*$", srcs, re.M):
    urls[int(m.group(1))] = m.group(2)

claims = extract_claims(body)
for claim, nums in random.sample(claims, min(5, len(claims))):
    print(claim[:300])
    for n in nums:
        print("    [" + str(n) + "]", urls.get(n, "?"))
    print()
