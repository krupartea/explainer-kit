"""One scene per file; the class name matches the '# <id>' header in narration.txt."""
from manim import *

import kit
import common  # noqa: F401  (shared data, drawings and helpers for this video)


class S00(kit.NarratedScene):
    def construct(self):
        # beat 0, device: title card
        self.say()
        title = kit.T("Replace me", kit.FS_TITLE)
        self.play(FadeIn(title), run_time=self.portion(0.4))
        self.hold()
        self.play(FadeOut(title), run_time=kit.RT_FAST)
