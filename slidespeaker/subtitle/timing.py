"""
Subtitle timing utilities (subtitle package).
"""

import re


def calculate_chunk_durations(
    total_duration: float,
    chunks: list[str],
    original_text: str,
    language: str | None = None,
) -> list[float]:
    if not chunks:
        return []
    if len(chunks) == 1:
        return [max(0.1, total_duration)]

    is_cjk = bool(
        re.search(
            r"[\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\uAC00-\uD7AF]",
            original_text,
        )
    )
    is_thai = bool(re.search(r"[\u0E00-\u0E7F]", original_text))
    lang = (language or "").lower()

    use_char_weight = (
        is_cjk
        or is_thai
        or lang
        in {
            "simplified_chinese",
            "traditional_chinese",
            "japanese",
            "korean",
            "thai",
        }
    )

    def token_weight(s: str) -> int:
        if use_char_weight:
            return max(1, len(re.sub(r"\s+", "", s)))
        return max(1, len(s.split()))

    weights = [token_weight(c) for c in chunks]
    total_w = sum(weights)
    if total_w <= 0:
        return [total_duration / len(chunks)] * len(chunks)

    durations = [total_duration * (w / total_w) for w in weights]

    min_dur = 1.2
    max_dur = 7.0
    if use_char_weight:
        min_cps, max_cps = 4.0, 12.0
    else:
        min_cps, max_cps = 10.0, 20.0

    nonspace_lens = [max(1, len(re.sub(r"\s+", "", c))) for c in chunks]
    lower_bounds = [max(min_dur, nl / max_cps) for nl in nonspace_lens]
    upper_bounds = [min(max_dur, nl / max(min_cps, 1e-6)) for nl in nonspace_lens]

    durations = [
        max(lb, min(d, ub))
        for d, lb, ub in zip(durations, lower_bounds, upper_bounds, strict=False)
    ]

    def renormalize(durs: list[float], total: float) -> list[float]:
        current = sum(durs)
        if current <= 0:
            return [total / len(durs)] * len(durs)
        scale = total / current
        durs = [d * scale for d in durs]
        for _ in range(2):
            deficit = 0.0
            for i, (d, lb) in enumerate(zip(durs, lower_bounds, strict=False)):
                if d < lb:
                    deficit += lb - d
                    durs[i] = lb
            if deficit > 0:
                adjustable = [
                    max(0.0, durs[i] - max(lower_bounds[i], 0.0))
                    for i in range(len(durs))
                ]
                total_adj = sum(adjustable)
                if total_adj > 1e-6:
                    for i in range(len(durs)):
                        if adjustable[i] > 0:
                            durs[i] -= deficit * (adjustable[i] / total_adj)
                current2 = sum(durs)
                if abs(current2 - total) > 1e-6:
                    s = total / max(current2, 1e-6)
                    durs = [d * s for d in durs]

            surplus = 0.0
            for i, (d, ub) in enumerate(zip(durs, upper_bounds, strict=False)):
                if d > ub:
                    surplus += d - ub
                    durs[i] = ub
            if surplus > 0:
                room = [max(0.0, upper_bounds[i] - durs[i]) for i in range(len(durs))]
                total_room = sum(room)
                if total_room > 1e-6:
                    for i in range(len(durs)):
                        if room[i] > 0:
                            durs[i] += surplus * (room[i] / total_room)
                current3 = sum(durs)
                if abs(current3 - total) > 1e-6:
                    s = total / max(current3, 1e-6)
                    durs = [d * s for d in durs]
        return durs

    return renormalize(durations, total_duration)
