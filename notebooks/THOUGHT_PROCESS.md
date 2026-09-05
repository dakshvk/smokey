# Project Smokey: working log

A running record of the reasoning behind every unfamiliar piece of code in this project,
plus the findings and mistakes that shaped the design. These are notes, not code. Nothing
in the project imports or runs this file. The Python in `explore.ipynb` and `eval/` is
hand typed line by line.

## What I require of an explanation

I set these rules early because I kept accepting code I could not have written myself.

1. No name goes unexplained at the point it first appears. Every function, method,
   attribute, and argument, including the ones that look obvious. If a line contains
   `ax.set_xlim(0, 10)`, then `set_xlim` gets explained right there rather than later.

2. For each new function I want three things: what it is (function, method on an object,
   attribute), what it does in plain words, and what it returns. "Returns nothing, changes
   something in place" counts as an answer.

3. No claim about an API from memory. Verify it live with `inspect.signature`, `__doc__`,
   or by running it, and show the verification. Where the docs are ambiguous, say so
   instead of filling the gap with a guess.

4. Keep CREATE separate from DISPLAY. Many libraries split "make an object" from "put it
   on screen." That split is the most common reason nothing shows up.

5. One concept at a time. Do not fix a bug, introduce a new function, and restructure
   things in the same breath.

6. Every worked solution uses the annotated style above, with a reason attached wherever
   a choice was not obvious, and an explicit warning wherever skipping a step fails
   silently instead of raising. A bare code block is not an answer.

## Four moves when I get stuck

1. Look at what I actually have. `type(x)` before assuming anything about an object.
2. Interrogate it. `dir(x)` lists what it can do. Read the names without underscores.
3. Print compulsively. Before writing real code against a value, print it raw and look at it.
4. Find the gap. Name what I have, name what I want, and ask which single operation turns
   one into the other.

## Debugging habits so far

Read a traceback from the bottom up. The last line is almost always the real answer, and
everything above it is the chain of calls that led there.

Compare error messages character by character against what I meant to type. A `NameError`
naming something I clearly meant to define usually means a typo in the assignment itself,
like `-` instead of `=`, rather than a missing variable.

Notebooks remember execution order, not page order. The kernel only knows about cells I
actually ran, in the order I ran them. If a variable is undefined but the cell defining it
sits above, check whether that cell really ran by looking at its `[N]` number, or use Run
All to reset cleanly.

Ask "how do I know that?" Any claim about data format or repo behavior should trace to one
of two things: I ran it and observed the result, and here is the command, or it is
documented somewhere real, and here is the source. Memory does not count.

## Q&A log

### Why does `.size` exist on the image, and how do I know?

`type(img)` showed `PIL.JpegImageFile`, a Pillow image. `.size`, `.mode`, and `.format` are
core Pillow API, not something specific to this dataset. Verified live: `img.size` returned
`(1280, 720)` without error, which is itself the proof it exists. A missing attribute would
raise AttributeError instead of returning a value.

### What does the annotation string actually mean?

Verified against the HF dataset card at huggingface.co/datasets/pyronear/pyro-sdis rather
than memory: `class_id x_center y_center width height`, with all four coordinates
normalized to fractions of image size between 0 and 1. That is YOLO format. It is not a
count, which I confirmed by noticing a count would not have decimals.

### Can one image have more than one smoke box?

Yes, provable two ways. The README states 31,975 instances across 28,103 smoke images, a
ratio of about 1.14, which is only possible if some images contribute more than one box.
Searching for `\n` inside the annotation strings finds real examples directly.

The consequence is that any code assuming exactly 5 numbers per annotation, meaning
`.split()` with no argument, breaks on a multi box image. Split on `"\n"` first, then split
each line separately.

### What does class_id actually range over? (resolved)

The README's own example uses class 0 while real rows show class 1. I settled it by
collecting the full set across 500 training rows. The result is `{'1'}`, always 1 and never
0. So this is a single class detection problem, and the README's 0 was a generic
placeholder in an illustrative example rather than literal data. That confirms the training
config should declare exactly one class.

### What is `p` in `[float(p) for p in line.split()]`, and why `float()` at all?

`p` is just a loop variable name, short for "piece," holding one item at a time from the
list `line.split()` produces. Nothing special about the letter.

