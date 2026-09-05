# Thought Process — Living Log

## RULES FOR CLAUDE — read before every code explanation

These are not suggestions. Violating them has repeatedly wasted Daksh's time.

1. **NEVER introduce a name without explaining it, at the moment it first appears.**
   Every function, method, attribute, and argument. No exceptions for "obvious" ones.
   If code contains `ax.set_xlim(0, 10)`, then `set_xlim` gets explained right there --
   not later, not "you'll pick it up."

2. **For every new function, state three things:**
   - what it IS (a function? a method on an object? an attribute?)
   - what it DOES (in plain words)
   - what it RETURNS (or explicitly: "returns nothing, it changes something in place")

3. **Never assert an API's behavior from memory.** Verify it live -- `inspect.signature`,
   `__doc__`, or just run it -- and SHOW the verification. If the docs are ambiguous,
   say so out loud instead of filling the gap with assumption.

4. **Distinguish CREATE from DISPLAY.** Many libraries separate "make an object" from
   "put it on screen." When that split exists, name it explicitly -- it is the single
   most common source of "why is nothing showing up."

5. **One concept at a time.** Do not fix a bug, introduce a new function, and refactor
   structure in the same message.

6. **Call on this file every time.** Re-read these rules before writing any code
   explanation, and append new Q&A entries as they come up.

7. **Every tutor solution is written in the annotated style** -- the WHAT IT IS /
   WHAT IT DOES / WHAT IT RETURNS format, with a WHY line wherever a choice was
   non-obvious, and an explicit warning wherever skipping a step fails SILENTLY
   rather than erroring. A bare code block is never an acceptable "answer".

8. **Write tutor targets JUST IN TIME, never in advance.** Seed a day's targets
   when Daksh actually reaches that day, not before. Reasons: he is behind the
   original schedule and a wall of unwritten future days is discouraging; the
   earlier days keep surfacing facts (multi-box rows, class_id always 1, camera
   skew) that change what the later targets should say; and every solution has to
   be RUN against the real dataset before seeding, which is wasted effort if the
   plan shifts underneath it.


A running record of the reasoning behind every unfamiliar piece of code, updated as
Daksh works through Project Smokey. This file is notes, not code — nothing in the
project imports or runs it. The actual Python in explore.ipynb and beyond stays
hand-typed line by line.

## The four moves, every time you're stuck

1. **Look at what you actually have.** `type(x)` before assuming anything about an object.
2. **Interrogate it.** `dir(x)` lists everything it can do — read the non-underscore names.
3. **Print compulsively.** Before writing real code against a value, print it raw and look.
4. **Find the gap.** Name what you HAVE, name what you WANT, ask: what single operation
   turns one into the other?

## Debugging habits established so far

- **Read a traceback from the BOTTOM up.** The last line is almost always the real answer;
  everything above it is just the chain of calls that led there.
- **Compare error messages character by character** against what you meant to type —
  a `NameError` naming something you clearly meant to define usually means a typo in the
  assignment itself (e.g. `-` instead of `=`), not a missing variable.
- **Notebooks remember execution order, not page order.** The kernel only knows about
  cells you've actually run, in the order you ran them. If a variable "isn't defined"
  but the cell defining it is clearly above — check whether that cell actually ran
  (look at its `[N]` number), or use Run All to reset cleanly.
- **"How do you know that?"** — any claim about data format or repo behavior should trace
  to one of two things: (a) it was actually run and observed, here's the command, or
  (b) it's documented somewhere real, here's the source. Never just memory.

## Definition of done for explore.ipynb

- [ ] Cell 3: grid of 12 images viewed
- [ ] Cell 4: box(es) drawn and visually correct across 5-10 different images
- [ ] Cell 4: handles an image with multiple smoke boxes without crashing
- [ ] New: class_id question resolved -- full set of values collected, meaning known
- [ ] Cell 5: camera distribution counted, checked for skew

## Q&A Log

