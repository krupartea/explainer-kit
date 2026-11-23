# Brief

<!-- Benchmark brief: the fixed input for every SIFT-descriptor video, so videos made by different kit
     versions can be compared. Written 2026-11-23; never add feedback on earlier videos. -->

- **Topic:** The SIFT descriptor: how SIFT turns the patch around a keypoint into 128 numbers that still
  match when the same point is photographed rotated, brighter or darker, or from a slightly different view.
  The descriptor only: keypoint detection (difference-of-Gaussians scale space, extremum refinement) is out of
  scope; take a keypoint's location and scale as given and say so in one line.
- **Viewer:** a computer-vision / ML engineer. Knows what an image gradient is and has called SIFT through a
  library (detect, compute, match) to stitch or align images, but treats the 128-number vector as a black box:
  doesn't know where 128 comes from, why it's built from gradient histograms, or which step buys which
  robustness.
- **The need (felt before the name):** find the same physical point in two photos of a scene, where the
  second is rotated and has different lighting. Comparing the raw pixel patches around the point gives a
  large difference for the true match and can rank a wrong patch closer.
- **Running example:** one image and a second view of it: the same image rotated (e.g. 30°) with changed
  brightness and contrast (e.g. intensities ×0.6 + 20). One keypoint whose match the video follows throughout,
  plus at least one wrong candidate patch. No OpenCV or scikit-image in the kit venv: synthesize the image
  with numpy/PIL (shapes with clear edges and corners, some texture), implement the descriptor in numpy in a
  script in `data/`, and compute every number on screen with it (patch distances, histograms, descriptor
  distances, ratios).
- **Payoff:** the viewer can explain what the 128 numbers are (4×4 cells × 8 orientation bins), say which
  step makes the descriptor robust to which change (brightness, contrast, rotation, small shifts and
  deformations, strong local lighting changes), predict what breaks if a step is removed, and knows how two
  descriptors are compared (distance, and the ratio test).
- **Target length:** about 4 minutes.

## From the conversation

Workspace (codebase the conversation was about, read-only; empty if none):

- What the user asked, in their words, and why they want it: a benchmark run: the same topic and brief are
  produced by successive kit versions to see whether the videos get better. The video should be a proper,
  finished clip.
- What they already understand; where they were confused: n/a. Assume the viewer profile above.
- Facts and numbers established in the conversation, each with its source: the facts below (Sources); derive
  every number on screen from the running example.
- How they want this video to go: no preference beyond the brief.

## Sources

David G. Lowe, "Distinctive Image Features from Scale-Invariant Keypoints", IJCV 60(2), 2004, sections 5–7:
- Orientation assignment (sec. 5): a 36-bin histogram of gradient orientations around the keypoint, weighted
  by gradient magnitude and a Gaussian window; its peak is the keypoint's orientation (peaks within 80% of it
  create additional keypoints). Descriptor coordinates and gradient orientations are rotated relative to it.
- Descriptor (sec. 6.1): gradient magnitudes and orientations sampled around the keypoint at its scale,
  weighted by a Gaussian with σ equal to half the descriptor window width; accumulated into orientation
  histograms over 4×4 subregions with 8 bins each (4×4×8 = 128), with trilinear interpolation between
  neighbouring bins and cells. In the paper's figure, a 16×16 sample array feeds the 4×4 grid.
- Illumination (sec. 6.1): normalize the vector to unit length (cancels contrast change; gradients already
  cancel a brightness offset), clip every element at 0.2, and renormalize (reduces the weight of large
  gradient magnitudes from non-linear lighting changes).
- Matching (sec. 7.1): nearest neighbour by Euclidean distance; reject a match when the distance ratio of the
  closest to the second-closest neighbour is above 0.8, which removed 90% of false matches while discarding
  under 5% of correct ones in the paper's data.

## Numbers on screen

<!-- Filled by the producer. -->

| number | where (scene:beat) | source (file / command output) |
|---|---|---|

## Accepted QA flags

<!-- Filled by the producer: one line per narration ⚠ or layout finding left as is, and why it is fine. -->