`.split()` returns a list of strings even when they look like numbers. To Python, "0.067"
is text. I proved this live: `1280 * "0.0670989"` does not multiply. Python repeats the
string 1280 times and produces 11,520 characters of garbage, silently, with no error.
`float()` is what converts the text into a real number safe to do arithmetic on.

### What is `cls`?

Short for "class," holding the box's class_id after conversion. It cannot be named `class`
outright because that is a reserved Python keyword used to define classes, as in
`class Dog:`, so `cls` is the standard workaround.

### Which corner does patches.Rectangle anchor to? (resolved by experiment)

Matplotlib's docstring only says `xy : (float, float)`, the anchor point, and never names a
corner. I settled it empirically by drawing `Rectangle((2,2), 4, 3)` on a plot with
`set_xlim(0,10)`, `set_ylim(0,10)`, and `invert_yaxis()`. The observed edges span x from 2
to 6 and y from 2 to 5, so the anchor is the corner with minimum x and minimum y.

Whether that looks like top left depends on axis direction. With `invert_yaxis()`, and with
`imshow` which inverts automatically, minimum y is the top, so it renders top left. On a
normal upward y axis the identical code anchors bottom left instead. That ambiguity is
exactly why the docs say "anchor point" rather than "top left corner."

So `x0 = x_center*img_w - box_w_px/2` and `y0 = y_center*img_h - box_h_px/2` produce the
minimum x and minimum y corner, which is what Rectangle wants. Box math confirmed.

### matplotlib names explained (day 1)

`plt.subplots()` is a function. It builds a figure plus a plotting area and returns two
objects: fig, the whole canvas, and ax, the area you draw into. figsize is optional and
defaults to 6.4 by 4.8 inches, which I verified via `plt.rcParams['figure.figsize']`.

`ax.set_xlim(a, b)` and `ax.set_ylim(a, b)` are methods on ax. They fix the visible range of
an axis and return the tuple you passed, which is ignored. They are called for side effect.

`ax.invert_yaxis()` is a method on ax. It flips y to count downward and returns None. It is
needed because images count pixel rows from the top, and imshow does this automatically.

`patches.Rectangle(xy, w, h)` is a class that constructs an object and returns a Rectangle.
It draws nothing on its own. The object stays invisible until attached.

`ax.add_patch(rect)` is a method on ax. It attaches the shape so it renders, and returns the
same Rectangle back, which is ignored. This is what makes the shape appear.

`ax.plot(x, y, "bo")` is a method on ax. It draws points or lines, where "bo" means blue
circle, and returns a list of Line2D objects that is ignored.

CREATE versus DISPLAY is the recurring trap here. `Rectangle()` makes it and `add_patch()`
shows it. Skipping the second gives no error and no shape, which is a silent failure.

### Is PyroNear's published train/val split held out by camera? (no, verified)

I checked directly by comparing `set(ds['train']['camera'])` against
`set(ds['val']['camera'])`. Train has 39 cameras, val has 24, the overlap is 23, and the
only val exclusive camera is `brison-226`.

So 1 of 24 val cameras is genuinely unseen in training. The shipped val score measures
detecting smoke against mostly seen backgrounds, not generalizing to a new lookout tower.
It reads optimistically compared to real deployment.

Camera names encode site plus bearing. `brison-200`, `-110`, `-290`, and `-20` are one
physical tower facing four directions, so grouping has to happen on the prefix before the
dash rather than the full name. The distribution is steep: `brison-200` and `brison-110`
alone are about 25% of the 29,537 training rows.

The consequence is that an honest generalization number requires splitting by site, and by
fire sequence, holding whole sites out.

Set operations used, for reference. `set(x)` is a built in type storing unique unordered
values and returns a new set. `a & b` is intersection and returns a new set of values
present in both, with no mutation. `a - b` is difference and returns values in `a` that are
not in `b`.

### Where does the data actually come from? (correction, verified 2026-08-31)

I had this wrong. I believed pyro-sdis covered France, Spain, Chile, and the US, but that
describes the broader PYRONEAR-2025 research dataset. pyro-sdis is entirely French:

    sdis-07   15,342  (Ardeche)
    force-06  12,322  (Alpes-Maritimes)
    sdis-77    1,873

The camera prefixes are French place names: brison, cabanelle, courmettes, croix-augas,
ferion, marguerite, serre-de-barre, valbonne. SDIS is the French fire service.

