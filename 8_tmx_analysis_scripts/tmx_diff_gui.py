#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

try:
    from lxml import etree
except ImportError:
    sys.exit("ERROR: lxml is required. Install it with: pip install lxml")


XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
INLINE_TAG_NAMES = {"bpt", "ept", "ph", "it", "hi", "ut", "sub"}
# Containers whose children, if also inline, indicate semantic inline nesting.
# - hi: a TMX 1.4 highlight wrapper around inline content.
# - sub: explicitly a subflow nested inside another inline element.
# - ph/it: TMX 1.4 placeholders that may legitimately contain <sub> subflows;
#   ph/sub and it/sub are standard nested-code constructs and must be detected
#   as nesting rather than as flat sibling sequences.
NESTING_CONTAINER_NAMES = {"hi", "sub", "ph", "it"}
SYSTEM_FIELDS = {
    "creationdate", "changedate", "usagecount", "creationid", "changeid",
    "datatype", "lastusagedate", "lastusedby",
}
MODES_REQUIRING_TWO_FILES = {"H0", "C0", "H1"}
MODE_MIN_FILES = {"H0": 2, "C0": 2, "H1": 2, "H2": 3, "H3": 5}
MODE_MAX_FILES = 5

# ---------------------------------------------------------------------------
# Judgement thresholds (centralised so the choice is documentable and tweakable
# for sensitivity analysis). Change here to test how robust the verdicts are.
# ---------------------------------------------------------------------------
SEVERE_LOSS_THRESHOLD = 90.0   # below this, an axis is considered severely degraded
NEAR_PERFECT_THRESHOLD = 98.0  # above this, an axis is considered effectively preserved


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NormalisationOptions:
    ignore_system_fields: bool = True
    normalise_lang_case: bool = True
    text_space_normalise: bool = True


@dataclass
class MatchPair:
    pre_index: int
    post_index: int
    method: str
    confidence: str
    score: float | None = None


@dataclass
class MatchResult:
    strategy_used: str
    tuid_overlap_ratio: float | None
    matched_count: int
    unmatched_pre_indices: list[int]
    unmatched_post_indices: list[int]
    duplicate_fingerprints_pre: int
    duplicate_fingerprints_post: int
    confidence: str
    method_counts: dict[str, int]
    low_confidence_count: int
    pairs: list[MatchPair]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def pct(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator * 100, 2)


def safe_pct(numerator: float, denominator: float) -> float | None:
    return pct(numerator, denominator) if denominator else None


def norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()[:16]


def clean_route(route: list[str]) -> str:
    safe = [re.sub(r"[^A-Za-z0-9_.-]+", "-", r.strip()) for r in route if r.strip()]
    return "_to_".join(safe) if safe else "route"


def fmt_score(v: Any) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def counter_intersection_count(a: Counter, b: Counter) -> int:
    return sum(min(a[k], b.get(k, 0)) for k in a)


def list_duplicate_count(items: list[str]) -> int:
    c = Counter(items)
    return sum(1 for _, n in c.items() if n > 1)


# ---------------------------------------------------------------------------
# TMX parsing
# ---------------------------------------------------------------------------

def parse_tmx(path: Path, options: NormalisationOptions) -> dict[str, Any]:
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    tree = etree.parse(str(path), parser)
    root = tree.getroot()
    header = root.find("header")
    body = root.find("body")

    header_fields = {}
    if header is not None:
        for k, v in header.attrib.items():
            if options.ignore_system_fields and k.lower() in SYSTEM_FIELDS:
                continue
            header_fields[k] = v

    tus = []
    if body is not None:
        for idx, tu_el in enumerate(body.findall("tu")):
            tus.append(parse_tu(tu_el, idx, options))

    return {
        "path": str(path),
        "header_fields": header_fields,
        "tus": tus,
    }


def parse_tu(tu_el: etree._Element, tu_idx: int, options: NormalisationOptions) -> dict[str, Any]:
    attribs = {}
    for k, v in tu_el.attrib.items():
        if options.ignore_system_fields and k.lower() in SYSTEM_FIELDS:
            continue
        attribs[k] = v

    props = []
    for p in tu_el.findall("prop"):
        p_type = p.get("type")
        p_text = norm_space("".join(p.itertext()))
        props.append({"type": p_type, "text": p_text})

    tuvs = []
    for tuv_el in tu_el.findall("tuv"):
        raw_lang = tuv_el.get(XML_LANG)
        norm_lang = raw_lang.lower() if raw_lang and options.normalise_lang_case else raw_lang
        seg_el = tuv_el.find("seg")
        seg_text = extract_visible_text(seg_el, options)
        pure_text = extract_pure_text(seg_el, options)
        tags = extract_tags(seg_el)
        tuvs.append({
            "lang": raw_lang,
            "lang_norm": norm_lang,
            "seg_text": seg_text,
            "pure_text": pure_text,
            "alignment_text": extract_alignment_text(seg_el, options),
            "tags": tags,
            "has_dom_nesting": detect_dom_nesting(seg_el),
            "pairing_profile": pairing_profile(tags),
            "tag_signature": tag_signature(tags),
        })

    tuid = tu_el.get("tuid")
    real_tuid = tuid if tuid else None

    tu = {
        "index": tu_idx,
        "tuid": real_tuid,
        "attribs": attribs,
        "props": props,
        "tuvs": tuvs,
    }
    tu["visible_text_fingerprint"] = visible_text_fingerprint(tu)
    tu["source_target_fingerprint"] = source_target_fingerprint(tu)
    tu["alignment_text_fingerprint"] = alignment_text_fingerprint(tu, include_language=True)
    tu["alignment_text_only_fingerprint"] = alignment_text_fingerprint(tu, include_language=False)
    tu["tag_fingerprint"] = short_hash("|".join(tag_signature([tag for tuv in tuvs for tag in tuv["tags"]])))
    return tu


def extract_visible_text(seg_el: etree._Element | None, options: NormalisationOptions) -> str:
    if seg_el is None:
        return ""
    text = "".join(seg_el.itertext())
    return norm_space(text) if options.text_space_normalise else text


def extract_pure_text(seg_el: etree._Element | None, options: NormalisationOptions) -> str:
    """
    Translatable text only — strips out content INSIDE format-placeholder tags
    (bpt/ept/ph/it/ut/sub) but preserves text inside <hi> which carries actual
    translatable content according to TMX 1.4.

    Example:
        <seg>WHEREAS the <bpt i='1'>&lt;b&gt;</bpt>park<ept i='1'>&lt;/b&gt;</ept>
             is in the <hi>public interest</hi>...</seg>
        -> "WHEREAS the park is in the public interest..."
           (bpt/ept inner "<b>" / "</b>" stripped; <hi> content preserved)
    """
    if seg_el is None:
        return ""

    # These tags hold format-placeholder strings (e.g. "<b>", "<br/>") whose
    # content is NOT translatable text. Strip their inner content.
    PLACEHOLDER_TAGS = {"bpt", "ept", "ph", "it", "ut", "sub"}
    # <hi> is different: its content IS translatable text. Keep it.

    parts: list[str] = []

    def walk(el: etree._Element, inside_placeholder: bool) -> None:
        if el.text and not inside_placeholder:
            parts.append(el.text)
        for child in el:
            child_local = etree.QName(child).localname
            now_inside = inside_placeholder or (child_local in PLACEHOLDER_TAGS)
            walk(child, now_inside)
            # tail text belongs to the parent's flow, NOT inside the child;
            # whether it's translatable depends on the parent's status.
            if child.tail and not inside_placeholder:
                parts.append(child.tail)

    walk(seg_el, inside_placeholder=False)
    joined = "".join(parts)
    return norm_space(joined) if options.text_space_normalise else joined


def extract_alignment_text(seg_el: etree._Element | None, options: NormalisationOptions) -> str:
    """Return a conservative TU identity string for cross-file alignment.

    This is intentionally separate from A2/A2b scoring. It removes code payloads
    from placeholder elements, preserves translatable ``hi``/``sub`` content,
    and ignores markup-like code that a tool has surfaced as plain text. The
    result is used only to identify corresponding TUs; it is never reported as
    evidence that visible text was retained.
    """
    if seg_el is None:
        return ""

    code_containers = {"bpt", "ept", "ph", "it", "ut"}
    translatable_containers = {"seg", "hi", "sub"}
    parts: list[str] = []

    def walk(el: etree._Element, text_visible: bool) -> None:
        local = etree.QName(el).localname
        own_text_visible = text_visible
        if local in code_containers:
            own_text_visible = False
        elif local in translatable_containers:
            own_text_visible = True

        if el.text and own_text_visible:
            parts.append(el.text)

        for child in el:
            child_local = etree.QName(child).localname
            child_visible = own_text_visible
            if child_local in code_containers:
                child_visible = False
            elif child_local in {"hi", "sub"}:
                child_visible = True
            walk(child, child_visible)
            if child.tail and own_text_visible:
                parts.append(child.tail)

    walk(seg_el, True)
    joined = "".join(parts)
    # Some tools surface escaped inline code as plain text (for example,
    # ``<a href=\"\">``). Ignore it for identity matching while leaving A2/A2b
    # untouched so that the transformation remains measurable there.
    joined = re.sub(r"<[^<>]*>", " ", joined)
    joined = joined.replace("{}", " ")
    joined = norm_space(joined) if options.text_space_normalise else joined
    return joined.casefold()


