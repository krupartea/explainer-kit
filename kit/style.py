"""House style: one palette, one type scale, one meaning per color. Every video uses these, so the viewer
learns the visual language once. Change values here, never per video (unless the feedback log says so).

Color semantics (fixed across all videos):
    BAD     red      something fails, is rejected, or is the wrong answer
    GOOD    green    the correct answer / success / accepted
    FOCUS   yellow   "look here now" (transient highlight, never a permanent identity color)
    DIM     grey     context that is present but not the point right now
Concept colors C1..C6 are *identities*: assign one per key concept at the start of a video
(e.g. C1 = key, C2 = value) and keep that mapping for the whole video. Never reuse a concept
color for a different concept in the same video, and never use BAD/GOOD as concept colors.
(Names avoid WRONG/RIGHT: manim's RIGHT is a direction vector.)
"""
from manim import config

BG = "#0f1115"
INK = "#E8E6E1"        # main text and lines
GREY = "#8A8F98"       # secondary text, captions, axes
DIM = "#4A4F58"        # de-emphasized context
CARD = "#1A1D23"       # panels / boxes fill
CARD_EDGE = "#3A3F48"  # panels / boxes stroke

BAD = "#FC6255"
GOOD = "#83C167"
FOCUS = "#FFD166"

C1 = "#58C4DD"  # blue
C2 = "#FF8C42"  # orange
C3 = "#C792EA"  # purple
C4 = "#5CD0B3"  # teal
C5 = "#F78FB3"  # pink
C6 = "#9CDCFE"  # light blue
CONCEPTS = [C1, C2, C3, C4, C5, C6]

SANS = "Ubuntu"
MONO = "Ubuntu Mono"

# type scale (font_size)
FS_TITLE, FS_HEAD, FS_BODY, FS_LABEL, FS_SMALL, FS_CODE = 56, 40, 32, 26, 20, 26

# layout: frame is 14.22 x 8 units. Keep the bottom band free: players draw .srt subtitles there.
SAFE_BOTTOM = -3.0     # nothing essential below this y
SAFE_TOP = 3.55
SAFE_X = 6.6

# timing defaults (seconds)
RT_FAST, RT_NORMAL, RT_SLOW = 0.5, 1.0, 1.6


def apply():
    config.background_color = BG