That makes the data plan cross continent:

    TRAIN      pyro-sdis   29,537 images   France
    BENCHMARK  FIgLib      522 sequences   Southern California
    DEPLOY     HPWREN RT   live feeds      Southern California

Why not just train on FIgLib? Because FIgLib has no bounding boxes. Its labels are time
offsets encoded in filenames, where `_-02400` means 2400 seconds before ignition and
`_+00000` is ignition itself. That tells you whether a frame has smoke, not where it is,
and you cannot train a box detector on frame level labels. PyroNear is the only one of the
two with real box annotations.

So FIgLib gets benchmarked at the frame level, asking whether the model alerted on a frame.
That is also the operationally correct question: did it catch the fire.

Three tiers of eval honesty, weakest to strongest:

1. val mAP, on the same cameras as training with 23 of 24 overlapping. Optimistic and close
   to meaningless on its own.
2. Held out site mAP, French, unseen towers. An honest generalization number within France.
3. FIgLib frame level, California. True cross domain, and the one that predicts real
   deployment.

A large gap between 2 and 3 quantifies the cost of domain shift. That is a finding worth
reporting, not a failure to hide.

### Does FIgLib ship bounding box annotations? (no, verified on disk 2026-08-31)

I inspected a downloaded sequence, `20160604_FIRE_rm-n-mobo-c`, and found 81 `.jpg` files
plus 1 `.mp4`, with zero non image files. No `.txt`, `.xml`, `.csv`, or `.json`.

The only labels live in the filenames: `<unix_ts>_<offset>.jpg` where offset is seconds from
ignition, running from -02400 to +02400. So FIgLib gives frame level smoke or no smoke and
never box locations, which confirms it can be a benchmark but never a training set for a
box detector.

A third party box annotation repo exists, aiformankind/wildfire-smoke-dataset, but it has
been dead since 2021 and is licensed CC BY-NC-SA, meaning non commercial. Not used.

### Design option, not scheduled: pseudo labelling to close the France to California gap

The idea is to run the French trained model on California frames, keep the confident
predictions, and train on them. This is an established technique, usually called pseudo
labelling or self training.

The known killer is confirmation bias. The model's errors become its training data, so it
grows more confident in the same mistakes. If it reads Californian fog as smoke, pseudo
labelling teaches it that fog is smoke, permanently.

FIgLib is unusually safe for this because the filename offsets give free ground truth on
box existence, though not location. Any box drawn on a pre ignition frame is definitionally
wrong, since no fire exists yet. Discard it and count it, and that count is a free, exact
false positive rate on real California imagery. Any box on a post ignition frame is at
least plausible, because smoke genuinely is present. The filenames rather than the model
decide whether it was right, and that is what breaks the feedback loop.

Safeguards worth stacking: confidence thresholding, temporal consistency since real smoke
persists and grows across consecutive frames while noise flickers, human spot checks of a
sample, and never training on pseudo labels alone. Always mix with the real French boxes as
an anchor.

Sequencing matters. Measure the tier 3 gap first. If the French model already does fine on
California this is unnecessary complexity, so only pursue it if the gap is genuinely bad.

### Box outline thickness has to adapt to box size (noticed 2026-08-31)

Drawing row 12 with `linewidth=2` exposed the problem. Its boxes are 20.3 by 6.6 px and
20.1 by 9.9 px, so a 2px outline consumes 68% and 52% of the box respectively. You end up
looking at more border than smoke, which defeats the point of checking labels visually. Row
0's box, at 171.8 by 77.8 px, loses only 7% to the same outline.

The fix for visualization is to scale linewidth to box size, something like
`linewidth = max(0.5, min(2, box_h/10))`, or for genuinely tiny boxes to crop and zoom the
region instead of outlining it in place. This is display only and does not affect the model.

### How small is smoke, actually? (measured over 2,894 boxes across 3,000 rows)

    1st pct  0.0134%   |  25th 0.0667%  |  median 0.1356%
    75th     0.3047%   |  99th 3.76%
    smallest 0.00742%  |  largest 36.6%

That is roughly a 5,000x range, and 38% of all boxes are under 0.1% of the frame.

Row 0, at 1.45%, is not typical. It sits in about the top 10% by size. Typical smoke looks
like row 12: a smudge around 20px wide.

