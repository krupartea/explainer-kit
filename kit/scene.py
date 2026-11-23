"""NarratedScene: one continuous Manim scene for the whole video, driven by the narration timing
(timing.json from kit.narrate). narration.txt's `# C01 ...` headers are chapters; their beats play in order, and
whatever is on screen carries over from one chapter into the next.

    class Video(kit.NarratedScene):                      # video.py
        def construct(self):
            self.chapter("C01")                          # checks that the next beat is C01's first
            self.say()                                   # beat audio starts now
            self.play(FadeIn(a), run_time=self.portion(0.3))  # 30% of the beat
            self.hold()                                  # wait until the beat (plus its gap) ends
            self.say()
            self.play(Create(b), run_time=self.until("wrong"))   # land exactly on the word "@wrong"
            self.hold()
            self.chapter("C02")                          # a and b are still here: transform them onward

A scene class named like a chapter id (older per-scene videos) plays only that chapter.
Timing file: $VID_TIMING (default <video dir>/timing.json). Beat log (subtitles, sheets): <video dir>/logs/<class>.json.
The frame is checked (kit/layout.py) at the end of every beat and every SAMPLE_EVERY seconds: issues go to
logs/<class>.layout.json and print as "LAYOUT C03:2 ..." (end of beat 2 of C03) or "LAYOUT C03@12.0 ..."
(12 s into C03).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from manim import Scene, MovingCameraScene, ThreeDScene

from kit import layout, style


def _video_dir() -> Path:
    return Path(os.environ.get("VID_DIR", Path.cwd()))


def _timing() -> dict:
    p = Path(os.environ.get("VID_TIMING", _video_dir() / "timing.json"))
    return json.loads(p.read_text())


SAMPLE_EVERY = 4.0  # seconds between layout checks and contact-sheet frames


class _Narrated:
    MIN_WAIT = 1 / 60

    def setup(self):
        style.apply()
        sid = type(self).__name__
        t = _timing()
        chapters = {sid: t[sid]} if sid in t else t
        if not chapters:
            raise KeyError("timing.json has no chapters: run `vid narrate` first")
        self.T = [dict(b, chapter=c, k=k) for c, bs in chapters.items() for k, b in enumerate(bs)]
        self.bi, self.log, self.t0, self.deadline = 0, [], 0.0, 0.0
        self.layout_issues: dict[str, list[str]] = {}
        self._checked: set[int] = set()
        self._next_sample = SAMPLE_EVERY
        self._chapter_start: dict[str, float] = {}

    def _layout(self, where: str):
        if isinstance(self, ThreeDScene):
            return
        kw = {}
        if isinstance(self, MovingCameraScene):
            f = self.camera.frame
            kw = dict(frame_center=tuple(f.get_center()[:2]), frame_w=f.width, frame_h=f.height)
        found = layout.check(self, **kw)
        if found:
            self.layout_issues[where] = found
            for msg in found:
                print(f"LAYOUT {where} {msg}")

    def _check_layout(self):
        """Check the frame at the end of beat self.bi - 1 (once: after its hold(), else before the next say())."""
        if self.bi == 0 or (self.bi - 1) in self._checked:
            return
        self._checked.add(self.bi - 1)
        b = self.T[self.bi - 1]
        self._layout(f"{b['chapter']}:{b['k']}")

    def _sample(self):
        """Layout check whenever the scene clock passes the next SAMPLE_EVERY mark (checked after each play/wait)."""
        now = self.renderer.time
        if now < self._next_sample:
            return
        self._next_sample = (now // SAMPLE_EVERY + 1) * SAMPLE_EVERY
        if self.bi:
            c = self.T[self.bi - 1]["chapter"]
            self._layout(f"{c}@{now - self._chapter_start.get(c, 0.0):.1f}")

    def play(self, *args, **kwargs):
        super().play(*args, **kwargs)
        self._sample()

    def wait(self, *args, **kwargs):
        super().wait(*args, **kwargs)
        self._sample()

    def chapter(self, cid: str):
        """Mark where chapter cid starts in the code; raises if the next beat isn't cid's first beat."""
        if self.bi < len(self.T) and self.T[self.bi]["chapter"] == cid and self.T[self.bi]["k"] == 0:
            return
        nxt = (f"beat {self.T[self.bi]['k']} of {self.T[self.bi]['chapter']}" if self.bi < len(self.T)
               else "past the last beat")
        raise RuntimeError(f"chapter({cid!r}): the next beat is {nxt}; say() calls don't match narration.txt")

    # ---- beats ----
    def say(self):
        """Start the next beat's audio now."""
        if self.bi >= len(self.T):
            raise IndexError(f"{type(self).__name__}: say() called more times than there are beats ({len(self.T)})")
        self._check_layout()
        b = self.T[self.bi]
        self.bi += 1
        self.t0 = self.renderer.time
        if b["k"] == 0:
            self._chapter_start[b["chapter"]] = self.t0
        self.add_sound(b["wav"])
        self.log.append({"chapter": b["chapter"], "k": b["k"], "start": round(self.t0, 3), "dur": b["dur"],
                         "text": b["text"]})
        self.deadline = self.t0 + b["dur"] + b["gap"]
        return b

    @property
    def beat(self):
        return self.T[self.bi - 1]

    def left(self, frac=1.0, minimum=0.2):
        """frac of the time *remaining* in the current beat. Chained calls shrink: left(0.5) twice = 0.5 + 0.25.
        Use it for the last animation of a beat (fill what's left); use portion() for planned splits."""
        return max(minimum, (self.deadline - self.renderer.time) * frac)

    def portion(self, frac, minimum=0.2):
        """frac of the *whole* current beat (its speech + gap), independent of time already used:
        portion(0.3) then portion(0.5) = 30% and 50% of the beat."""
        return max(minimum, (self.beat["dur"] + self.beat["gap"]) * frac)

    def until(self, anchor, minimum=0.15):
        """Run time that ends exactly when the @anchor word is spoken."""
        t = self.beat["anchors"].get(anchor)
        if t is None:
            b = self.beat
            raise KeyError(f"anchor @{anchor} not found in beat {b['k']} of {b['chapter']} (QA may have failed to align it)")
        return max(minimum, self.t0 + t - self.renderer.time)

    def wait_until(self, anchor):
        r = self.until(anchor, 0)
        if r > self.MIN_WAIT:
            self.wait(r)

    def hold(self, extra=0.0):
        """Wait out the rest of the current beat (and its gap)."""
        r = self.deadline - self.renderer.time + extra
        if r > self.MIN_WAIT:
            self.wait(r)
        self._check_layout()

    def tear_down(self):
        sid = type(self).__name__
        self._check_layout()
        if self.bi != len(self.T):
            print(f"WARNING {sid}: used {self.bi}/{len(self.T)} beats")
        logs = _video_dir() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"{sid}.json").write_text(json.dumps({"beats": self.log, "end": self.renderer.time,
                                                      "chapters": self._chapter_start}))
        (logs / f"{sid}.layout.json").write_text(json.dumps(self.layout_issues, indent=1))
        super().tear_down()


class NarratedScene(_Narrated, Scene):
    pass


class NarratedCameraScene(_Narrated, MovingCameraScene):
    """For zooming into details: self.play(self.camera.frame.animate.scale(0.4).move_to(x))."""
    pass


class NarratedThreeDScene(_Narrated, ThreeDScene):
    """Only when the content has three real dimensions (see toolbox.md, '2D or 3D')."""
    pass