### Why does `.size` exist on the image, and how do we know?
`type(img)` showed `PIL.JpegImageFile` — a Pillow image. `.size`, `.mode`, `.format` are
core, stable Pillow API, not specific to this dataset. Verified live: `img.size` returned
`(1280, 720)` without error, which is itself the proof it exists (a missing attribute
would crash with AttributeError instead of returning a value).

### What does the annotation string actually mean?
Verified against the real HF dataset card (huggingface.co/datasets/pyronear/pyro-sdis),
not memory: `class_id x_center y_center width height`, all four coordinates normalized
(fractions of image size, 0-1), YOLO format. Confirmed NOT a count -- a count wouldn't
have decimals.

### Can one image have more than one smoke box?
Yes -- proven two ways: (1) README states 31,975 instances across 28,103 smoke images,
a ratio of ~1.14, which is only possible if some images contribute more than one box;
(2) direct search for `\n` inside annotation strings should find a real example.
Consequence: any code that assumes exactly 5 numbers per annotation (`.split()` with
no argument) will break on a multi-box image -- must `.split("\n")` first, then split
each line separately.

### What does class_id actually range over? (RESOLVED)
README's own example uses class 0; real rows show class 1. Settled by collecting the
full set across 500 training rows: the result is `{'1'}` -- ALWAYS 1, never 0. So this
is a single-class detection problem, and the README's `0` was a generic placeholder in
an illustrative example, not literal data. Confirms Day 4's training config should
declare exactly one class.

### What is `p` in `[float(p) for p in line.split()]`, and why `float()` at all?
`p` is just a loop variable name (short for "piece"), holding one item at a time from
the list `line.split()` produces -- nothing special about the letter. `.split()` returns
a list of STRINGS, even when they look like numbers ("0.067" is text, not a number, to
Python). Proven live: `1280 * "0.0670989"` does NOT multiply -- Python repeats the
string 1280 times, producing 11,520 characters of garbage, silently, no error. `float()`
is what actually converts the text into a real number safe to do arithmetic on.

### What is `cls`?
Short for "class" -- holds the box's class_id after conversion. Can't be named `class`
outright: that word is a reserved Python keyword (used to define classes, e.g.
`class Dog:`), so `cls` is the standard workaround.

### Which corner does patches.Rectangle anchor to? (RESOLVED by experiment)
Matplotlib's docstring only says `xy : (float, float) -- The anchor point`, never
naming a corner. Settled empirically: drew Rectangle((2,2), 4, 3) on a plot with
set_xlim(0,10), set_ylim(0,10), invert_yaxis(). Observed edges: x spans 2->6,
y spans 2->5. So the anchor is the corner with MINIMUM x and MINIMUM y.

Whether that LOOKS like top-left depends on axis direction -- with invert_yaxis()
(and with imshow, which inverts automatically) minimum y is the top, so it renders
top-left. On a normal upward y-axis the identical code anchors bottom-left instead.
That ambiguity is exactly why the docs say "anchor point" and not "top-left corner".

Consequence: `x0 = x_center*img_w - box_w_px/2` and `y0 = y_center*img_h - box_h_px/2`
produce the minimum-x/minimum-y corner, which is what Rectangle wants. Box math CONFIRMED.

### matplotlib names explained (day 1)
- `plt.subplots()` -- FUNCTION. Builds a figure + plotting area. RETURNS TWO objects:
  fig (the whole canvas) and ax (the area you draw into). figsize is optional;
  default is 6.4 x 4.8 inches (verified via plt.rcParams['figure.figsize']).
- `ax.set_xlim(a, b)` / `ax.set_ylim(a, b)` -- METHODS on ax. Fix the visible range of
  an axis. RETURN the tuple you passed, which is ignored -- called for side effect.
- `ax.invert_yaxis()` -- METHOD on ax. Flips y to count downward. RETURNS None.
  Needed because images count pixel rows from the top; imshow does this automatically.
