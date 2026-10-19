import re
from llm import ask

CHECK_SYS = (
    "You are a strict fact checker. You are given a SOURCE text and a CLAIM. "
    "Decide whether the SOURCE clearly supports the CLAIM. "
    "Reply with exactly one word: SUPPORTED or UNSUPPORTED."
)

def check_claim(claim, source_text):
    out = ask(
        CHECK_SYS,
        "SOURCE:\n" + source_text[:3000] + "\n\nCLAIM:\n" + claim,
        max_tokens=10,
    ).upper()
    if "UNSUPPORTED" in out:
        return False
    return "SUPPORTED" in out

def extract_claims(text):
    claims = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        nums = []
        for grp in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", s):
            nums += [int(x) for x in re.findall(r"\d+", grp)]
        if nums:
            claims.append((s.strip(), nums))
    return claims

def verify_report(body, by_n, log=print):
    claims = extract_claims(body)
    log("[Verifier] checking " + str(len(claims)) + " cited claims...")
    results = []
    for claim, nums in claims:
        ok = False
        for n in nums:
            text = by_n.get(n, "")
            if text and check_claim(claim, text):
                ok = True
                break
        results.append((claim, nums, ok))
    return results
