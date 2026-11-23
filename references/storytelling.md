# Storytelling

The viewer must **feel the need** for X before hearing X's name, and hear what X is before how X works. Every
video, every topic. Motivation first; definition second; mechanism third.

## The arc

| # | Beat group | What the viewer experiences | Typical share |
|---|---|---|---|
| 1 | **Goal** | A concrete task, with the running example on screen. "We want the flight number and arrival time from this ticket." | 5% |
| 2 | **Naive attempt** | The way you'd do it with today's tools (for a codebase: the existing API, used as is). It works on the easy part. | 10% |
| 3 | **Failure** | It breaks on a concrete case, shown on screen (`mark_wrong` lands on the word that names the failure). 2–4 failure modes, each with its own instance. | 15–20% |
| 4 | **The need** | The requirement stated as a sentence the viewer could have said themselves: "we need to know what is *below* the key, not just after it." | 5% |
| 5 | **X** | X named only now, as the answer to the need. One sentence: what it is, not how. | 5% |
| 6 | **Mechanism** | How X works, one idea at a time, ordered so each idea depends only on earlier ones. Each idea: its need → the idea → watch it work on the running example. | 40–50% |
| 7 | **Payoff** | Replay the step-3 failure; now it succeeds (`mark_right`). Then the ideas as a recap strip, then where it lives (for a codebase: which module/API). | 10% |

**Gate (check before `vid narrate`):** X's name first appears in group 5 or later, and every idea in group 6 is
preceded by the problem it solves. Search narration.txt for X's name and for each idea's name to confirm.

A **clip** (a narrow question, 1–2 min) compresses the arc: one failure, one idea, one payoff. The order stays.

## Length

Default ~5 min. Narration runs ~140 spoken words per minute, so ~700 words. Infer longer or shorter from the
conversation (a single sub-question → clip; "explain the whole system" → up to ~10 min).

## Running example

One concrete instance carried through the whole video (one ticket, one array, one request). Introduce it in
group 1, break it in group 3, fix it in group 7. New examples only when the running one can't show a failure
mode, and then return to it. For a codebase, take the example and every number from the real code and data:
run the code, read the real values, cite the files in brief.md.

## Concrete before abstract

Real values first, symbols after: show `0.36` and `1.09` before `cost(θ, d)`. When a formula appears, its terms
morph out of numbers the viewer already watched (`becomes`). Names of components appear as on-screen labels
before the narration relies on them (pre-training).

## Writing for the ear

- One claim per sentence; most sentences under ~20 words. One beat (line) = one visual change.
- Concrete nouns from the running example ("the time below ARR"), not abstractions.
- **One term per concept**, identical in narration, on-screen labels and, for codebases, the code identifier.
- Signposts make the arc visible: "First…", "But…", "So we need…", "Idea two:".
- A question is a transition into the next need; give it the `[curious]` mood.
- **Intonation carries meaning**: focus, pauses and moods follow references/delivery.md.
- Numbers: speak a rounded form, show the exact form on screen.
- Open on the goal itself and end on the payoff; the first and last lines carry content.

## Accuracy

Every claim traceable to a source listed in brief.md (file, PR, doc, or your own run of the code). Unsure of a
fact: say less rather than guess. API names, numbers and file names exactly as in the source.
