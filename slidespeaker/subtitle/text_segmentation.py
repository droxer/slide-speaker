"""
Multilingual sentence segmentation utilities (subtitle package).
"""

import re

_ASCII_ENDERS = ".!?;"
_CJK_ENDERS = "。！？；"


def split_sentences(text: str, max_fallback_len: int = 60) -> list[str]:
    s = (text or "").strip()
    if not s:
        return []
    is_cjk = bool(
        re.search(
            r"[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]", s
        )
    )
    is_thai = bool(re.search(r"[\u0E00-\u0E7F]", s))

    if is_cjk:
        chunks = _split_by_chars(s, _CJK_ENDERS) or _split_by_soft_delims(s)
        return _fallback_chunking(chunks or [s], max_fallback_len)
    if is_thai:
        chunks = _split_ascii_with_abbrev(s)
        if not chunks or chunks == [s]:
            return _fallback_chunking([s], max_fallback_len)
        return _fallback_chunking(chunks, max_fallback_len)

    chunks = _split_ascii_with_abbrev(s)
    if not chunks:
        soft = _split_by_soft_delims(s)
        return _fallback_chunking(soft or [s], max_fallback_len)
    return _fallback_chunking(chunks, max_fallback_len)


def _split_by_chars(s: str, enders: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for ch in s:
        buf.append(ch)
        if ch in enders:
            seg = "".join(buf).strip()
            if seg:
                out.append(seg)
            buf = []
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _split_by_soft_delims(s: str) -> list[str]:
    parts = re.split(r"[，、：:;；,]", s)
    return [p.strip() for p in parts if p and p.strip()]


def _split_ascii_with_abbrev(s: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    n = len(s)
    i = 0
    while i < n:
        ch = s[i]
        buf.append(ch)
        if ch in _ASCII_ENDERS and i < n - 1:
            next_ch = s[i + 1]
            seg_preview = "".join(buf)
            if _looks_like_sentence_end(seg_preview, next_ch):
                seg = seg_preview.strip()
                if seg:
                    out.append(seg)
                buf = []
        i += 1
    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _looks_like_sentence_end(seg: str, next_ch: str) -> bool:
    if not (next_ch.isspace() or next_ch in "'\"»)）】】】]}"):
        return False
    last = seg.strip().rstrip(_ASCII_ENDERS).split()
    if not last:
        return True
    last_word = last[-1].lower().strip("'\"")
    common = {"mr", "mrs", "dr", "prof", "ms", "sr", "jr", "vs", "etc", "i.e", "e.g"}
    return not (last_word in common or len(last_word) <= 2)


def _fallback_chunking(chunks: list[str], max_len: int) -> list[str]:
    out: list[str] = []
    for c in chunks:
        cc = c.strip()
        if not cc:
            continue
        if len(cc) <= max_len:
            out.append(cc)
        else:
            start = 0
            while start < len(cc):
                end = min(len(cc), start + max_len)
                window = cc[start:end]
                if re.search(r"[A-Za-z]", window):
                    last_space = window.rfind(" ")
                    if last_space > 0:
                        end = start + last_space
                out.append(cc[start:end].strip())
                start = end
    return out