def extract_tags(seg_el: etree._Element | None) -> list[dict[str, Any]]:
    if seg_el is None:
        return []
    tags: list[dict[str, Any]] = []
    for el in seg_el.iter():
        if el is seg_el:
            continue
        local = etree.QName(el).localname
        if local in INLINE_TAG_NAMES:
            tags.append({
                "name": local,
                "attribs": dict(el.attrib),
                "text": norm_space("".join(el.itertext())),
            })
    return tags


def detect_dom_nesting(seg_el: etree._Element | None) -> bool:
    if seg_el is None:
        return False
    for el in seg_el.iter():
        if el is seg_el:
            continue
        local = etree.QName(el).localname
        if local in NESTING_CONTAINER_NAMES | {"bpt", "ept"}:
            for child in el.iterchildren():
                child_local = etree.QName(child).localname
                if child_local in INLINE_TAG_NAMES:
                    return True
    return False


def pairing_profile(tags: list[dict[str, Any]]) -> Counter:
    """Return a Counter of complete bpt/ept pairs indexed by the i attribute.

    A pair is "complete" when both a bpt and an ept share the same i value.
    The previous implementation iterated only over the bpt keys, which
    silently ignored orphan ept tags (ept with an i value that has no
    matching bpt). This version unions the i values from both sides so
    that orphans on either side correctly reduce the complete-pair count.
    """
    bpt = Counter()
    ept = Counter()
    for tag in tags:
        i = tag["attribs"].get("i")
        if i is None:
            continue
        if tag["name"] == "bpt":
            bpt[i] += 1
        elif tag["name"] == "ept":
            ept[i] += 1
    all_keys = set(bpt) | set(ept)
    return Counter({i: min(bpt.get(i, 0), ept.get(i, 0)) for i in all_keys})


def tag_signature(tags: list[dict[str, Any]]) -> list[str]:
    sigs = []
    for tag in tags:
        attrib = tag.get("attribs", {})
        key_parts = []
        for k in ("i", "x", "type", "pos", "assoc", "ctype"):
            if k in attrib:
                key_parts.append(f"{k}={attrib[k]}")
        sigs.append(f"{tag.get('name')}[{','.join(key_parts)}]")
    return sigs


def visible_text_fingerprint(tu: dict[str, Any]) -> str:
    langs = []
    for tuv in tu.get("tuvs", []):
        lang = (tuv.get("lang_norm") or tuv.get("lang") or "").lower()
        langs.append(f"{lang}:{tuv.get('seg_text','')}")
    return short_hash("||".join(langs))


def source_target_fingerprint(tu: dict[str, Any]) -> str:
    texts = [tuv.get("seg_text", "") for tuv in tu.get("tuvs", [])]
    return short_hash("||".join(texts))


def alignment_text_fingerprint(tu: dict[str, Any], *, include_language: bool) -> str:
    values = []
    for tuv in tu.get("tuvs", []):
        lang = (tuv.get("lang_norm") or tuv.get("lang") or "").lower()
        text = tuv.get("alignment_text", "")
        values.append((lang if include_language else "", text))
    # TUV order may be normalised by a tool, so identity matching is order-free.
    values.sort()
    return short_hash("||".join(f"{lang}:{text}" for lang, text in values))


def alignment_text_value(tu: dict[str, Any]) -> str:
    values = []
    for tuv in tu.get("tuvs", []):
        lang = (tuv.get("lang_norm") or tuv.get("lang") or "").lower()
        values.append((lang, tuv.get("alignment_text", "")))
    values.sort()
    return " || ".join(f"{lang}:{text}" for lang, text in values)


def alignment_token_counter(tu: dict[str, Any]) -> Counter:
    return Counter(re.findall(r"\w+", alignment_text_value(tu), flags=re.UNICODE))


def token_dice_similarity(left: Counter, right: Counter) -> float:
    total = sum(left.values()) + sum(right.values())
    if total == 0:
        return 1.0 if not left and not right else 0.0
    overlap = sum((left & right).values())
    return 2.0 * overlap / total


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

def match_tus(pre: dict[str, Any], post: dict[str, Any], strategy: str = "auto") -> MatchResult:
    pre_tus = pre["tus"]
    post_tus = post["tus"]

    if strategy not in {"auto", "tuid", "text", "position"}:
        raise ValueError(f"Unknown matching strategy: {strategy}")

    pre_tuids = {tu["tuid"] for tu in pre_tus if tu.get("tuid")}
    post_tuids = {tu["tuid"] for tu in post_tus if tu.get("tuid")}
    overlap_ratio = None
    if pre_tuids:
        overlap_ratio = round(len(pre_tuids & post_tuids) / len(pre_tuids), 4)

    chosen = strategy
    if strategy == "auto":
        chosen = "hybrid"

    if chosen == "tuid":
        pairs, unmatched_pre, unmatched_post = _match_by_tuid(pre_tus, post_tus)
        confidence = "high" if overlap_ratio and overlap_ratio >= 0.95 else "medium"
    elif chosen == "text":
        result = _match_hybrid(pre_tus, post_tus, use_tuid=False)
        pairs = result["pairs"]
        unmatched_pre = result["unmatched_pre"]
        unmatched_post = result["unmatched_post"]
        confidence = result["confidence"]
    elif chosen == "hybrid":
        result = _match_hybrid(pre_tus, post_tus, use_tuid=True)
        pairs = result["pairs"]
        unmatched_pre = result["unmatched_pre"]
        unmatched_post = result["unmatched_post"]
        confidence = result["confidence"]
    else:
        pairs, unmatched_pre, unmatched_post = _match_by_position(pre_tus, post_tus)
        confidence = "medium" if len(pre_tus) == len(post_tus) else "low"

    pre_fps = [tu["alignment_text_fingerprint"] for tu in pre_tus]
    post_fps = [tu["alignment_text_fingerprint"] for tu in post_tus]
    method_counts = Counter(pair.method for pair in pairs)
    low_confidence_count = sum(1 for pair in pairs if pair.confidence == "low")

    return MatchResult(
        strategy_used=chosen,
        tuid_overlap_ratio=overlap_ratio,
        matched_count=len(pairs),
        unmatched_pre_indices=unmatched_pre,
        unmatched_post_indices=unmatched_post,
        duplicate_fingerprints_pre=list_duplicate_count(pre_fps),
        duplicate_fingerprints_post=list_duplicate_count(post_fps),
        confidence=confidence,
        method_counts=dict(sorted(method_counts.items())),
        low_confidence_count=low_confidence_count,
        pairs=pairs,
    )


def _match_by_tuid(pre_tus: list[dict[str, Any]], post_tus: list[dict[str, Any]]) -> tuple[list[MatchPair], list[int], list[int]]:
    pre_by_tuid = defaultdict(list)
    post_by_tuid = defaultdict(list)
    for tu in pre_tus:
        if tu.get("tuid"):
            pre_by_tuid[tu["tuid"]].append(tu["index"])
    for tu in post_tus:
        if tu.get("tuid"):
            post_by_tuid[tu["tuid"]].append(tu["index"])

    pairs = []
    matched_pre = set()
    matched_post = set()
    for tuid, pre_indices in pre_by_tuid.items():
        post_indices = post_by_tuid.get(tuid, [])
        if len(pre_indices) == 1 and len(post_indices) == 1:
            pidx, qidx = pre_indices[0], post_indices[0]
            pairs.append(MatchPair(pidx, qidx, "tuid", "high"))
            matched_pre.add(pidx)
            matched_post.add(qidx)
    unmatched_pre = [tu["index"] for tu in pre_tus if tu["index"] not in matched_pre]
    unmatched_post = [tu["index"] for tu in post_tus if tu["index"] not in matched_post]
    return pairs, unmatched_pre, unmatched_post