- `patches.Rectangle(xy, w, h)` -- CLASS, constructs an object. RETURNS a Rectangle.
  DRAWS NOTHING on its own -- the object is invisible until attached.
- `ax.add_patch(rect)` -- METHOD on ax. Attaches the shape so it renders.
  RETURNS the same Rectangle back (ignored). THIS is what makes it appear.
- `ax.plot(x, y, "bo")` -- METHOD on ax. Draws points/lines; "bo" = blue circle.
  RETURNS a list of Line2D objects (ignored).

CREATE vs DISPLAY is the recurring trap: Rectangle() makes it, add_patch() shows it.
Skipping the second gives NO error and NO shape -- a silent failure.

### Is PyroNear's published train/val split held out by camera? (NO -- verified)
Checked directly: set(ds['train']['camera']) vs set(ds['val']['camera']).
  train = 39 cameras, val = 24, overlap = 23, val-only = {'brison-226'}
So only 1 of 24 val cameras is genuinely unseen in training. The shipped val score
measures "detect smoke against mostly-seen backgrounds", NOT "generalise to a new
lookout tower" -- it will read optimistically versus real deployment.

Camera names encode SITE + BEARING: brison-200 / -110 / -290 / -20 are one physical
tower facing four directions. Group by the prefix before the dash, not by full name.
Distribution is steep: brison-200 + brison-110 alone are ~25% of the 29,537 train rows.

Consequence for Day 3: split by SITE (and by fire sequence), holding whole sites out,
if you want an honest generalisation number.

Set operations used, for reference:
- `set(x)` -- built-in type storing unique unordered values. RETURNS a new set.
- `a & b` -- intersection. RETURNS a new set of values present in BOTH. No mutation.
- `a - b` -- difference. RETURNS values in `a` that are not in `b`.

### Where does the data actually come from? (CORRECTION -- verified 2026-08-31)
I previously said pyro-sdis covers "France, Spain, Chile, US". WRONG -- that described
the broader PYRONEAR-2025 research dataset. pyro-sdis is 100% FRENCH:
  sdis-07  15,342 (Ardeche)  |  force-06 12,322 (Alpes-Maritimes)  |  sdis-77 1,873
Camera prefixes are French place names: brison, cabanelle, courmettes, croix-augas,
ferion, marguerite, serre-de-barre, valbonne. SDIS = French fire service.

THE DATA PLAN IS THEREFORE CROSS-CONTINENT:
  TRAIN     pyro-sdis    29,537 imgs   FRANCE
  BENCHMARK FIgLib       522 seqs      SOUTHERN CALIFORNIA
  DEPLOY    HPWREN RT    live feeds    SOUTHERN CALIFORNIA

Why not just train on FIgLib? Because FIgLib has NO BOUNDING BOXES -- its labels are
time-offsets encoded in filenames (_-02400 = 2400s before ignition, _+00000 = ignition).
That tells you WHETHER a frame has smoke, not WHERE. You cannot train a box detector on
frame-level labels. PyroNear is the only one of the two with real box annotations.

Consequence: benchmark FIgLib at the FRAME level ("did it alert on this frame?") rather
than by box overlap. That is also the operationally correct metric -- did it catch the fire.

THREE TIERS OF EVAL HONESTY, weakest to strongest:
  1. val mAP            -- same cameras as train (23/24 overlap). Optimistic, near-meaningless alone.
  2. held-out-site mAP  -- French, unseen towers. Honest generalisation within France.
  3. FIgLib frame-level -- California. True cross-domain; predicts real deployment.
A large gap between 2 and 3 quantifies the cost of domain shift -- that is a FINDING to
report, not a failure to hide.

