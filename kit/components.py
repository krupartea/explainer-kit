"""House components: text, drawing helpers and animations that carry one meaning each (see references/toolbox.md).
No slide furniture (panels, chips, step strips): the picture itself carries the story.

    import kit          # then kit.T(...), kit.mark_wrong(...), kit.FS_BODY ...
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


def depicted(mob):
    """Mark mobjects that are part of a pictured object (a product label, a screenshot-like mock): their small
    print is intentional, so the layout check doesn't call it tiny. Returns mob."""
    for x in mob.get_family():
        x._kit_depicted = True
    return mob


def fit_to(m, w, h=None):
    m.scale_to_fit_width(w)
    if h is not None and m.height > h:
        m.scale_to_fit_height(h)
    return m


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


# ---------------- meaning-carrying animations ----------------
def mark_wrong(mob, tint=True):
    """'This is wrong / it fails.' Red tint + Wiggle (the shake viewers learn once).
    One animation (no AnimationGroup: that re-stacks parts and can bury text under its own box). The tint is
    applied as the shake starts. Play it on the exact word that names the failure (use an @anchor)."""
    if tint:
        mob.set_color(BAD)
    return Wiggle(mob, scale_value=1.08, rotation_angle=0.03 * TAU, n_wiggles=6)


def mark_right(mob, color=GOOD):
    """'This is the correct one / it works.' A gentle green Indicate."""
    return Indicate(mob, color=color, scale_factor=1.06)


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
    """Signaling: fade everything except `keep` (coherence: the rest is context now).
    Returns a list: self.play(*kit.dim_others(...))."""
    keep_ids = {id(m) for m in keep.get_family()} if hasattr(keep, "get_family") else set()
    return [m.animate.set_opacity(opacity) for m in scene_mobs if id(m) not in keep_ids]


def live_readout(measure, a, b, label, places=2, color=FOCUS):
    """Concept sandbox helper: a live readout `label = value` that recomputes measure(a, b) every frame while
    you move or resize a and b. Returns the readout mobject (add it, then animate a/b)."""
    num = live_number(measure(a, b), places, FS_HEAD, color)
    row = VGroup(T(label + " =", FS_HEAD, GREY), num).arrange(RIGHT, buff=0.25)
    num.add_updater(lambda m: m.set_value(measure(a, b)))
    return row


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