The consequences for training are real. Small object detection is a known weakness of the
YOLO family. The default `imgsz=640` downscales a 20 by 7 box to roughly 10 by 3 px, at or
below what the architecture can resolve, which makes imgsz an actual decision rather than a
default to accept. Higher imgsz costs GPU memory and time, and that tradeoff needs
measuring rather than guessing. Eval also has to bucket by box size, because a single
aggregate mAP will hide complete failure on the smallest third while looking acceptable
overall.

### Site grouping and split, done (2026-09-01)

8 physical sites from 39 camera names, via `cam.rsplit('-', 1)[0]`:

    brison  10,605 (35.9%)  |  courmettes 6,553  |  marguerite 4,433
    cabanelle  2,416        |  ferion     1,944  |  croix-augas 1,873
    valbonne   1,409        |  serre-de-barre 304

Holding out marguerite and valbonne gives `Counter({'train': 23695, 'val': 5842})`, which
is 19.8% val. 23,695 plus 5,842 is 29,537, so nothing was lost or double counted. Zero site
leakage.

### Two bugs hit while writing that, both worth remembering

No output at all from a loop that fills a collection means nothing was ever added. My
`sites[site] += 1` line was missing, so the loop computed `site` and discarded it every
pass. The symptom distinction is worth keeping: blank output means the collection is empty,
wrong output means it filled incorrectly. Different causes, different fixes. The habit that
catches it is `print(len(collection))` right after a loop that is supposed to fill
something.

`camera.replit(...)` instead of `rsplit` gave `AttributeError: 'str' object has no
attribute 'replit'`, and the traceback's last line named it exactly. I also learned why
that traceback was so long. `Counter()` consuming a generator expression means
`split_for()` runs lazily from deep inside `collections/__init__.py`, so the library frames
are just the call path. Skip them and find the frame pointing at my own file.

### Project decision (2026-09-01): full scope, Sept 17 is a checkpoint not a deadline

I considered cutting Phase 3, meaning FastAPI, Postgres, S3, Docker, and k3s, around 8
build tasks, in order to hit Sept 17. I decided against it. Nothing gets removed. Sept 17
becomes a progress checkpoint instead, and the pace is deliberately uneven, heavy some days
and light others.

The honest pace data behind that: days 1 to 3 of the plan took 4 calendar days, Aug 29 to
Sep 1. Extrapolating, the remaining 17 plan days land nearer Sept 22 to 24 than Sept 17.
That is accepted rather than a problem to solve by cutting.

The reason for keeping Phase 3 is that containerization and a real API contract are the
parts that show up most often in job descriptions, so cutting them would remove resume
value to protect a self imposed date nobody else set.

The consequence for tracking is that dated days stop being meaningful at a variable pace.
The plan should be read as an ordered queue, meaning what is next, rather than a calendar
meaning what is due today.

### The single_cls bug (2026-09-02), which cost one 7.7 hour training run

The symptom: training reported mAP50 climbing to 0.753 over 30 epochs, but loading the
saved `best.pt` and running `val()` standalone gave mAP50 of 0.029. Same weights, same val
set, a 26x disagreement. `last.pt` was worse still at 0.0287.

The metrics alone could not explain it. Predicting on one image and looking at the output
did. The model drew 10 boxes at confidence exactly 1.00, tiled as even vertical strips
across the lower frame. That is a collapsed box regression head emitting grid positions
rather than detections. It also explained the numbers, because strips that large overlap
almost any real box by accident, giving recall of 0.84 while being almost entirely wrong,
with precision between 0.03 and 0.07.

A second clue sat in the same picture. The boxes were labelled "item" rather than "smoke,"
which is Ultralytics' placeholder when `single_cls=True` overrides the names in
`data.yaml`.

Confirmed by a controlled test, 2 epochs, identical config minus the flag:

                         in-training mAP50   standalone val()   gap
      with single_cls          0.753              0.029         26x
      without                  0.660              0.660         none

It also trained better. Epoch 2 scored 0.660 without the flag against 0.534 with it. Final
proof: on a val image with zero ground truth boxes, the broken model drew 10 boxes at
confidence 1.00 while the fixed model correctly predicted nothing.