### Does FIgLib ship bounding-box annotations? (NO -- verified on disk 2026-08-31)
Inspected a downloaded sequence (20160604_FIRE_rm-n-mobo-c): 81 .jpg + 1 .mp4, and
ZERO non-image files. No .txt/.xml/.csv/.json. The only labels are in the FILENAMES:
<unix_ts>_<offset>.jpg where offset is seconds from ignition (-02400 .. +02400).
So FIgLib gives frame-level smoke/no-smoke, never box locations. Confirms it can be a
benchmark but never a training set for a box detector.
(A third-party box-annotation repo exists -- aiformankind/wildfire-smoke-dataset -- but
it is dead since 2021 and licensed CC BY-NC-SA, i.e. non-commercial. Not used.)

### DESIGN OPTION (not scheduled): pseudo-labelling to close the France->California gap
Idea: run the French-trained model on California frames, keep confident predictions,
train on them. This is a real established technique (pseudo-labelling / self-training).

THE KNOWN KILLER is confirmation bias: the model's errors become its training data, so
it grows MORE confident in the same mistakes. If it reads Californian fog as smoke,
pseudo-labelling teaches it fog IS smoke, permanently.

WHY FIgLib IS UNUSUALLY SAFE FOR THIS: the filename offsets give free ground truth on
box EXISTENCE (not location). So:
  * any box drawn on a PRE-ignition frame is definitionally wrong -- no fire exists yet.
    Discard it, and COUNT it: that is a free, exact false-positive rate on real
    California imagery.
  * any box on a POST-ignition frame is at least plausible -- smoke genuinely is present.
The filenames, not the model, decide whether it was right. That breaks the feedback loop.

STACKING SAFEGUARDS: confidence thresholding; temporal consistency (real smoke persists
and grows across consecutive frames, noise flickers); human spot-check of a sample; and
NEVER train on pseudo-labels alone -- always mix with the real French boxes as an anchor.

SEQUENCING: measure the tier-3 gap FIRST. If the French model already does fine on
California, this is unnecessary complexity. Only pursue if the gap is genuinely bad.

### Box outline thickness has to adapt to box size (noticed 2026-08-31)
Drawing row 12 with linewidth=2 revealed the problem: its boxes are 20.3 x 6.6 px and
20.1 x 9.9 px, so a 2px outline consumes 68% and 52% of the box respectively. You end up
looking at more border than smoke, which defeats the point of visual label checking.
By contrast row 0's box (171.8 x 77.8 px) loses only 7% to the same outline.

FIX for the visualisation: scale linewidth to box size (e.g. linewidth = max(0.5,
min(2, box_h/10))), or for genuinely tiny boxes crop-and-zoom the region instead of
outlining it in place. Display-only issue -- does not affect the model.

### HOW SMALL IS SMOKE, ACTUALLY? (measured over 2,894 boxes / 3,000 rows)
  1st pct 0.0134%  |  25th 0.0667%  |  MEDIAN 0.1356%  |  75th 0.3047%  |  99th 3.76%
  smallest 0.00742%   largest 36.6%   -- a ~5,000x range
  38% OF ALL BOXES ARE UNDER 0.1% OF THE FRAME.

Row 0 (1.45%) is NOT typical -- it sits in roughly the top 10% by size. Typical smoke
looks like row 12: a ~20px-wide smudge.

CONSEQUENCE FOR DAY 4 (training):
  * Small-object detection is a known weakness of YOLO-family models.
  * Default imgsz=640 downscales a 20x7 box to about 10x3 px -- at or below what the
    architecture can resolve. imgsz is a REAL DECISION here, not a default to accept.
    Higher imgsz costs GPU memory and time; that tradeoff needs measuring, not guessing.
  * Day 5 eval must BUCKET BY BOX SIZE. A single aggregate mAP will hide complete
    failure on the smallest third while looking acceptable overall.

### Site grouping + split, DONE (2026-09-01)
8 physical sites from 39 camera names, via cam.rsplit('-', 1)[0]:
  brison 10,605 (35.9%) | courmettes 6,553 | marguerite 4,433 | cabanelle 2,416
  ferion 1,944 | croix-augas 1,873 | valbonne 1,409 | serre-de-barre 304
