"""The whole video: one continuous scene (references/manim.md). Chapters follow narration.txt."""
from manim import *

import kit


class Video(kit.NarratedScene):
    def construct(self):
        self.chapter("C01")
        self.say()
        hello = kit.T("Replace me", kit.FS_HEAD)
        self.play(FadeIn(hello), run_time=self.portion(0.4))
        self.hold()