def _match_hybrid(pre_tus: list[dict[str, Any]], post_tus: list[dict[str, Any]], *, use_tuid: bool) -> dict[str, Any]:
    """Cascade exact anchors, then align unresolved TUs without global index fallback."""
    pairs: list[MatchPair] = []
    used_pre: set[int] = set()
    used_post: set[int] = set()

    def add_unique_matches(key: str, method: str, confidence: str) -> None:
        pre_map = defaultdict(list)
        post_map = defaultdict(list)
        for tu in pre_tus:
            if tu["index"] not in used_pre and tu.get(key):
                pre_map[tu[key]].append(tu["index"])
        for tu in post_tus:
            if tu["index"] not in used_post and tu.get(key):
                post_map[tu[key]].append(tu["index"])
        for value, pre_indices in pre_map.items():
            post_indices = post_map.get(value, [])
            if len(pre_indices) == 1 and len(post_indices) == 1:
                pidx, qidx = pre_indices[0], post_indices[0]
                pairs.append(MatchPair(pidx, qidx, method, confidence))
                used_pre.add(pidx)
                used_post.add(qidx)

    if use_tuid:
        add_unique_matches("tuid", "tuid", "high")
    add_unique_matches("alignment_text_fingerprint", "alignment_text_fingerprint", "high")
    add_unique_matches("alignment_text_only_fingerprint", "alignment_text_only_fingerprint", "medium")
    add_unique_matches("visible_text_fingerprint", "seg_text_fingerprint", "medium")

    remaining_pre = [tu["index"] for tu in pre_tus if tu["index"] not in used_pre]
    remaining_post = [tu["index"] for tu in post_tus if tu["index"] not in used_post]
    sequence_pairs = _match_remaining_by_sequence(pre_tus, post_tus, remaining_pre, remaining_post)
    for pair in sequence_pairs:
        pairs.append(pair)
        used_pre.add(pair.pre_index)
        used_post.add(pair.post_index)

    pairs.sort(key=lambda pair: pair.pre_index)
    unmatched_pre = [tu["index"] for tu in pre_tus if tu["index"] not in used_pre]
    unmatched_post = [tu["index"] for tu in post_tus if tu["index"] not in used_post]
    coverage = len(pairs) / max(1, max(len(pre_tus), len(post_tus)))
    low_count = sum(1 for pair in pairs if pair.confidence == "low")
    if coverage >= 0.95 and low_count == 0:
        confidence = "high"
    elif coverage >= 0.80:
        confidence = "medium"
    else:
        confidence = "low"
    return {
        "pairs": pairs,
        "unmatched_pre": unmatched_pre,
        "unmatched_post": unmatched_post,
        "matched_count": len(pairs),
        "confidence": confidence,
    }