Held out marguerite + valbonne -> Counter({'train': 23695, 'val': 5842}) = 19.8% val,
and 23,695 + 5,842 = 29,537 so nothing was lost or double-counted. Zero site leakage.

### Two bugs hit while writing it, both worth remembering
1. NO OUTPUT AT ALL from a loop that fills a collection = nothing was ever added.
   The `sites[site] += 1` line was missing -- the loop computed `site` and discarded it
   every pass. Symptom distinction worth keeping: BLANK output means the collection is
   empty; WRONG output means it filled incorrectly. Different causes, different fixes.
   Habit: print(len(collection)) right after a loop that is supposed to fill something.

2. `camera.replit(...)` instead of `rsplit` -> AttributeError: 'str' object has no
   attribute 'replit'. The traceback's LAST line named it exactly.
   Also learned why that traceback was long: Counter() consuming a generator expression
   means split_for() runs lazily from deep inside collections/__init__.py. The library
   frames are just the call path -- skip them, find the frame pointing at YOUR file.

### PROJECT DECISION (2026-09-01): full scope, Sept 17 is a checkpoint not a deadline
Considered cutting Phase 3 (FastAPI/Postgres/S3/Docker/k3s, ~8 build tasks) to hit
Sept 17. DECIDED AGAINST. Nothing gets removed. Sept 17 becomes a progress checkpoint,
and the pace is deliberately uneven -- heavy some days, light others.

Honest pace data behind the decision: Days 1-3 of the plan took 4 calendar days
(Aug 29 -> Sep 1). Extrapolating, the remaining 17 plan-days land nearer Sept 22-24
than Sept 17. That is accepted, not a problem to solve by cutting.

Reasoning for keeping Phase 3: containerisation and a real API contract are the parts
that appear most often in job descriptions, so cutting them would remove resume value
to protect a self-imposed date nobody else set.

CONSEQUENCE FOR THE TRACKER: dated days stop being meaningful at a variable pace.
The plan should be read as an ORDERED QUEUE ("what is next") rather than a calendar
("what is due today").

### THE single_cls BUG (2026-09-02) -- cost one 7.7-hour training run
SYMPTOM: training reported mAP50 climbing to 0.753 over 30 epochs, but loading the
saved best.pt and running val() standalone gave mAP50 = 0.029. Same weights, same val
set, 26x disagreement. last.pt was worse still (0.0287).

The metrics alone could not explain it. PREDICTING ON ONE IMAGE AND LOOKING did:
the model drew 10 boxes at confidence EXACTLY 1.00, tiled as even vertical strips
across the lower frame. That is a collapsed box-regression head emitting grid
positions, not detection. It also explained the numbers -- strips that large overlap
almost any real box by accident (recall 0.84) while being almost entirely wrong
(precision 0.03-0.07).

Second clue in the same picture: boxes labelled "item", not "smoke". That is
Ultralytics' placeholder when single_cls=True overrides the names in data.yaml.

CONFIRMED BY CONTROLLED TEST -- 2 epochs, identical config minus single_cls:
                     in-training mAP50   standalone val()   gap
  with single_cls          0.753              0.029         26x
  without                  0.660              0.660         none
Also trained BETTER: epoch 2 scored 0.660 without the flag vs 0.534 with it.
Final proof: on a val image with ZERO ground-truth boxes, the broken model drew 10
boxes at conf 1.00; the fixed model correctly predicted nothing.

ROOT CAUSE OF THE MISTAKE: single_cls=True was copied from Pyronear's args.yaml
without asking why THEY needed it. The labels here were already remapped to class 0
and data.yaml already declared nc: 1 -- the dataset was single-class by construction,
so the flag had nothing to collapse and only interfered.

LESSONS:
1. A reference config is a REFERENCE, not a template. Ask what each setting is FOR
   before copying it.
2. When metrics contradict each other, STOP doing metric archaeology and LOOK at a
   prediction. One image answered what four val() runs could not.