The root cause of the mistake was copying `single_cls=True` from Pyronear's `args.yaml`
without asking why they needed it. My labels were already remapped to class 0 and my
`data.yaml` already declared `nc: 1`, so the dataset was single class by construction. The
flag had nothing to collapse and only interfered.

What I took from it:

1. A reference config is a reference, not a template. Ask what each setting is for before
   copying it.
2. When metrics contradict each other, stop doing metric archaeology and look at a
   prediction. One image answered what four `val()` runs could not.
3. Confidence of exactly 1.00 is a red flag, not a good sign. Real detections vary, at 0.81,
   0.64, 0.43. Uniform 1.0 means a saturated output, which means breakage.
4. Always sanity check against a known empty image. Predicting nothing on nothing is a real
   test, and it is cheap.

### HPWREN access, working URLs (verified live 2026-09-03)

`c1.hpwren.ucsd.edu` and `c2.hpwren.ucsd.edu` are dead. DNS resolves, with c1 pointing at
169.228.44.159, but connections time out. Every HPWREN doc page still lists them, including
the 2021 "Camera Image Access" overview, so those docs are stale. Everything moved to
CloudFront.

What works, all verified by actual fetch:

Live frame, always current:

    https://cdn.hpwren.ucsd.edu/RT/<camera>.jpg

Verified on bh-n-mobo-c: 200, 3072x2048, 188 KB, with Last-Modified 52 seconds old. This is
the live feed, one URL, no listing to parse.

Archive frame:

    https://cdn.hpwren.ucsd.edu/MTA/<camera>/large/<yyyymmdd>/Q<n>/<unix_ts>.jpg

Index of a 3 hour block, newline separated filenames:

    https://cdn.hpwren.ucsd.edu/hpwren-cameras/<cam>/<yyyy>/<yyyymmdd>/<yyyymmdd>_<cam>_Q<n>.txt

That index is only published after the block closes. Q6 gave 180 names while Q7 returned
403 during its own block, so the index route lags up to 3 hours. That is why `/RT/` exists.

Camera manifest:

    https://www.hpwren.ucsd.edu/cameras/sites.js

81 sites, 503 cameras, 199 of them color, with lat, long, elevation, and azimuth per camera.

Q blocks run on local Pacific time: Q1 covers 00-03, Q2 03-06, Q3 06-09, Q4 09-12, Q5 12-15,
Q6 15-18, Q7 18-21, Q8 21-24. Q6 spanned 15:00:04 to 17:59:05 local.

Cadence is confirmed at 1 frame per minute. Q6 held exactly 180 frames across 3 hours, with
deltas of 61, 60, 60, 59, 61, and 60 seconds. The one frame per minute design matches the
source exactly.

On liveness, sites.js marks all 503 cameras `"active": "y"`, so that flag is useless as a
liveness signal. The real test is fetching `/RT/<cam>.jpg` and checking Last-Modified
freshness, which is the same call the live loop makes anyway. Filter on
`imager == "color"`, the `-c` suffix, because `-m` cameras are monochrome and the model
trains on RGB.

On policy, attribution to HPWREN is required if images are published. There is no signed
license, no registration, and no stated rate limit. One request per minute per camera
matches their publish rate, so a live loop is inherently polite. Backfills stay sequential.

### Three resolutions now in play (measured 2026-09-03), so the size_bucket default is dead

    PyroNear (training)   1280x720    16:9   0.92 MP    sampled 500 images, 100% uniform
    FIgLib (archive)      2048x1536    4:3   3.1  MP    all 81 frames of the one sequence
    HPWREN live           3072x2048    3:2   6.3  MP    verified by download

Live frames are 6.8x the pixel count of the training data, at a third aspect ratio.

The first consequence is that `size_bucket(box, img_w=1280, img_h=720)` has to take
required dimensions. A default is wrong for two of the three sources, and passing the wrong
denominator inflates `frac` and mislabels small boxes as medium. I would end up concluding
the model handles small smoke better than it does.

The second consequence is that downscaling eats small smoke. At `imgsz=1024` a 3072x2048
frame is squeezed about 3x, so a 30px plume reaches the model as 10px. 38% of PyroNear
boxes are already under 0.1% of frame area. That is a concrete, measured argument for
tiling rather than a theory, and it is worth one experiment once I have honest weights:
the same live frame, full frame against tiled.
