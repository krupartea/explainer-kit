"""NarratedScene: a Manim scene driven by the narration timing (timing.json from kit.narrate).

    class S02(kit.NarratedScene):
        def construct(self):
            self.say()                                   # beat 0 audio starts now
            self.play(FadeIn(a), run_time=self.portion(0.3))  # 30% of the beat
            self.hold()                                  # wait until the beat (plus its gap) ends
            self.say()                                   # beat 1
            self.play(Create(b), run_time=self.until("wrong"))   # land exactly on the word "@wrong"
            self.play(kit.mark_wrong(b))
            self.hold()

Timing file: $VID_TIMING (default <video dir>/timing.json). Beat logs for subtitles: <video dir>/logs/<scene>.json.
At the end of every beat the frame is checked (kit/layout.py): issues go to logs/<scene>.layout.json and print as
"LAYOUT <scene>:<beat> ...".
The scene id is the class name and must match a '# <id>' header in narration.txt.
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


class _Narrated:
    MIN_WAIT = 1 / 60

    def setup(self):
        style.apply()
        sid = type(self).__name__
        t = _timing()
        if sid not in t:
            raise KeyError(f"scene {sid} has no narration (headers in timing.json: {list(t)})")
        self.T, self.bi, self.log, self.t0, self.deadline = t[sid], 0, [], 0.0, 0.0
        self.layout_issues: dict[int, list[str]] = {}

    def _check_layout(self):
        """Check the frame at the end of beat self.bi - 1 (once: after its hold(), else before the next say())."""
        if self.bi == 0 or isinstance(self, ThreeDScene) or (self.bi - 1) in getattr(self, "_checked", set()):
            return
        self._checked = getattr(self, "_checked", set()) | {self.bi - 1}
        kw = {}
        if isinstance(self, MovingCameraScene):
            f = self.camera.frame
            kw = dict(frame_center=tuple(f.get_center()[:2]), frame_w=f.width, frame_h=f.height)
        found = layout.check(self, **kw)
        if found:
            self.layout_issues[self.bi - 1] = found
            for msg in found:
                print(f"LAYOUT {type(self).__name__}:{self.bi - 1} {msg}")

    # ---- beats ----
    def say(self):
        """Start the next beat's audio now."""
        if self.bi >= len(self.T):
            raise IndexError(f"{type(self).__name__}: say() called more times than there are beats ({len(self.T)})")
        self._check_layout()
        b = self.T[self.bi]
        self.bi += 1
        self.t0 = self.renderer.time
        self.add_sound(b["wav"])
        self.log.append({"start": round(self.t0, 3), "dur": b["dur"], "text": b["text"]})
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
            raise KeyError(f"anchor @{anchor} not found in beat {self.bi - 1} (QA may have failed to align it)")
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
        (logs / f"{sid}.json").write_text(json.dumps({"beats": self.log, "end": self.renderer.time}))
        (logs / f"{sid}.layout.json").write_text(json.dumps(self.layout_issues, indent=1))
        super().tear_down()


class NarratedScene(_Narrated, Scene):
    pass


class NarratedCameraScene(_Narrated, MovingCameraScene):
    """For zooming into details: self.play(self.camera.frame.animate.scale(0.4).move_to(x))."""
    pass


class NarratedThreeDScene(_Narrated, ThreeDScene):
    """Only when the content has three real dimensions (see visual-devices.md, '2D or 3D')."""
    pass
