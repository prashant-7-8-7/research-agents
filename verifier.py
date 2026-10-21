import re
from llm import ask
from evidence import select_evidence

CHECK_SYS = (
    "You are a strict fact checker. You are given a SOURCE text and a CLAIM. "
    "Decide whether the SOURCE clearly supports the CLAIM. "
    "Reply with exactly one word: SUPPORTED or UNSUPPORTED."
)

DIRECTION_SYS = """You verify claims against a source. Reply in exactly this format:
QUOTE: <the single source sentence closest to the claim, copied exactly, or NONE>
REASON: <one short sentence: do the figures, names and direction (higher/lower, more/less, increase/decrease, positive/negative) in the claim match the quote?>
VERDICT: SUPPORTED or UNSUPPORTED
Say SUPPORTED only if the quote states the same facts in the same direction. If the claim reverses, exaggerates or changes any figure, say UNSUPPORTED. If no sentence addresses the claim, say UNSUPPORTED."""

def check_claim_basic(claim, source_text):
    out = ask(
        DIRECTION_SYS,
        "SOURCE:\n" + select_evidence(claim, source_text) + "\n\nCLAIM:\n" + claim,
        max_tokens=250,
    )
    verdict = ""
    for line in out.splitlines():
        if line.strip().upper().startswith("VERDICT"):
            verdict = line.upper()
    return "UNSUPPORTED" not in verdict and "SUPPORTED" in verdict

DIR_PAIRS = [
    ("reduces", "increases"), ("reduce", "increase"), ("reducing", "increasing"),
    ("increases", "reduces"), ("increase", "reduce"), ("higher", "lower"),
    ("lower", "higher"), ("more", "less"), ("less", "more"),
    ("improves", "worsens"), ("prevents", "causes"), ("prevent", "cause"),
    ("mandates", "prohibits"), ("requires", "forbids"), ("benefits", "harms"),
    ("positive", "negative"), ("growth", "decline"), ("expanded", "shrank"),
    ("expansion", "contraction"),
]
OPP = {}
for _a, _b in DIR_PAIRS:
    OPP.setdefault(_a, _b)
DIR_RE = re.compile(r"\b(" + "|".join(OPP) + r")\b", re.I)

def _fill(src, template, w1, w2):
    q = ("SOURCE:\n" + select_evidence(template, src) + "\n\nFill the blank with the word the source supports. "
         "Options: " + w1 + " or " + w2 + ".\n\nSTATEMENT: " + template + "\n\nAnswer with one word only.")
    out = ask("You answer with exactly one word.", q, max_tokens=5).lower()
    if w1 in out and w2 not in out:
        return w1
    if w2 in out and w1 not in out:
        return w2
    return "?"


def check_claim(claim, source_text):
    if not check_claim_basic(claim, source_text):
        return False
    return direction_check(claim, source_text)

def extract_claims(text):
    claims = []
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        nums = []
        for grp in re.findall(r"\[(\d+(?:\s*,\s*\d+)*)\]", s):
            nums += [int(x) for x in re.findall(r"\d+", grp)]
        if nums:
            claims.append((s.strip(), nums))
    return claims

def verify_report_old(body, by_n, log=print):
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


def _vote(fn, claim, text, n=3):
    return sum(1 for _ in range(n) if fn(claim, text))


def _tf(src, claim, order):
    q = ("SOURCE:\n" + select_evidence(claim, src) + "\n\nSTATEMENT: " + claim +
         "\n\nBased only on the source, is the statement " + order + "? Answer with one word only.")
    out = ask("You answer with exactly one word.", q, max_tokens=5).lower()
    if "true" in out and "false" not in out:
        return "true"
    if "false" in out and "true" not in out:
        return "false"
    return "?"

def tf_check(claim, source_text):
    a = _tf(source_text, claim, "TRUE or FALSE")
    b = _tf(source_text, claim, "FALSE or TRUE")
    return a == "true" and b == "true"

def _grade(claim, text):
    b = _vote(check_claim_basic, claim, text)
    if b == 0:
        return "no"
    d = _vote(direction_check, claim, text)
    if d == 0:
        return "no"
    t = _vote(tf_check, claim, text)
    if t == 0:
        return "no"
    if b >= 2 and d >= 2 and t >= 2:
        return "yes"
    return "unsure"


NEG_RE = re.compile(r"\b(not|no|never|neither|nor|cannot|without)\b|n't", re.I)

