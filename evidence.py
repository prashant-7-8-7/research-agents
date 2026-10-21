"""Pick a claim-relevant excerpt from a long saved source for local LLM checks.

This is lexical retrieval, NOT verification or proof of support. The existing
Verifier still checks numbers, negation, names, and uses its model judgments.
Only the model-facing context is changed; the full source remains available to
rule-based checks. No dependencies beyond the Python standard library.
"""

import math
import re
from collections import Counter

_CITE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")
_WORD = re.compile(r"[a-z]+|\d+(?:\.\d+)?", re.I)
_STOP = set("""a an and are as at be been being by can could each for from had has
have in into is it its of on or our that the their them there these they this
those to was were which while who will with would also such more most many
some other under over than then only through about among across additionally
however furthermore mission initiative document report india indian government
national green hydrogen energy sector sectors""".split())


def _terms(text):
    clean = _CITE.sub(" ", text.lower())
    return {word for word in _WORD.findall(clean)
            if any(ch.isdigit() for ch in word)
            or (len(word) >= 3 and word not in _STOP)}


def select_evidence(claim, source_text, limit=3000, stride=1100):
    """Return at most ``limit`` source characters relevant to ``claim``.

    For short sources, preserve them exactly. For long ones, score overlapping
    windows by shared informative terms. Important numerals have extra weight.
    A high-scoring passage is only a candidate, never evidence of truth by itself.
    """
    if len(source_text) <= limit:
        return source_text
    if limit <= 0 or stride <= 0:
        raise ValueError("limit and stride must be positive")
    query = _terms(claim)
    if not query:
        return source_text[:limit]

    starts = sorted(set(range(0, len(source_text) - limit + 1, stride))
                    | {len(source_text) - limit})
    windows = [source_text[start:start + limit] for start in starts]
    sets = [_terms(window) & query for window in windows]
    counts = Counter(term for group in sets for term in group)

    def score(terms):
        return sum((5 if any(c.isdigit() for c in term) else 1)
                   * (1 + math.log((len(windows) + 1) / (counts[term] + 1)))
                   for term in terms)

    winner = max(range(len(starts)), key=lambda i: (score(sets[i]), -starts[i]))
    return windows[winner]
