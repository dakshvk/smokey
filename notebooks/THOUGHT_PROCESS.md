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
