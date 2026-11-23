"""explainer-kit house library. In a video's video.py (one continuous scene for the whole video):

    from manim import *
    import kit

    class Video(kit.NarratedScene):
        def construct(self):
            self.chapter("C01")
            self.say()
            self.play(FadeIn(kit.T("key", kit.FS_LABEL, kit.C1)), run_time=self.portion(0.3))

Kit names live only under `kit.`, so scene code can't shadow them; `vid render` rejects the clashes that remain
possible (rebinding `kit`, module-level shadowing of star-imported Manim names, rebinding Manim classes/constants).
"""
import ast as _ast
from pathlib import Path as _Path

from kit import components as _components
from kit import style as _style
from kit.scene import NarratedCameraScene, NarratedScene, NarratedThreeDScene


def _defined(mod) -> list[str]:
    """Names a kit module defines itself (not what it imported)."""
    out = []
    for node in _ast.parse(_Path(mod.__file__).read_text()).body:
        if isinstance(node, (_ast.FunctionDef, _ast.ClassDef)):
            out.append(node.name)
        elif isinstance(node, (_ast.Assign, _ast.AnnAssign)):
            for t in (node.targets if isinstance(node, _ast.Assign) else [node.target]):
                out += [n.id for n in _ast.walk(t) if isinstance(n, _ast.Name)]
    return [n for n in out if not n.startswith("_")]


__all__ = ["NarratedScene", "NarratedCameraScene", "NarratedThreeDScene"]
for _mod in (_style, _components):
    for _n in _defined(_mod):
        globals()[_n] = getattr(_mod, _n)
        __all__.append(_n)

_style.apply()  # background must be set before any Scene's camera exists
