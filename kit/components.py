"""House components. Each one encodes ONE meaning (see references/visual-devices.md); prefer these over ad-hoc
mobjects so the same idea always looks the same across videos.

    import kit          # then kit.chip(...), kit.mark_wrong(...), kit.FS_BODY ...
"""
from __future__ import annotations

import shutil

import numpy as np
from manim import *

from kit.style import *

HAS_LATEX = shutil.which("latex") is not None and shutil.which("dvisvgm") is not None


# ---------------- text ----------------
def T(text, size=FS_BODY, color=INK, font=SANS, **kw):
    """Plain text. On-screen text is labels and keywords, not narration sentences (redundancy principle)."""
    return Text(text, font=font, font_size=size, color=color, **kw)


def mono(text, size=FS_CODE, color=INK, **kw):
    return Text(text, font=MONO, font_size=size, color=color, **kw)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def span(text, color, weight=None):
    w = f' weight="{weight}"' if weight else ""
    return f'<span foreground="{color}"{w}>{esc(text)}</span>'


def rich(m, size=FS_BODY, font=SANS, **kw):
    """Pango markup, e.g. rich(f"the {span('key', C1)} is found")."""
    return MarkupText(m, font=font, font_size=size, color=INK, **kw)


def tex(latex, size=FS_BODY, color=INK, **kw):
    """Real LaTeX math when installed, otherwise a mono fallback (setup.sh warns if LaTeX is missing)."""
    if HAS_LATEX:
        return MathTex(latex, font_size=size * 1.25, color=color, **kw)
    return mono(latex.replace("\\", ""), size, color)


def live_number(value, places=2, size=FS_BODY, color=INK, **kw):
    """Live number (pair with ValueTracker + add_updater). Text-based so it works without LaTeX."""
    return DecimalNumber(value, num_decimal_places=places, font_size=size, color=color, mob_class=Text, **kw)


def centered_text(label, size, target, max_w, max_h, color=INK):
    """Text centered on `target` by its baseline, so 'regex' and 'finder' sit level in sibling boxes.
    Shrinks only when it doesn't fit (sibling boxes keep one font size)."""
    if "\n" in label:                            # multi-line: center the block by its bounding box
        t = T(label, size, color)
        if t.width > max_w or t.height > max_h:
            t.scale(min(max_w / t.width, max_h / t.height))
        return t.move_to(target)
    full = T("Hg" + label, size, color)          # "Hg" spans ascender..descender, then is hidden
    strut, t = VGroup(*full[:2]), VGroup(*full[2:])
    if t.width > max_w or full.height > max_h:
        k = min(max_w / t.width, max_h / full.height)
        full.scale(k)
    full.shift(target.get_center() - np.array([t.get_center()[0], full.get_center()[1], 0]))
    strut.set_opacity(0)
    t.full = full
    return t


def fit_to(m, w, h=None):
    m.scale_to_fit_width(w)
    if h is not None and m.height > h:
        m.scale_to_fit_height(h)
    return m


# ---------------- containers ----------------
def panel(w, h, color=CARD_EDGE, fill=CARD, r=0.15):
    return RoundedRectangle(width=w, height=h, corner_radius=r, stroke_color=color, stroke_width=2,
                            fill_color=fill, fill_opacity=1)


def chip(text, color=CARD_EDGE, size=FS_LABEL, fill=CARD):
    """A named thing (concept, field, step). Stroke color = the concept's identity color."""
    t = T(text, size, INK)
    r = RoundedRectangle(width=t.width + 0.4, height=t.height + 0.26, corner_radius=0.12, stroke_color=color,
                         stroke_width=2, fill_color=fill, fill_opacity=1)
    return VGroup(r, t.move_to(r))


def stage_box(label, w=2.4, h=1.0, color=CARD_EDGE, size=FS_LABEL):
    """A component / stage in a system (pipeline step, module, service)."""
    r = panel(w, h, color)
    return VGroup(r, centered_text(label, size, r, w * 0.85, h * 0.7))


def pipeline(labels, color=CARD_EDGE, w=2.3, h=0.9, buff=0.8):
    """Left-to-right stages joined by arrows: data flows left to right, always."""
    boxes = VGroup(*[stage_box(l, w, h, color) for l in labels]).arrange(RIGHT, buff=buff)
    arrows = VGroup(*[Arrow(a.get_right(), b.get_left(), buff=0.06, stroke_width=4, color=GREY,
                            max_tip_length_to_length_ratio=0.3) for a, b in zip(boxes, boxes[1:])])
    g = VGroup(boxes, arrows)
    g.boxes, g.arrows = boxes, arrows
    return g


def cell_row(values, w=0.8, h=0.8, size=FS_LABEL, color=CARD_EDGE, index=False):
    """An array / sequence / tensor row. Optional index labels under each cell."""
    g = VGroup()
    for v in values:
        r = Rectangle(width=w, height=h, stroke_color=color, stroke_width=2, fill_color=CARD, fill_opacity=1)
        g.add(VGroup(r, fit_to(mono(str(v), size), w * 0.8, h * 0.6).move_to(r)))
    g.arrange(RIGHT, buff=0)
    if index:
        g.idx = VGroup(*[T(str(i), FS_SMALL, GREY).next_to(c, DOWN, buff=0.12) for i, c in enumerate(g)])
    return g


def code_block(src: str, language="python", size=22, highlight=None):
    """Code block in the house theme. highlight: list of 1-based line numbers to tint FOCUS."""
    c = Code(code_string=src, language=language, formatter_style="monokai", background="rectangle",
             add_line_numbers=False, paragraph_config={"font": MONO, "font_size": size},
             background_config={"fill_color": CARD, "stroke_color": CARD_EDGE, "stroke_width": 2})
    if highlight:
        lines = c.code_lines if hasattr(c, "code_lines") else c[-1]
        for n in highlight:
            ln = lines[n - 1]
            c.add(SurroundingRectangle(ln, color=FOCUS, buff=0.05, stroke_width=0, fill_opacity=0.15))
    return c


