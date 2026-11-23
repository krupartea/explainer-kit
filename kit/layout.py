"""Automatic layout check, run by NarratedScene at the end of every beat (the frame the contact sheet shows).
Exact, from mobject bounds, so the producer reads images only to judge the picture, not to hunt for layout bugs.

Reports, per beat:
- off-frame:   a visible mobject sticks out of the camera frame
- subtitles:   visible text below SAFE_BOTTOM (players draw the .srt there)
- overlap:     two visible text blocks overlap (labels on top of each other)
- tiny text:   text rendered below 80% of FS_SMALL, unless marked kit.depicted() (small print that is part of
               a pictured object, e.g. a product label)
"""
from __future__ import annotations

import numpy as np
from manim import Code, DecimalNumber, MarkupText, MathTex, Paragraph, SingleStringMathTex, Text, VMobject
from manim.mobject.svg.svg_mobject import VMobjectFromSVGPath

from kit import style

TEXTLIKE = (Text, MarkupText, Paragraph, MathTex, SingleStringMathTex, Code, DecimalNumber)
TOL = 0.05


def _visible(m) -> bool:
    fam = [x for x in m.get_family() if isinstance(x, VMobject) and len(x.points)]
    if not fam:
        return False
    return max(max(x.get_fill_opacity(), x.get_stroke_opacity() if x.get_stroke_width() > 0 else 0) for x in fam) > 0.05


def _texts(mobjects):
    """-> (text blocks, loose glyphs). Animating a few letters of a Text makes Manim split it into loose glyph
    mobjects; those still count, compared against whole text blocks."""
    out, loose = [], []

    def walk(m):
        if isinstance(m, TEXTLIKE):
            out.append(m)
            return
        if isinstance(m, VMobjectFromSVGPath) and not m.submobjects:
            loose.append(m)
            return
        for s in m.submobjects:
            walk(s)
    for m in mobjects:
        walk(m)
    return out, loose


def _depicted(m) -> bool:
    return bool(getattr(m, "_kit_depicted", False))


def _glyph_boxes(m):
    leaves = [x for x in m.get_family() if isinstance(x, VMobject) and len(x.points) and not x.submobjects]
    return [_box(x) for x in leaves] or [_box(m)]


def _hit(a, b) -> float:
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    if w <= 0 or h <= 0:
        return 0.0
    small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return w * h / small if small > 0 else 0.0


def _box(m):
    return np.array([m.get_left()[0], m.get_bottom()[1], m.get_right()[0], m.get_top()[1]])


def _label(m) -> str:
    t = getattr(m, "text", None) or getattr(m, "original_text", None) or getattr(m, "tex_string", None)
    if t is None and isinstance(m, DecimalNumber):
        t = f"{m.get_value():g}"
    return (str(t)[:24] if t else type(m).__name__).replace("\n", " ")


def check(scene, frame_center=(0.0, 0.0), frame_w=None, frame_h=None) -> list[str]:
    from manim import config
    fw, fh = frame_w or config.frame_width, frame_h or config.frame_height
    cx, cy = frame_center
    x0, x1, y0, y1 = cx - fw / 2, cx + fw / 2, cy - fh / 2, cy + fh / 2
    safe_bottom = y0 + (style.SAFE_BOTTOM + config.frame_height / 2) * fh / config.frame_height
    issues = []
    tops = [m for m in scene.mobjects if _visible(m)]
    texts, loose = _texts(tops)
    texts = [m for m in texts if _visible(m)]
    loose = [m for m in loose if _visible(m)]
    for m in texts + [m for m in tops if not isinstance(m, TEXTLIKE)]:   # text blocks + top-level shapes
        l, b, r, t = _box(m)
        if l < x0 - TOL or r > x1 + TOL or b < y0 - TOL or t > y1 + TOL:
            if (r - l) >= fw * 0.98 and (t - b) >= fh * 0.98:
                continue                                                # a deliberate full-frame backdrop
            issues.append(f"off-frame: {_label(m)} spans x {l:.1f}..{r:.1f}, y {b:.1f}..{t:.1f}")
    for m in texts:
        if m.get_bottom()[1] < safe_bottom - TOL and m.get_top()[1] > y0:
            issues.append(f"subtitles: '{_label(m)}' reaches y {m.get_bottom()[1]:.2f} (< {safe_bottom:.2f})")
        if isinstance(m, (Text, MarkupText)) and not isinstance(m, Paragraph):
            fs = getattr(m, "font_size", None)
            if fs is not None and not _depicted(m) and fs * config.frame_height / fh < 0.8 * style.FS_SMALL:
                issues.append(f"tiny text: '{_label(m)}' at font size {fs:.0f}")
    boxes = [(_box(m), m) for m in texts]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (a, ma), (b, mb) = boxes[i], boxes[j]
            if _hit(a, b) == 0:
                continue
            if _label(ma) == _label(mb) and np.allclose(a, b, atol=0.02):
                continue                                   # the same text drawn twice in place: invisible
            # glyph level, so rotated or ragged text isn't judged by its loose bounding box
            worst = max((_hit(ga, gb) for ga in _glyph_boxes(ma) for gb in _glyph_boxes(mb)), default=0.0)
            if worst > 0.10:
                issues.append(f"overlap: '{_label(ma)}' and '{_label(mb)}' (glyphs overlap {worst:.0%})")
    for m in texts:                                        # split texts' glyphs vs whole text blocks
        gm = _glyph_boxes(m)
        bm = _box(m)
        near = [g for g in loose if _hit(bm, _box(g)) > 0 and g not in m.get_family()]
        if near and max(_hit(ga, _box(g)) for ga in gm for g in near) > 0.10:
            c = np.mean([_box(g) for g in near], axis=0)
            issues.append(f"overlap: '{_label(m)}' and the split text around x {(c[0] + c[2]) / 2:.1f}, "
                          f"y {(c[1] + c[3]) / 2:.1f}")
    return sorted(set(issues))