3. Confidence of EXACTLY 1.00 is a red flag, not a good sign. Real detections vary
   (0.81, 0.64, 0.43). Uniform 1.0 means a saturated output, i.e. breakage.
4. Always sanity-check against a KNOWN-EMPTY image. Predicting nothing on nothing is
   a real test, and it is cheap.

### HPWREN ACCESS -- WORKING URLs (verified live 2026-09-03)

c1.hpwren.ucsd.edu and c2.hpwren.ucsd.edu ARE DEAD. DNS resolves (c1 -> 169.228.44.159)
but connections time out. Every HPWREN doc page still lists them, including the 2021
"Camera Image Access" overview. Those docs are stale. Everything moved to CloudFront.

WORKING (all verified by actual fetch):

  LIVE frame, always current:
    https://cdn.hpwren.ucsd.edu/RT/<camera>.jpg
    -> verified bh-n-mobo-c: 200, 3072x2048, 188 KB, Last-Modified 52 SECONDS old.
       This is the live feed. One URL, no listing to parse.

  ARCHIVE frame:
    https://cdn.hpwren.ucsd.edu/MTA/<camera>/large/<yyyymmdd>/Q<n>/<unix_ts>.jpg

  INDEX of a 3-hour block (newline-separated filenames):
    https://cdn.hpwren.ucsd.edu/hpwren-cameras/<cam>/<yyyy>/<yyyymmdd>/<yyyymmdd>_<cam>_Q<n>.txt
    -> ONLY published AFTER the block closes. Q6 gave 180 names; Q7 was 403 while in
       progress. So the index route lags up to 3h. That is why /RT/ exists.

  CAMERA MANIFEST:
    https://www.hpwren.ucsd.edu/cameras/sites.js
    -> 81 sites, 503 cameras, 199 color. lat/long/elev/azimuth per camera.

  Q blocks are LOCAL Pacific time: Q1 00-03, Q2 03-06, Q3 06-09, Q4 09-12,
  Q5 12-15, Q6 15-18, Q7 18-21, Q8 21-24. (Q6 spanned 15:00:04 to 17:59:05 local.)

CADENCE: CONFIRMED 1 frame/min. Q6 held exactly 180 frames for 3 hours; deltas were
61, 60, 60, 59, 61, 60 seconds. The 1-frame-per-minute design matches the source exactly.

LIVENESS: sites.js marks all 503 cameras "active": "y", so THE FLAG IS USELESS as a
liveness signal. Real test = fetch /RT/<cam>.jpg and check Last-Modified freshness.
That is the same call the live loop makes anyway. Filter imager == "color" (the -c
suffix); -m cameras are monochrome and the model trains on RGB.

POLICY: attribution to HPWREN required if images are published. No signed license, no
registration, no stated rate limit. 1 req/min/camera matches their publish rate, so a
live loop is inherently polite. Keep backfills sequential.

### THREE RESOLUTIONS NOW IN PLAY (measured 2026-09-03) -- size_bucket default is dead

  PyroNear (training)  1280x720    16:9   0.92 MP   <- sampled 500 imgs, 100% uniform
  FIgLib (archive)     2048x1536    4:3   3.1  MP   <- all 81 frames of the one sequence
  HPWREN live          3072x2048    3:2   6.3  MP   <- verified by download

Live frames are 6.8x the pixels of training data, at a THIRD aspect ratio.

CONSEQUENCE 1: size_bucket(box, img_w=1280, img_h=720) must take REQUIRED dims. A default
is wrong for two of the three sources. Passing the wrong denominator inflates `frac` and
mislabels small boxes as medium -- you would conclude the model handles small smoke better
than it does.

CONSEQUENCE 2: downscaling eats small smoke. At imgsz=1024 a 3072x2048 frame is squeezed
~3x, so a 30px plume reaches the model as 10px. 38% of PyroNear boxes are already under
0.1% of frame area. This is the concrete, measured argument for tiling -- a number now,
not a theory. Worth one experiment on honest weights: same live frame, full-frame vs tiled.