def label_arrow(a, b, text=None, color=GREY, size=FS_SMALL, curved=0.0):
    """Relationship from a to b. curved: angle (radians) for CurvedArrow; 0 = straight."""
    if curved:
        ar = CurvedArrow(a, b, angle=curved, color=color, stroke_width=4, tip_length=0.18)
    else:
        ar = Arrow(a, b, buff=0.08, color=color, stroke_width=4, max_tip_length_to_length_ratio=0.15)
    if not text:
        return ar
    lab = T(text, size, color).set_stroke(BG, 6, background=True).move_to(ar.point_from_proportion(0.5) + UP * 0.3)
    return VGroup(ar, lab)


def brace_label(mob, text, direction=DOWN, color=GREY, size=FS_SMALL):
    br = Brace(mob, direction, color=color)
    return VGroup(br, T(text, size, color).next_to(br, direction, buff=0.1))


def badge(ok: bool, size=0.5):
    """Green check or red cross icon."""
    if ok:
        mark = VMobject(stroke_color=GOOD, stroke_width=8).set_points_as_corners(
            [[-0.5, 0, 0], [-0.15, -0.4, 0], [0.55, 0.45, 0]]).scale(size / 1.0)
    else:
        mark = VGroup(Line([-0.4, -0.4, 0], [0.4, 0.4, 0]), Line([-0.4, 0.4, 0], [0.4, -0.4, 0])).set_stroke(
            BAD, 8).scale(size / 0.8)
    return mark


# ---------------- meaning-carrying animations ----------------
def mark_wrong(mob, tint=True):
    """'This is wrong / it fails.' Red tint + Wiggle (the shake viewers learn once).
    Returns an AnimationGroup; play it on the exact word that names the failure (use an @anchor)."""
    anims = [Wiggle(mob, scale_value=1.08, rotation_angle=0.03 * TAU, n_wiggles=6)]
    if tint:
        anims.append(mob.animate.set_color(BAD))
    return AnimationGroup(*anims)


def mark_right(mob, color=GOOD):
    """'This is the correct one / it works.' Green tint + gentle Indicate."""
    return AnimationGroup(Indicate(mob, color=color, scale_factor=1.06))


def look(mob, color=FOCUS):
    """'Look here now.' Transient: the element returns to normal afterwards."""
    return Indicate(mob, color=color, scale_factor=1.08)


def this_one(mob, color=FOCUS):
    """'This specific one, among several.' Circle around it, then fade the circle."""
    return Circumscribe(mob, color=color, fade_out=True)


def flash_at(point, color=FOCUS):
    """'Something happened here' (a hit, a match, a write)."""
    return Flash(point, color=color, flash_radius=0.45, line_length=0.18)


def dim_others(scene_mobs, keep, opacity=0.25):
    """Signaling: fade everything except `keep` (coherence: the rest is context now)."""
    keep_ids = {id(m) for m in keep.get_family()} if hasattr(keep, "get_family") else set()
    return AnimationGroup(*[m.animate.set_opacity(opacity) for m in scene_mobs if id(m) not in keep_ids])


def strike(mob, color=BAD):
    """'Rejected / no longer valid.' A line through it (keeps it readable, unlike removing it)."""
    ln = Line(mob.get_left() + LEFT * 0.05, mob.get_right() + RIGHT * 0.05, color=color, stroke_width=5)
    return Create(ln), ln


def becomes(a, b):
    """'a is the same thing as b, rewritten' (equivalence; shared parts stay put)."""
    return TransformMatchingShapes(a, b)


def replaced_by(a, b):
    """'a turns into b' (a state change)."""
    return ReplacementTransform(a, b)


def live_counter(start, places=0, size=FS_BODY, color=INK, label=None):
    """Live counter: returns (group, tracker). Animate with tracker.animate.set_value(x)."""
    tr = ValueTracker(start)
    num = live_number(start, places, size, color)
    num.add_updater(lambda m: m.set_value(tr.get_value()))
    g = VGroup(num)
    if label:
        g = VGroup(T(label, FS_SMALL, GREY), num).arrange(RIGHT, buff=0.2)
        num.add_updater(lambda m: m.next_to(g[0], RIGHT, buff=0.2))
    return g, tr


def ghost_of(mob, opacity=0.25):
    """Counterfactual / previous state: a translucent copy that stays for comparison."""
    return mob.copy().set_opacity(opacity)


def split_screen(left_title, right_title, left_color=BAD, right_color=GOOD):
    """Before/after or without/with comparison frame. Returns (group, left_center, right_center)."""
    div = DashedLine(UP * 3.3, DOWN * 2.9, color=DIM)
    lt = T(left_title, FS_HEAD, left_color).move_to([-3.55, 3.1, 0])
    rt = T(right_title, FS_HEAD, right_color).move_to([3.55, 3.1, 0])
    return VGroup(div, lt, rt), np.array([-3.55, 0.1, 0]), np.array([3.55, 0.1, 0])


def step_counter(total, size=FS_SMALL):
    """'Step k of n' in the top-right; returns (mobject, set_step(k) -> animation)."""
    t = T(f"step 1 / {total}", size, GREY).to_corner(UR, buff=0.35)

    def set_step(k):
        new = T(f"step {k} / {total}", size, GREY).move_to(t)
        return Transform(t, new)
    return t, set_step
