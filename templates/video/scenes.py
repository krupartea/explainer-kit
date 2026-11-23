"""Scenes for this video. One NarratedScene subclass per '# <id>' header in narration.txt, same name.
House library: `import kit`, then kit.<name> (references/visual-devices.md says which device means what)."""
from manim import *

import kit


class S00(kit.NarratedScene):
    def construct(self):
        self.say()
        title = kit.T("Replace me", kit.FS_TITLE)
        self.play(FadeIn(title), run_time=self.portion(0.4))
        self.hold()
        self.play(FadeOut(title), run_time=kit.RT_FAST)