def _negs(s):
    return {m.group(0).lower() for m in NEG_RE.finditer(s)}

def neg_flag(claim, texts):
    have = set()
    for t in texts:
        have |= _negs(t)
    return sorted(_negs(claim) - have)

def direction_check(claim, source_text):
    m = DIR_RE.search(claim)
    if not m:
        return True
    word = m.group(1).lower()
    opp = OPP[word]
    before = claim[:m.start()].split()[-6:]
    after = claim[m.end():].split()[:6]
    template = " ".join(before) + " ___ " + " ".join(after)
    a1 = _fill(source_text, template, word, opp)
    a2 = _fill(source_text, template, opp, word)
    return a1 == word and a2 == word


def _verify_report_core(body, by_n, log=print):
    claims = extract_claims(body)
    log("[Verifier] checking " + str(len(claims)) + " cited claims...")
    results = []
    for claim, nums in claims:
        texts = [by_n.get(n, "") for n in nums]
        texts = [t for t in texts if t]
        if not texts:
            log("  UNSUPPORTED (no source text) " + str(nums) + ": " + claim[:80])
            results.append((claim, nums, False))
            continue
        ok_num, missing = numbers_ok(claim, texts)
        if not ok_num:
            log("  UNSUPPORTED (figure not in source: " + ", ".join(missing) + ") " + str(nums) + ": " + claim[:80])
            results.append((claim, nums, False))
            continue
        nf = neg_flag(claim, texts)
        if nf:
            log("  CANT VERIFY (negation not in source: " + ", ".join(nf) + ") " + str(nums) + ": " + claim[:80])
            results.append((claim, nums, False))
            continue
        grades = [_grade(claim, t) for t in texts]
        if "yes" in grades:
            results.append((claim, nums, True))
        elif "unsure" in grades:
            log("  CANT VERIFY " + str(nums) + ": " + claim[:80])
            results.append((claim, nums, False))
        else:
            log("  UNSUPPORTED " + str(nums) + ": " + claim[:80])
            results.append((claim, nums, False))
    return results


_CITE_RE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")
_NAME_STOP = {"the","this","these","those","additionally","however","furthermore","for","under","while","such","in","as","with","its","it","a","an","some","many","both","also","moreover","overall","despite","although","to","by","from","one","other","they","there","each","several","most","key"}

def name_flag(claim, texts):
    s = _CITE_RE.sub(" ", claim)
    src = " ".join(texts).lower()
    missing = []
    for m in re.finditer(r"(?<![.!?] )(?<!^)\b[A-Z][A-Za-z]{2,}\b", s):
        w = m.group().lower()
        if w in _NAME_STOP:
            continue
        if w[:5] not in src and w not in missing:
            missing.append(w)
    return missing


def verify_report(body, by_n, log=print):
    claims = extract_claims(body)
    log("[Verifier] checking " + str(len(claims)) + " cited claims...")
    results = []
    for claim, nums in claims:
        texts = [by_n.get(n, "") for n in nums]
        texts = [t for t in texts if t]
        if texts:
            nm = name_flag(claim, texts)
            if nm:
                log("  CANT VERIFY (name not in source: " + ", ".join(nm) + ") " + str(nums) + ": " + claim[:80])
                results.append((claim, nums, False))
                continue
        res = _verify_report_core(claim, by_n, log=lambda m: None if "checking 1 cited" in m else log(m))
        results.append((claim, nums, bool(res) and all(r[2] for r in res)))
    return results


def _chunks(s):
    s = re.sub(r"\[\d+(?:\s*,\s*\d+)*\]", " ", s)
    s = re.sub(r"(\d)\s*[\u2013-]\s*[$\u20b9]?\s*(\d)", r"\1 \2", s)
    out = set()
    for w in s.split():
        if re.search(r"\d", w):
            w = w.strip(".,;:()\"'").lower().replace(",", "")
            w = w.replace("\u20b9", "").replace("rs.", "").replace("$", "")
            w = re.sub(r"/[a-z]+$", "", w)
            if w:
                out.add(w)
    return out

def numbers_ok(claim, texts):
    src = " ".join(texts).lower().replace(",", "")
    src = re.sub(r"(\d)\s*[\u2013-]\s*[$\u20b9]?\s*(\d)", r"\1 \2", src)
    missing = []
    for c in _chunks(claim):
        if not re.search(r"(?<![\d\w])" + re.escape(c) + r"(?!\d)", src):
            missing.append(c)
    return (not missing), sorted(missing)

_range_fix = True