def _match_remaining_by_sequence(
    pre_tus: list[dict[str, Any]],
    post_tus: list[dict[str, Any]],
    pre_indices: list[int],
    post_indices: list[int],
    *,
    min_similarity: float = 0.58,
) -> list[MatchPair]:
    """Order-aware dynamic alignment for TUs whose identifiers/text were rewritten.

    Unlike raw position matching, a deletion creates a gap rather than shifting
    every subsequent pair. Matches below ``min_similarity`` are left unresolved.
    """
    if not pre_indices or not post_indices:
        return []

    n, m = len(pre_indices), len(post_indices)
    gap_penalty = -0.20
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    trace = [[""] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + gap_penalty
        trace[i][0] = "up"
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + gap_penalty
        trace[0][j] = "left"

    similarities: dict[tuple[int, int], float] = {}
    pre_tokens = {idx: alignment_token_counter(pre_tus[idx]) for idx in pre_indices}
    post_tokens = {idx: alignment_token_counter(post_tus[idx]) for idx in post_indices}
    for i in range(1, n + 1):
        pidx = pre_indices[i - 1]
        for j in range(1, m + 1):
            qidx = post_indices[j - 1]
            similarity = token_dice_similarity(pre_tokens[pidx], post_tokens[qidx])
            similarities[(i, j)] = similarity

            candidates = [
                (dp[i - 1][j] + gap_penalty, "up"),
                (dp[i][j - 1] + gap_penalty, "left"),
            ]
            if similarity >= min_similarity:
                candidates.append((dp[i - 1][j - 1] + similarity - 0.45, "diag"))
            dp[i][j], trace[i][j] = max(candidates, key=lambda item: item[0])

    pairs: list[MatchPair] = []
    i, j = n, m
    while i > 0 or j > 0:
        direction = trace[i][j]
        if direction == "diag":
            similarity = similarities[(i, j)]
            confidence = "high" if similarity >= 0.95 else "medium" if similarity >= 0.80 else "low"
            pairs.append(MatchPair(
                pre_indices[i - 1],
                post_indices[j - 1],
                "sequence_similarity",
                confidence,
                round(similarity, 4),
            ))
            i -= 1
            j -= 1
        elif direction == "up":
            i -= 1
        elif direction == "left":
            j -= 1
        else:
            break
    pairs.reverse()
    return pairs


def _match_by_fingerprint(pre_tus: list[dict[str, Any]], post_tus: list[dict[str, Any]]) -> dict[str, Any]:
    # Stage 1: visible text with language identity.
    pairs, used_pre, used_post = [], set(), set()
    for fp_key in ("visible_text_fingerprint", "source_target_fingerprint"):
        pre_map = defaultdict(list)
        post_map = defaultdict(list)
        for tu in pre_tus:
            if tu["index"] not in used_pre:
                pre_map[tu[fp_key]].append(tu["index"])
        for tu in post_tus:
            if tu["index"] not in used_post:
                post_map[tu[fp_key]].append(tu["index"])
        for fp, pre_indices in pre_map.items():
            post_indices = post_map.get(fp, [])
            if len(pre_indices) == 1 and len(post_indices) == 1:
                pi, qi = pre_indices[0], post_indices[0]
                pairs.append(MatchPair(pi, qi, fp_key, "high" if fp_key == "visible_text_fingerprint" else "medium"))
                used_pre.add(pi)
                used_post.add(qi)

    unmatched_pre = [tu["index"] for tu in pre_tus if tu["index"] not in used_pre]
    unmatched_post = [tu["index"] for tu in post_tus if tu["index"] not in used_post]
    confidence = "high" if len(pairs) >= int(min(len(pre_tus), len(post_tus)) * 0.95) else "medium"
    return {
        "pairs": pairs,
        "unmatched_pre": unmatched_pre,
        "unmatched_post": unmatched_post,
        "matched_count": len(pairs),
        "confidence": confidence,
    }


def _match_by_position(pre_tus: list[dict[str, Any]], post_tus: list[dict[str, Any]]) -> tuple[list[MatchPair], list[int], list[int]]:
    n = min(len(pre_tus), len(post_tus))
    pairs = [MatchPair(i, i, "position", "medium") for i in range(n)]
    return pairs, list(range(n, len(pre_tus))), list(range(n, len(post_tus)))


# ---------------------------------------------------------------------------
# Comparison / scoring
# ---------------------------------------------------------------------------

def compare_pair(pre_doc: dict[str, Any], post_doc: dict[str, Any], *, mode: str, route: list[str], match_strategy: str, options: NormalisationOptions, group: str = "") -> dict[str, Any]:
    match = match_tus(pre_doc, post_doc, match_strategy)
    pairs = match.pairs
    pre_tus = pre_doc["tus"]
    post_tus = post_doc["tus"]

    axes: dict[str, Any] = {}
    diagnostics: dict[str, Any] = {}

    # A1 TU count retention
    axes["A1_tu_count_retention"] = safe_pct(len(post_tus), len(pre_tus))
    diagnostics["tu_count_pre"] = len(pre_tus)
    diagnostics["tu_count_post"] = len(post_tus)

    # A2 text retention — two flavours:
    #   A2a (default A2): seg_text equality including text inside bpt/ept/ph/etc.
    #                    Sensitive to whether the tool preserved the original-format
    #                    representation that lived INSIDE bpt/ept (e.g. canonical
    #                    `<bpt>&lt;b&gt;</bpt>` vs Trados-emptied `<bpt/>`).
    #   A2b: pure translatable text only — tag inner content stripped.
    #        Reflects whether the actual translation text was preserved.
    #        A gap between A2a and A2b indicates the tool stripped formatting
    #        info from inside bpt/ept while keeping the surrounding sentence.
    src_tgt_total = 0
    src_tgt_same = 0
    pure_total = 0
    pure_same = 0
    for pair in pairs:
        ptu = pre_tus[pair.pre_index]
        qtu = post_tus[pair.post_index]
        n = max(len(ptu["tuvs"]), len(qtu["tuvs"]))
        for i in range(n):
            ptxt = ptu["tuvs"][i]["seg_text"] if i < len(ptu["tuvs"]) else None
            qtxt = qtu["tuvs"][i]["seg_text"] if i < len(qtu["tuvs"]) else None
            if ptxt is None:
                continue
            src_tgt_total += 1
            if ptxt == qtxt:
                src_tgt_same += 1
            # Pure text — strip tag inner content
            p_pure = ptu["tuvs"][i].get("pure_text", "") if i < len(ptu["tuvs"]) else None
            q_pure = qtu["tuvs"][i].get("pure_text", "") if i < len(qtu["tuvs"]) else None
            if p_pure is not None:
                pure_total += 1
                if p_pure == q_pure:
                    pure_same += 1
    axes["A2_text_retention"] = safe_pct(src_tgt_same, src_tgt_total)
    axes["A2b_pure_text_retention"] = safe_pct(pure_same, pure_total)
    diagnostics["text_units_compared"] = src_tgt_total
    diagnostics["text_units_same"] = src_tgt_same
    diagnostics["pure_text_units_same"] = pure_same

    pre_all_tags = flatten_tags(pre_tus)
    post_all_tags = flatten_tags(post_tus)
    pre_tag_count = len(pre_all_tags)
    post_tag_count = len(post_all_tags)

    # A3 tag count retention can exceed 100% if tools expand tags.
    axes["A3_inline_tag_count_retention"] = safe_pct(post_tag_count, pre_tag_count)
    axes["A3b_tag_introduction_ratio"] = safe_pct(max(0, post_tag_count - pre_tag_count), pre_tag_count)
    diagnostics["tag_count_pre"] = pre_tag_count
    diagnostics["tag_count_post"] = post_tag_count

    # A4 tag type retention — position-sensitive within matched TUs.
    # A type is "preserved" only if the SAME tag at the SAME position in pre
    # has the same element name as in post. Counts over matched TUs only.
    # The global multiset version is kept as A4b for diagnostic comparison —
    # it tells you whether the tool retained the right TYPES somewhere, even
    # if it shuffled their positions.
    type_position_total = 0
    type_position_same = 0
    for pair in pairs:
        ptu = pre_tus[pair.pre_index]
        qtu = post_tus[pair.post_index]
        for ptuv, qtuv in zip(ptu["tuvs"], qtu["tuvs"]):
            for ptag, qtag in zip(ptuv["tags"], qtuv["tags"]):
                type_position_total += 1
                if ptag["name"] == qtag["name"]:
                    type_position_same += 1
    axes["A4_inline_tag_type_retention"] = safe_pct(type_position_same, type_position_total)

    # A4b — global multiset intersection (position-blind). Diagnoses whether
    # the right tag types exist somewhere in the file, ignoring placement.
    pre_type_counter = Counter(tag["name"] for tag in pre_all_tags)
    post_type_counter = Counter(tag["name"] for tag in post_all_tags)
    axes["A4b_inline_tag_type_multiset_retention"] = safe_pct(
        counter_intersection_count(pre_type_counter, post_type_counter), pre_tag_count
    )
    diagnostics["tag_types_pre"] = dict(pre_type_counter)
    diagnostics["tag_types_post"] = dict(post_type_counter)
    diagnostics["tag_type_position_matched"] = type_position_total
    diagnostics["tag_type_position_same"] = type_position_same

    # A5 bpt/ept pairing retention
    pre_pairs = sum_pair_count(pre_tus)
    post_pairs = sum_pair_count(post_tus)
    axes["A5_bpt_ept_pairing_retention"] = safe_pct(post_pairs, pre_pairs)
    diagnostics["bpt_ept_pairs_pre"] = pre_pairs
    diagnostics["bpt_ept_pairs_post"] = post_pairs

    # A6 DOM-level nesting preservation over matched TUs that had nesting in pre.
    # Also: A6b — count of matched TUs where post has nesting that pre did not.
    # This catches tools that *introduce* nesting (e.g. memoQ wrapping content
    # in <bpt><sub>...</sub></bpt> dual-track structures).
    nested_pre = 0
    nested_preserved = 0
    nested_introduced = 0
    for pair in pairs:
        ptu = pre_tus[pair.pre_index]
        qtu = post_tus[pair.post_index]
        p_nested = any(tuv["has_dom_nesting"] for tuv in ptu["tuvs"])
        q_nested = any(tuv["has_dom_nesting"] for tuv in qtu["tuvs"])
        if p_nested:
            nested_pre += 1
            if q_nested:
                nested_preserved += 1
        elif q_nested:
            nested_introduced += 1
    axes["A6_dom_nesting_retention"] = safe_pct(nested_preserved, nested_pre)
    matched_count = len(pairs)
    axes["A6b_dom_nesting_introduction_ratio"] = safe_pct(nested_introduced, matched_count)
    diagnostics["nested_tus_pre_matched"] = nested_pre
    diagnostics["nested_tus_preserved"] = nested_preserved
    diagnostics["nested_tus_introduced_by_tool"] = nested_introduced

    # A7/A8 tag attribute key/value retention, position-sensitive within matched TUs.
    # Denominator is the TOTAL number of (pre tag position × attribute key) triples
    # in pre-side matched TUs — including positions where the post-side tag
    # is missing entirely (tag was deleted by the tool). This makes A7/A8
    # reflect both attribute loss AND tag-position loss correctly.
    attr_total = 0
    attr_key_same = 0
    attr_value_same = 0
    for pair in pairs:
        ptu = pre_tus[pair.pre_index]
        qtu = post_tus[pair.post_index]
        for tuv_idx, ptuv in enumerate(ptu["tuvs"]):
            qtuv = qtu["tuvs"][tuv_idx] if tuv_idx < len(qtu["tuvs"]) else None
            for tag_idx, ptag in enumerate(ptuv["tags"]):
                qtag = (
                    qtuv["tags"][tag_idx]
                    if qtuv is not None and tag_idx < len(qtuv["tags"])
                    else None
                )
                for k, v in ptag["attribs"].items():
                    attr_total += 1
                    if qtag is None:
                        # post-side tag at this position is missing — both key and value lost
                        continue
                    if k in qtag["attribs"]:
                        attr_key_same += 1
                        if qtag["attribs"][k] == v:
                            attr_value_same += 1
    axes["A7_attribute_key_retention"] = safe_pct(attr_key_same, attr_total)
    axes["A8_attribute_value_retention"] = safe_pct(attr_value_same, attr_total)
    diagnostics["attribute_triples_pre_matched"] = attr_total
    diagnostics["attribute_keys_retained"] = attr_key_same
    diagnostics["attribute_values_retained"] = attr_value_same

    # A9 header retention: presence + value.
    p_header = pre_doc["header_fields"]
    q_header = post_doc["header_fields"]
    p_keys, q_keys = set(p_header), set(q_header)
    retained_header_keys = p_keys & q_keys
    retained_header_values = {k for k in retained_header_keys if p_header[k] == q_header[k]}
    axes["A9a_header_field_presence_retention"] = safe_pct(len(retained_header_keys), len(p_keys)) if p_keys else 100.0
    axes["A9b_header_value_retention"] = safe_pct(len(retained_header_values), len(p_keys)) if p_keys else 100.0
    diagnostics["header_fields_lost"] = sorted(p_keys - q_keys)
    diagnostics["header_fields_added"] = sorted(q_keys - p_keys)
    diagnostics["header_fields_value_changed"] = sorted(k for k in retained_header_keys if p_header[k] != q_header[k])

    # A10 props: type and value retention over matched TUs.
    #
    # Two complementary granularities are computed:
    #   * A10a (soft / per-instance): counts every individual <prop> instance
    #     in the pre file and asks whether a matching type exists in the
    #     paired post TU. This is the headline radar axis: it scales
    #     gracefully when a TU retains some but not all of its prop types.
    #   * A10a_strict (per-TU all-or-nothing): a TU counts as retained only
    #     if every pre prop type in that TU is present in the post TU. This
    #     mirrors the strict reading in the axis definitions document and
    #     is exported as a diagnostic axis for boundary inspection.
    prop_type_total = 0
    prop_type_retained = 0
    prop_value_retained = 0
    tus_with_pre_props = 0
    tus_retaining_all_pre_prop_types = 0
    global_pre_prop_types, global_post_prop_types = set(), set()
    for tu in pre_tus:
        global_pre_prop_types.update(p["type"] for p in tu["props"] if p.get("type"))
    for tu in post_tus:
        global_post_prop_types.update(p["type"] for p in tu["props"] if p.get("type"))

    for pair in pairs:
        ptu = pre_tus[pair.pre_index]
        qtu = post_tus[pair.post_index]
        q_props_by_type = defaultdict(list)
        for prop in qtu["props"]:
            if prop.get("type"):
                q_props_by_type[prop["type"]].append(prop.get("text", ""))
        pre_types_in_tu = []
        for prop in ptu["props"]:
            ptype = prop.get("type")
            if not ptype:
                continue
            pre_types_in_tu.append(ptype)
            prop_type_total += 1
            if ptype in q_props_by_type:
                prop_type_retained += 1
                if prop.get("text", "") in q_props_by_type[ptype]:
                    prop_value_retained += 1
        if pre_types_in_tu:
            tus_with_pre_props += 1
            if all(t in q_props_by_type for t in pre_types_in_tu):
                tus_retaining_all_pre_prop_types += 1
    axes["A10a_prop_type_retention"] = safe_pct(prop_type_retained, prop_type_total)
    axes["A10a_strict_prop_type_retention_per_tu"] = safe_pct(
        tus_retaining_all_pre_prop_types, tus_with_pre_props
    )
    axes["A10b_prop_value_retention"] = safe_pct(prop_value_retained, prop_type_total)
    diagnostics["prop_types_lost_global"] = sorted(global_pre_prop_types - global_post_prop_types)
    diagnostics["prop_types_added_global"] = sorted(global_post_prop_types - global_pre_prop_types)
    diagnostics["prop_instances_pre_matched"] = prop_type_total
    diagnostics["tus_with_pre_props"] = tus_with_pre_props
    diagnostics["tus_retaining_all_pre_prop_types"] = tus_retaining_all_pre_prop_types

    # A11 language retention: strict + case-normalised.
    pre_lang_strict = collect_lang_instances(pre_doc, normalised=False)
    post_lang_strict = collect_lang_instances(post_doc, normalised=False)
    pre_lang_norm = collect_lang_instances(pre_doc, normalised=True)
    post_lang_norm = collect_lang_instances(post_doc, normalised=True)
    axes["A11a_language_strict_retention"] = safe_pct(counter_intersection_count(Counter(pre_lang_strict), Counter(post_lang_strict)), len(pre_lang_strict))
    axes["A11b_language_case_normalised_retention"] = safe_pct(counter_intersection_count(Counter(pre_lang_norm), Counter(post_lang_norm)), len(pre_lang_norm))

    # A12 tuid retention: independent of matching strategy.
    pre_tuids = {tu["tuid"] for tu in pre_tus if tu.get("tuid")}
    post_tuids = {tu["tuid"] for tu in post_tus if tu.get("tuid")}
    retained_tuids = pre_tuids & post_tuids
    axes["A12_tuid_retention"] = safe_pct(len(retained_tuids), len(pre_tuids)) if pre_tuids else None
    diagnostics["tuids_pre"] = len(pre_tuids)
    diagnostics["tuids_post"] = len(post_tuids)
    diagnostics["tuids_lost_sample"] = sorted(pre_tuids - post_tuids)[:20]
    diagnostics["tuids_added_sample"] = sorted(post_tuids - pre_tuids)[:20]

    per_tu = build_per_tu_rows(pre_tus, post_tus, match)
    transformations = detect_transformations(axes, diagnostics, match)
    judgement = interpret_pair(mode, axes, diagnostics, match, transformations)

    return {
        "mode": mode,
        "group": group,
        "route": route,
        "pre_path": pre_doc["path"],
        "post_path": post_doc["path"],
        "matching": asdict(match),
        "axis_scores": axes,
        "diagnostics": diagnostics,
        "detected_transformations": transformations,
        "judgement": judgement,
        "per_tu": per_tu,
    }


def flatten_tags(tus: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [tag for tu in tus for tuv in tu["tuvs"] for tag in tuv["tags"]]


def sum_pair_count(tus: list[dict[str, Any]]) -> int:
    total = 0
    for tu in tus:
        for tuv in tu["tuvs"]:
            total += sum(tuv["pairing_profile"].values())
    return total


def collect_lang_instances(doc: dict[str, Any], normalised: bool) -> list[str]:
    out = []
    header = doc["header_fields"]
    for k in ("adminlang", "srclang"):
        if k in header:
            v = header[k].lower() if normalised and isinstance(header[k], str) else header[k]
            out.append(f"{k}={v}")
    for tu in doc["tus"]:
        for tuv in tu["tuvs"]:
            lang = tuv.get("lang")
            if lang:
                out.append(f"xml:lang={lang.lower() if normalised else lang}")
    return out


def build_per_tu_rows(pre_tus: list[dict[str, Any]], post_tus: list[dict[str, Any]], match: MatchResult) -> list[dict[str, Any]]:
    rows = []
    matched_pre = set()
    matched_post = set()
    for pair in match.pairs:
        ptu = pre_tus[pair.pre_index]
        qtu = post_tus[pair.post_index]
        matched_pre.add(pair.pre_index)
        matched_post.add(pair.post_index)
        p_tags = flatten_tags([ptu])
        q_tags = flatten_tags([qtu])
        p_text = " || ".join(tuv["seg_text"] for tuv in ptu["tuvs"])
        q_text = " || ".join(tuv["seg_text"] for tuv in qtu["tuvs"])
        rows.append({
            "status": "MATCHED",
            "match_method": pair.method,
            "match_confidence": pair.confidence,
            "match_score": pair.score if pair.score is not None else "",
            "pre_index": pair.pre_index,
            "post_index": pair.post_index,
            "pre_tuid": ptu.get("tuid") or "",
            "post_tuid": qtu.get("tuid") or "",
            "tuid_changed": "Y" if (ptu.get("tuid") or "") != (qtu.get("tuid") or "") else "",
            "text_changed": "Y" if p_text != q_text else "",
            "pre_text_hash": short_hash(p_text),
            "post_text_hash": short_hash(q_text),
            "pre_tag_count": len(p_tags),
            "post_tag_count": len(q_tags),
            "tag_count_delta": len(q_tags) - len(p_tags),
            "pre_tag_types": ";".join(sorted(Counter(t["name"] for t in p_tags).elements())),
            "post_tag_types": ";".join(sorted(Counter(t["name"] for t in q_tags).elements())),
            "pre_langs": ";".join(tuv.get("lang") or "" for tuv in ptu["tuvs"]),
            "post_langs": ";".join(tuv.get("lang") or "" for tuv in qtu["tuvs"]),
            "prop_types_pre": ";".join(sorted(p["type"] for p in ptu["props"] if p.get("type"))),
            "prop_types_post": ";".join(sorted(p["type"] for p in qtu["props"] if p.get("type"))),
            "has_dom_nesting_pre": any(tuv["has_dom_nesting"] for tuv in ptu["tuvs"]),
            "has_dom_nesting_post": any(tuv["has_dom_nesting"] for tuv in qtu["tuvs"]),
        })
    for i in match.unmatched_pre_indices:
        ptu = pre_tus[i]
        rows.append({
            "status": "MISSING_IN_POST", "match_method": "", "match_confidence": "", "match_score": "",
            "pre_index": i, "post_index": "", "pre_tuid": ptu.get("tuid") or "", "post_tuid": "",
            "tuid_changed": "", "text_changed": "", "pre_text_hash": ptu["visible_text_fingerprint"], "post_text_hash": "",
            "pre_tag_count": len(flatten_tags([ptu])), "post_tag_count": "", "tag_count_delta": "",
            "pre_tag_types": ";".join(t["name"] for t in flatten_tags([ptu])), "post_tag_types": "",
            "pre_langs": ";".join(tuv.get("lang") or "" for tuv in ptu["tuvs"]), "post_langs": "",
            "prop_types_pre": ";".join(sorted(p["type"] for p in ptu["props"] if p.get("type"))), "prop_types_post": "",
            "has_dom_nesting_pre": any(tuv["has_dom_nesting"] for tuv in ptu["tuvs"]), "has_dom_nesting_post": "",
        })
    for i in match.unmatched_post_indices:
        qtu = post_tus[i]
        rows.append({
            "status": "ADDED_IN_POST", "match_method": "", "match_confidence": "", "match_score": "",
            "pre_index": "", "post_index": i, "pre_tuid": "", "post_tuid": qtu.get("tuid") or "",
            "tuid_changed": "", "text_changed": "", "pre_text_hash": "", "post_text_hash": qtu["visible_text_fingerprint"],
            "pre_tag_count": "", "post_tag_count": len(flatten_tags([qtu])), "tag_count_delta": "",
            "pre_tag_types": "", "post_tag_types": ";".join(t["name"] for t in flatten_tags([qtu])),
            "pre_langs": "", "post_langs": ";".join(tuv.get("lang") or "" for tuv in qtu["tuvs"]),
            "prop_types_pre": "", "prop_types_post": ";".join(sorted(p["type"] for p in qtu["props"] if p.get("type"))),
            "has_dom_nesting_pre": "", "has_dom_nesting_post": any(tuv["has_dom_nesting"] for tuv in qtu["tuvs"]),
        })
    return rows


def detect_transformations(axes: dict[str, Any], diagnostics: dict[str, Any], match: MatchResult) -> list[str]:
    flags = []
    if match.strategy_used != "tuid" and (match.tuid_overlap_ratio is not None and match.tuid_overlap_ratio < 0.8):
        flags.append("tuid_overlap_low_matching_fell_back_to_text_or_position")
    if axes.get("A12_tuid_retention") is not None and axes["A12_tuid_retention"] < 80:
        flags.append("tuid_removed_or_reassigned")
    if axes.get("A11a_language_strict_retention") != axes.get("A11b_language_case_normalised_retention"):
        flags.append("language_code_case_normalised")
    if diagnostics.get("prop_types_added_global"):
        flags.append("tool_specific_props_added")
    if diagnostics.get("prop_types_lost_global"):
        flags.append("pre_existing_props_removed_or_replaced")
    tag_pre = diagnostics.get("tag_count_pre", 0)
    tag_post = diagnostics.get("tag_count_post", 0)
    if tag_pre and tag_post > tag_pre * 1.10:
        flags.append("inline_tags_expanded_or_reencoded")
    if tag_pre and tag_post < tag_pre * 0.90:
        flags.append("inline_tags_compressed_or_deleted")
    if diagnostics.get("header_fields_value_changed"):
        flags.append("header_values_changed")
    if diagnostics.get("header_fields_added"):
        flags.append("header_fields_added")
    if diagnostics.get("header_fields_lost"):
        flags.append("header_fields_lost")
    if diagnostics.get("nested_tus_introduced_by_tool", 0) > 0:
        flags.append("nesting_introduced_by_tool")
    if match.duplicate_fingerprints_pre or match.duplicate_fingerprints_post:
        flags.append("duplicate_text_fingerprints_detected_matching_may_need_manual_check")
    # Matching desync warning: under positional matching, if text retention is
    # low, the matching is probably misaligned rather than the text genuinely
    # different. Same-content TUs that ended up at shifted positions look like
    # text loss. Flag this so downstream readers don't over-interpret A2/A2b.
    a2 = axes.get("A2_text_retention")
    if (match.strategy_used == "position"
            and a2 is not None and a2 < 80
            and (axes.get("A1_tu_count_retention") or 100) < 100):
        flags.append("matching_likely_desynced_due_to_segmentation_change")
    return flags


def mean_scores(keys: Iterable[str], axes: dict[str, Any]) -> float | None:
    vals = [axes[k] for k in keys if k in axes and isinstance(axes[k], (int, float))]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)


def interpret_pair(mode: str, axes: dict[str, Any], diagnostics: dict[str, Any], match: MatchResult, transformations: list[str]) -> dict[str, Any]:
    content = mean_scores(["A1_tu_count_retention", "A2_text_retention", "A11b_language_case_normalised_retention"], axes)
    structure = mean_scores(["A3_inline_tag_count_retention", "A4_inline_tag_type_retention", "A5_bpt_ept_pairing_retention", "A6_dom_nesting_retention", "A7_attribute_key_retention", "A8_attribute_value_retention"], axes)
    metadata = mean_scores(["A9a_header_field_presence_retention", "A9b_header_value_retention", "A10a_prop_type_retention", "A10b_prop_value_retention", "A12_tuid_retention"], axes)

    severe_core_issue = any(
        axes.get(k) is not None and axes.get(k) < SEVERE_LOSS_THRESHOLD
        for k in ["A1_tu_count_retention", "A2_text_retention", "A11b_language_case_normalised_retention"]
    )
    structure_issue = structure is not None and structure < SEVERE_LOSS_THRESHOLD
    metadata_issue = metadata is not None and metadata < SEVERE_LOSS_THRESHOLD

    if mode == "H0":
        if severe_core_issue or structure_issue:
            level = "high first-pass structural degradation"
        elif metadata_issue or transformations:
            level = "moderate first-pass transformation"
        else:
            level = "low first-pass loss"
    elif mode == "C0":
        if severe_core_issue or structure_issue:
            level = "fail"
        elif metadata_issue or transformations:
            level = "partial pass"
        else:
            level = "pass"
    elif mode == "H1":
        if severe_core_issue or structure_issue:
            level = "poor interoperability"
        elif metadata_issue or transformations:
            level = "partial interoperability"
        else:
            level = "good interoperability"
    else:
        if severe_core_issue or structure_issue:
            level = "unstable route segment"
        elif metadata_issue or transformations:
            level = "partially stable route segment"
        else:
            level = "stable route segment"

    rationale = []
    if content is not None:
        rationale.append(f"content-layer mean={content}")
    if structure is not None:
        rationale.append(f"structure-layer mean={structure}")
    if metadata is not None:
        rationale.append(f"metadata/identifier-layer mean={metadata}")
    if transformations:
        rationale.append("detected: " + ", ".join(transformations[:6]))
    if match.confidence != "high":
        rationale.append(f"matching confidence={match.confidence}; inspect per-TU CSV if needed")

    return {
        "level": level,
        "content_layer_mean": content,
        "structure_layer_mean": structure,
        "metadata_identifier_layer_mean": metadata,
        "rationale": "; ".join(rationale),
    }


# ---------------------------------------------------------------------------
# Mode controller
# ---------------------------------------------------------------------------

def run_experiment(mode: str, group: str, route: list[str], chain: list[Path], out_dir: Path, match_strategy: str = "auto", options: NormalisationOptions | None = None) -> dict[str, Any]:
    mode = mode.upper()
    if mode not in MODE_MIN_FILES:
        raise ValueError(f"Unsupported mode: {mode}")
    required = MODE_MIN_FILES[mode]
    if len(chain) < required:
        raise ValueError(f"{mode} requires at least {required} file(s); got {len(chain)}")
    if len(chain) > MODE_MAX_FILES:
        raise ValueError(f"Maximum {MODE_MAX_FILES} files are supported; got {len(chain)}")
    if len(route) != len(chain):
        # Route names are descriptive; auto-fill if user left them short.
        if not route:
            route = [f"node{i+1}" for i in range(len(chain))]
        elif len(route) < len(chain):
            route = route + [f"node{i+1}" for i in range(len(route), len(chain))]
        else:
            route = route[:len(chain)]

    options = options or NormalisationOptions()
    docs = [parse_tmx(path, options) for path in chain]

    step_results = []
    for i in range(len(docs) - 1):
        step_mode = mode
        step_route = [route[i], route[i + 1]]
        step_results.append(compare_pair(docs[i], docs[i + 1], mode=step_mode, route=step_route, match_strategy=match_strategy, options=options, group=group))

    end_to_end = None
    if len(docs) > 2:
        end_to_end = compare_pair(docs[0], docs[-1], mode=mode, route=[route[0], route[-1]], match_strategy=match_strategy, options=options, group=group)

    if mode in MODES_REQUIRING_TWO_FILES:
        overall = step_results[0]
    else:
        overall = {
            "mode": mode,
            "group": group,
            "route": route,
            "pre_path": str(chain[0]),
            "post_path": str(chain[-1]),
            "step_results": step_results,
            "end_to_end": end_to_end,
            "judgement": interpret_route(mode, step_results, end_to_end),
        }

    written = write_outputs(overall, mode, group, route, out_dir)
    overall["output_files"] = {k: str(v) for k, v in written.items()}
    return overall


def interpret_route(mode: str, step_results: list[dict[str, Any]], end_to_end: dict[str, Any] | None) -> dict[str, Any]:
    levels = [s["judgement"]["level"] for s in step_results]
    worst_step = None
    worst_value = 999.0
    for idx, res in enumerate(step_results):
        structure = res["judgement"].get("structure_layer_mean")
        content = res["judgement"].get("content_layer_mean")
        score = min(v for v in [structure, content] if v is not None) if any(v is not None for v in [structure, content]) else 999.0
        if score < worst_value:
            worst_value = score
            worst_step = idx + 1
    if mode == "H2":
        label = "round-trip preliminary"
    elif mode == "H3":
        label = "multi-hop preliminary"
    else:
        label = "route preliminary"
    return {
        "level": label,
        "step_levels": levels,
        "worst_step_index_1_based": worst_step,
        "note": "H2/H3 advanced recoverability and oscillation logic is not fully implemented in this version; use stepwise and end-to-end scores for interpretation.",
        "end_to_end_level": end_to_end["judgement"]["level"] if end_to_end else None,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def write_outputs(result: dict[str, Any], mode: str, group: str, route: list[str], out_dir: Path) -> dict[str, Path]:
    base = f"{mode}_{group or 'NA'}_{clean_route(route)}"
    # Create a per-run subfolder so the four/five output files of each run
    # stay together. Caller's `out_dir` becomes the parent directory.
    run_dir = out_dir / base
    run_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    summary_path = run_dir / f"summary_{base}.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(strip_per_tu_for_json(result), f, ensure_ascii=False, indent=2)
    paths["summary_json"] = summary_path

    if "step_results" in result:
        # Multi-file route: write one combined axis file and one trajectory.
        axis_path = run_dir / f"axis_{base}.csv"
        write_axis_route_csv(result, axis_path)
        paths["axis_csv"] = axis_path

        traj_path = run_dir / f"trajectory_{base}.csv"
        write_trajectory_csv(result, traj_path)
        paths["trajectory_csv"] = traj_path

        diag_path = run_dir / f"diagnostics_{base}.md"
        write_route_diagnostics_md(result, diag_path)
        paths["diagnostics_md"] = diag_path

        # Per-step per-TU files.
        for idx, step in enumerate(result["step_results"], start=1):
            per_path = run_dir / f"per_tu_{base}_step{idx}.csv"
            write_per_tu_csv(step.get("per_tu", []), per_path)
            paths[f"per_tu_step{idx}_csv"] = per_path
        if result.get("end_to_end"):
            per_path = run_dir / f"per_tu_{base}_end_to_end.csv"
            write_per_tu_csv(result["end_to_end"].get("per_tu", []), per_path)
            paths["per_tu_end_to_end_csv"] = per_path
    else:
        axis_path = run_dir / f"axis_{base}.csv"
        write_axis_pair_csv(result, axis_path)
        paths["axis_csv"] = axis_path

        per_tu_path = run_dir / f"per_tu_{base}.csv"
        write_per_tu_csv(result.get("per_tu", []), per_tu_path)
        paths["per_tu_csv"] = per_tu_path

        diag_path = run_dir / f"diagnostics_{base}.md"
        write_pair_diagnostics_md(result, diag_path)
        paths["diagnostics_md"] = diag_path

    return paths


def _compact_result_for_json(item: dict[str, Any]) -> dict[str, Any]:
    # Keep JSON readable; per-TU detail and full pair mappings are in CSV.
    clone = dict(item)
    clone.pop("per_tu", None)
    if isinstance(clone.get("matching"), dict):
        m = dict(clone["matching"])
        pair_count = len(m.get("pairs", [])) if isinstance(m.get("pairs"), list) else None
        m.pop("pairs", None)
        if pair_count is not None:
            m["pair_mapping_omitted_from_json_count"] = pair_count
        clone["matching"] = m
    return clone


def strip_per_tu_for_json(result: dict[str, Any]) -> dict[str, Any]:
    # Keep JSON readable; per-TU detail is in CSV.
    if "step_results" in result:
        clone = dict(result)
        clone["step_results"] = [_compact_result_for_json(step) for step in result["step_results"]]
        if clone.get("end_to_end"):
            clone["end_to_end"] = _compact_result_for_json(clone["end_to_end"])
        return clone
    return _compact_result_for_json(result)


def write_axis_pair_csv(result: dict[str, Any], path: Path) -> None:
    axes = result["axis_scores"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["axis", "score", "layer", "note"])
        writer.writeheader()
        for axis, score in axes.items():
            writer.writerow({"axis": axis, "score": score, "layer": axis_layer(axis), "note": axis_note(axis)})


def write_axis_route_csv(result: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["comparison", "axis", "score", "layer", "note"])
        writer.writeheader()
        for idx, step in enumerate(result["step_results"], start=1):
            comparison = f"step{idx}:{'->'.join(step['route'])}"
            for axis, score in step["axis_scores"].items():
                writer.writerow({"comparison": comparison, "axis": axis, "score": score, "layer": axis_layer(axis), "note": axis_note(axis)})
        if result.get("end_to_end"):
            for axis, score in result["end_to_end"]["axis_scores"].items():
                writer.writerow({"comparison": f"end_to_end:{'->'.join(result['end_to_end']['route'])}", "axis": axis, "score": score, "layer": axis_layer(axis), "note": axis_note(axis)})


def write_trajectory_csv(result: dict[str, Any], path: Path) -> None:
    axes = []
    for step in result["step_results"]:
        for axis in step["axis_scores"]:
            if axis not in axes:
                axes.append(axis)
    fieldnames = ["axis"] + [f"step{i+1}" for i in range(len(result["step_results"]))] + ["end_to_end", "trend"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for axis in axes:
            vals = [step["axis_scores"].get(axis) for step in result["step_results"]]
            row = {"axis": axis}
            for i, v in enumerate(vals, start=1):
                row[f"step{i}"] = v
            row["end_to_end"] = result["end_to_end"]["axis_scores"].get(axis) if result.get("end_to_end") else ""
            row["trend"] = classify_trend(vals)
            writer.writerow(row)


def classify_trend(vals: list[Any]) -> str:
    nums = [v for v in vals if isinstance(v, (int, float))]
    if len(nums) < 2:
        return "insufficient_data"
    if all(v >= NEAR_PERFECT_THRESHOLD for v in nums):
        return "stable_high"
    if nums[-1] < nums[0] - 10 and all(nums[i] >= nums[i + 1] for i in range(len(nums) - 1)):
        return "cumulative_degradation"
    if nums[0] - nums[1] > 10 and all(abs(nums[i] - nums[i + 1]) < 5 for i in range(1, len(nums) - 1)):
        return "one_time_loss_then_stable"
    if max(nums) - min(nums) > 10:
        return "oscillating_or_tool_specific_rewrite"
    return "minor_variation"


def write_per_tu_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as f:
            f.write("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_pair_diagnostics_md(result: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Diagnostics: {result['mode']} {' → '.join(result['route'])}\n\n")
        f.write(f"Pre: `{result['pre_path']}`\n\n")
        f.write(f"Post: `{result['post_path']}`\n\n")
        f.write("## Judgement\n\n")
        f.write(f"- Level: **{result['judgement']['level']}**\n")
        f.write(f"- Rationale: {result['judgement']['rationale']}\n\n")
        f.write("## Matching\n\n")
        m = result["matching"]
        f.write(f"- Strategy used: `{m['strategy_used']}`\n")
        f.write(f"- tuid overlap ratio: `{m['tuid_overlap_ratio']}`\n")
        f.write(f"- matched TU count: `{m['matched_count']}`\n")
        f.write(f"- match method counts: `{m.get('method_counts', {})}`\n")
        f.write(f"- low-confidence matched TUs: `{m.get('low_confidence_count', 0)}`\n")
        f.write(f"- confidence: `{m['confidence']}`\n\n")
        f.write("## Detected transformations\n\n")
        if result["detected_transformations"]:
            for item in result["detected_transformations"]:
                f.write(f"- {item}\n")
        else:
            f.write("- No major transformation flag detected.\n")
        f.write("\n## Axis scores\n\n")
        for k, v in result["axis_scores"].items():
            f.write(f"- {k}: {fmt_score(v)}\n")
        f.write("\n## Notes\n\n")
        f.write("A7/A8 attribute retention is position-sensitive within matched TUs. If a tool inserts or re-tokenises tags, inspect the per-TU CSV before treating low attribute scores as pure loss.\n")


def write_route_diagnostics_md(result: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write(f"# Route diagnostics: {result['mode']} {' → '.join(result['route'])}\n\n")
        f.write("## Route judgement\n\n")
        f.write(json.dumps(result["judgement"], ensure_ascii=False, indent=2))
        f.write("\n\n## Stepwise results\n\n")
        for idx, step in enumerate(result["step_results"], start=1):
            f.write(f"### Step {idx}: {' → '.join(step['route'])}\n\n")
            f.write(f"- Level: **{step['judgement']['level']}**\n")
            f.write(f"- Rationale: {step['judgement']['rationale']}\n")
            f.write(
                f"- Matching: {step['matching']['strategy_used']}, "
                f"confidence={step['matching']['confidence']}, "
                f"methods={step['matching'].get('method_counts', {})}, "
                f"low-confidence={step['matching'].get('low_confidence_count', 0)}\n"
            )
            if step["detected_transformations"]:
                f.write("- Transformations: " + ", ".join(step["detected_transformations"]) + "\n")
            f.write("\n")
        if result.get("end_to_end"):
            e = result["end_to_end"]
            f.write(f"## End-to-end: {' → '.join(e['route'])}\n\n")
            f.write(f"- Level: **{e['judgement']['level']}**\n")
            f.write(f"- Rationale: {e['judgement']['rationale']}\n")


def axis_layer(axis: str) -> str:
    if axis.startswith(("A1", "A2")):
        return "content"
    if axis.startswith(("A3", "A4", "A5", "A6", "A7", "A8")):
        return "structure"
    if axis.startswith(("A9", "A10")):
        return "metadata"
    if axis.startswith(("A11", "A12")):
        return "language_identifier"
    return "diagnostic"


def axis_note(axis: str) -> str:
    notes = {
        "A3b_tag_introduction_ratio": "Inverted diagnostic: lower is better; high value means tag expansion/introduction.",
        "A6b_dom_nesting_introduction_ratio": "Inverted diagnostic: lower is better; high value means artificial nesting introduced by the tool.",
        "A7_attribute_key_retention": "Position-sensitive within matched TUs.",
        "A8_attribute_value_retention": "Position-sensitive within matched TUs.",
        "A10a_prop_type_retention": "Per-instance soft score (headline radar axis). See A10a_strict for the all-or-nothing per-TU reading.",
        "A10a_strict_prop_type_retention_per_tu": "Per-TU all-or-nothing diagnostic: a TU counts as retained only if every pre prop type is present in the post TU.",
        "A11a_language_strict_retention": "Byte/case-sensitive language comparison.",
        "A11b_language_case_normalised_retention": "Language comparison after lowercasing language tags.",
    }
    return notes.get(axis, "")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def launch_gui() -> None:
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        sys.exit("ERROR: tkinter is not available on this Python installation.")

    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore
        TkBase = TkinterDnD.Tk
        dnd_available = True
    except Exception:
        DND_FILES = None
        TkBase = tk.Tk
        dnd_available = False

    root = TkBase()
    root.title("TMX Interoperability Experiment Analyser v3")
    root.geometry("920x720")
    root.minsize(860, 650)

    mode_var = tk.StringVar(value="H0")
    group_var = tk.StringVar(value="GA")
    route_var = tk.StringVar(value="canonical,memoQ")
    out_var = tk.StringVar(value="")
    match_var = tk.StringVar(value="auto")
    status_var = tk.StringVar(value="Ready.")
    file_vars = [tk.StringVar(value="") for _ in range(MODE_MAX_FILES)]

    mode_help = {
        "H0": "H0: canonical/R1 → Tool T1. First-pass input loss profile. Requires 2 files.",
        "C0": "C0: Tool T1 → same Tool T2. Same-tool stability baseline. Requires 2 files.",
        "H1": "H1: Tool1 output → Tool2 output. One-way migration interoperability. Requires 2 files.",
        "H2": "H2: Tool1 → Tool2 → Tool1′. Preliminary round-trip route analysis. Requires 3 files.",
        "H3": "H3: Tool1 → Tool2 → Tool3 → Tool2′ → Tool1′. Preliminary multi-hop analysis. Requires 5 files.",
    }

    def required_files() -> int:
        return MODE_MIN_FILES.get(mode_var.get(), 2)

    def update_mode_hint(*_: Any) -> None:
        status_var.set(mode_help.get(mode_var.get(), ""))
        # Route default suggestions.
        current = route_var.get().strip()
        defaults = {
            "H0": "canonical,memoQ",
            "C0": "memoQ,memoQ",
            "H1": "memoQ,Trados",
            "H2": "memoQ,Trados,memoQ",
            "H3": "memoQ,Trados,YiCAT,Trados,memoQ",
        }
        if current in {"", "canonical,memoQ", "memoQ,memoQ", "memoQ,Trados", "memoQ,Trados,memoQ", "memoQ,Trados,YiCAT,Trados,memoQ"}:
            route_var.set(defaults.get(mode_var.get(), current))

    main = ttk.Frame(root, padding=14)
    main.pack(fill="both", expand=True)

    title = ttk.Label(main, text="TMX Interoperability Experiment Analyser v3", font=("TkDefaultFont", 16, "bold"))
    title.pack(anchor="w", pady=(0, 8))

    # Step 1
    step1 = ttk.LabelFrame(main, text="Step 1: Choose experiment mode", padding=12)
    step1.pack(fill="x", pady=6)
    mode_row = ttk.Frame(step1)
    mode_row.pack(fill="x")
    for m in ["H0", "C0", "H1", "H2", "H3"]:
        ttk.Radiobutton(mode_row, text=m, variable=mode_var, value=m, command=update_mode_hint).pack(side="left", padx=(0, 16))
    ttk.Label(step1, textvariable=status_var, foreground="#444").pack(anchor="w", pady=(8, 0))

    meta_row = ttk.Frame(step1)
    meta_row.pack(fill="x", pady=(10, 0))
    ttk.Label(meta_row, text="Group:").pack(side="left")
    group_combo = ttk.Combobox(meta_row, textvariable=group_var, values=["GA", "GB", "GC", "NA"], width=8, state="readonly")
    group_combo.pack(side="left", padx=(6, 20))
    ttk.Label(meta_row, text="Route names, comma-separated:").pack(side="left")
    ttk.Entry(meta_row, textvariable=route_var, width=48).pack(side="left", padx=(6, 20))
    ttk.Label(meta_row, text="Match:").pack(side="left")
    ttk.Combobox(meta_row, textvariable=match_var, values=["auto", "tuid", "text", "position"], width=10, state="readonly").pack(side="left", padx=(6, 0))

    # Step 2
    step2 = ttk.LabelFrame(main, text="Step 2: Add TMX files in comparison order", padding=12)
    step2.pack(fill="both", expand=True, pady=6)
    hint_text = "Drag .tmx files onto a row, or use Pick. For H0/C0/H1 only rows 1–2 are required; rows 3–5 may remain empty."
    if not dnd_available:
        hint_text += " Drag-and-drop is disabled because tkinterdnd2 is not installed; Pick buttons still work."
    ttk.Label(step2, text=hint_text, foreground="#444", wraplength=820).pack(anchor="w", pady=(0, 8))

    rows_frame = ttk.Frame(step2)
    rows_frame.pack(fill="both", expand=True)

    def pick_file(i: int) -> None:
        initial = Path(file_vars[i - 1].get()).parent if file_vars[i - 1].get() else Path.cwd()
        path = filedialog.askopenfilename(
            title=f"Pick TMX file {i}",
            filetypes=[("TMX files", "*.tmx"), ("All files", "*.*")],
            initialdir=str(initial) if initial.exists() else str(Path.cwd()),
        )
        if path:
            file_vars[i - 1].set(path)

    def clear_file(i: int) -> None:
        file_vars[i - 1].set("")

    def parse_drop_data(data: str) -> str:
        # Tk DND can produce {path with spaces} or a plain path.
        data = data.strip()
        if data.startswith("{") and data.endswith("}"):
            data = data[1:-1]
        # If several files were dropped, take the first.
        if "} {" in data:
            data = data.split("} {")[0].lstrip("{")
        return data

    for i in range(1, MODE_MAX_FILES + 1):
        row = ttk.Frame(rows_frame)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=f"File {i}", width=8).pack(side="left")
        entry = ttk.Entry(row, textvariable=file_vars[i - 1])
        entry.pack(side="left", fill="x", expand=True, padx=(4, 8))
        ttk.Button(row, text="Pick", command=lambda i=i: pick_file(i)).pack(side="left", padx=(0, 4))
        ttk.Button(row, text="Clear", command=lambda i=i: clear_file(i)).pack(side="left")
        if dnd_available:
            entry.drop_target_register(DND_FILES)  # type: ignore[name-defined]
            entry.dnd_bind("<<Drop>>", lambda event, i=i: file_vars[i - 1].set(parse_drop_data(event.data)))

    # Step 3
    step3 = ttk.LabelFrame(main, text="Step 3: Choose output folder", padding=12)
    step3.pack(fill="x", pady=6)
    out_row = ttk.Frame(step3)
    out_row.pack(fill="x")
    ttk.Entry(out_row, textvariable=out_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
    def pick_out() -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            out_var.set(path)
    ttk.Button(out_row, text="Pick output folder", command=pick_out).pack(side="left")

    # Run area
    run_frame = ttk.Frame(main)
    run_frame.pack(fill="x", pady=(10, 0))
    progress = ttk.Progressbar(run_frame, mode="indeterminate")
    progress.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def run_from_gui() -> None:
        mode = mode_var.get().upper()
        files = [Path(v.get()) for v in file_vars if v.get().strip()]
        required = required_files()
        if len(files) < required:
            messagebox.showerror("Missing files", f"{mode} requires at least {required} file(s). You selected {len(files)}.")
            return
        files = files[:MODE_MAX_FILES]
        for p in files:
            if not p.exists():
                messagebox.showerror("File not found", str(p))
                return
        out = Path(out_var.get()) if out_var.get().strip() else None
        if out is None:
            messagebox.showerror("Missing output folder", "Please choose an output folder in Step 3.")
            return
        route = [x.strip() for x in route_var.get().split(",") if x.strip()]
        try:
            progress.start(10)
            root.update_idletasks()
            result = run_experiment(
                mode=mode,
                group=group_var.get(),
                route=route,
                chain=files,
                out_dir=out,
                match_strategy=match_var.get(),
                options=NormalisationOptions(),
            )
            progress.stop()
            outputs = result.get("output_files", {})
            msg = "Run completed.\n\n" + "\n".join(f"{k}: {v}" for k, v in outputs.items())
            messagebox.showinfo("Completed", msg)
            status_var.set(f"Completed: {mode}. Outputs written to {out}")
        except Exception as exc:
            progress.stop()
            messagebox.showerror("Run failed", str(exc))
            status_var.set(f"Error: {exc}")

    ttk.Button(run_frame, text="Run analysis", command=run_from_gui).pack(side="right")

    footer = ttk.Label(main, text="Tip: for H0/C0/H1, only File 1 and File 2 are used. The route names should match the file order.", foreground="#555")
    footer.pack(anchor="w", pady=(8, 0))

    update_mode_hint()
    root.mainloop()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="TMX route-based interoperability analyser with GUI.")
    p.add_argument("--gui", action="store_true", help="Launch GUI even if CLI arguments are present.")
    p.add_argument("--mode", choices=["H0", "C0", "H1", "H2", "H3"], help="Experiment mode.")
    p.add_argument("--group", default="NA", help="Group label, e.g. GA, GB, GC.")
    p.add_argument("--route", default="", help="Comma-separated route names, e.g. canonical,memoQ.")
    p.add_argument("--chain", nargs="*", type=Path, help="Ordered TMX files in the route.")
    p.add_argument("--out", type=Path, help="Output folder.")
    p.add_argument("--match", choices=["auto", "tuid", "text", "position"], default="auto", help="TU matching strategy.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.gui or not args.mode:
        launch_gui()
        return
    if not args.chain:
        sys.exit("ERROR: --chain is required in CLI mode.")
    if not args.out:
        sys.exit("ERROR: --out is required in CLI mode.")
    for p in args.chain:
        if not p.exists():
            sys.exit(f"ERROR: file not found: {p}")
    route = [x.strip() for x in args.route.split(",") if x.strip()]
    result = run_experiment(
        mode=args.mode,
        group=args.group,
        route=route,
        chain=args.chain,
        out_dir=args.out,
        match_strategy=args.match,
        options=NormalisationOptions(),
    )
    print(json.dumps(result.get("output_files", {}), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
