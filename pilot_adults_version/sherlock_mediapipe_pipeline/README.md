# MediaPipe gaze-coding pipeline for Sherlock (CPU)

Runs MediaPipe Face Mesh iris-tracking gaze coding for the adult version of
this study's Proliferate/Prolific videos on Sherlock, one SLURM array task
per participant. Sibling pipeline to `sherlock_icatcher_pipeline/` (the kids
version) - same design pattern, same repeatable recipe - adapted for a
different data format (base64-embedded videos in a CSV export, not
individual video files) and a different, CPU-only tracking model.

Built from and tested against the 61-participant adult pilot
(`looking_time_formal_pilot-videos.csv` / `-test_order.csv`); designed to be
reused as-is for the preregistered full study and any batch after that -
the only thing that should ever need editing between batches is `config.sh`.

**Status note:** this pipeline hasn't been run live on Sherlock yet the way
the kids/iCatcher+ pipeline was (that one got debugged interactively through
several real bugs). It's built with those same lessons pre-applied (see
"Known quirks" below), but a first live run may still surface something new
- happy to walk through it together the same way, if you want a second set
of eyes the first time you run it.

## Why CPU, not GPU

The sibling kids pipeline runs iCatcher+ (a PyTorch model) on Sherlock's
`gpu` partition, with real CUDA acceleration. This pipeline is different:
MediaPipe's Python `solutions.face_mesh` API runs its (small) TFLite model
on CPU only - there's no GPU delegate available for this specific API on
headless Linux. Requesting a GPU would just mean queuing longer on
Sherlock's scarcer `gpu` partition for no speed benefit, since there's
nothing to accelerate. `run_mediapipe_array.sbatch` requests Sherlock's
general-purpose `normal` CPU partition instead, which also tends to
schedule faster.

## How the data format differs from the kids pipeline

The kids study (Lookit) exports one video file per trial plus a JSON of
responses. This adult study (Proliferate) exports two CSVs instead:

- `looking_time_formal_pilot-test_order.csv` - one row per trial per
  participant, giving the `proximal`/`distal` condition sequence.
- `looking_time_formal_pilot-videos.csv` - one row per trial per
  participant, with the **webcam video itself embedded as a base64 string**
  in a `base64` column (Proliferate has no native video upload, so the
  study code base64-encodes each clip and submits it as response data).

There's no separate videos folder to transfer - it's all inside that one
(potentially large) CSV. `make_participant_list.py` splits it into small
per-participant CSVs before the array job runs, so no single array task
ever has to load the whole thing.

## Files in this folder

| File | Purpose | Runs on |
|---|---|---|
| `config.sh` | **The only file you edit between batches.** SUNet ID, run name, data filenames. | sourced by everything, both machines |
| `process_videos_mediapipe_sherlock.py` | The analysis script (one-participant-at-a-time) | Sherlock |
| `make_participant_list.py` | Splits the combined CSVs per participant + builds `participants.txt` (the array index) | Sherlock |
| `merge_results.py` | Combines all per-participant CSVs into one | Sherlock |
| `setup_env.sh` | One-time-per-account environment build | Sherlock |
| `run_mediapipe_array.sbatch` | The SLURM job array definition | Sherlock |
| `transfer_to_sherlock.sh` | rsyncs a batch's data + these scripts up | your Mac |
| `retrieve_results.sh` | rsyncs results back down | your Mac |

## How it's organized

Each batch of data ("run") gets its own directory on Sherlock, named after
`RUN_NAME` in `config.sh`:

```
$GROUP_HOME/mediapipe_pipeline/
  _shared/                  <- venv (built once, reused by every run)
  adult_pilot61/             <- this pilot's data + results (RUN_NAME="adult_pilot61")
  prereg_run1/                <- next batch, once you preregister and collect more data
```

Deliberately a separate directory tree from `icatcher_pipeline/` - different
study, different dependencies (mediapipe/opencv vs. torch), no reason to
share.

## One-time setup (do this once, ever)

### 0. Confirm Sherlock login works

```
ssh <your_sunet_id>@login.sherlock.stanford.edu
```

Approve the Duo push. `exit` once confirmed.

### 1. Build the shared environment

This only needs to happen once per Sherlock account - `setup_env.sh`
installs into a shared location (`_shared/`) that every future run reuses.
You need at least one run's `config.sh` transferred first (below) since
`setup_env.sh` reads it, but you won't need to repeat this step for later
batches unless a dependency needs updating (the script is safe to re-run -
it skips work already done).

## Every new batch of data (the repeatable recipe)

### 1. Point config.sh at the new batch

Open `config.sh` and update:

- `RUN_NAME` - a short label for this batch, e.g. `prereg_run1`
- `VIDEOS_CSV_FILENAME` - the exact filename of the new Proliferate videos export, as it sits on your Desktop
- `TEST_ORDER_CSV_FILENAME` - the exact filename of the new Proliferate test-order export, as it sits on your Desktop

Leave `SUNET_ID` and everything below the "usually no need to touch" line
alone unless your Sherlock setup changed.

### 2. Transfer the data

From your **Mac** Terminal:

```
cd ~/Desktop/sherlock_mediapipe_pipeline
bash transfer_to_sherlock.sh
```

One Duo prompt. This creates `$GROUP_HOME/mediapipe_pipeline/<RUN_NAME>/`
on Sherlock and fills it with both CSVs (renamed to the stable
`videos.csv` / `test_order.csv` on the remote side) and the pipeline
scripts.

The videos CSV scales with participant count - the 61-participant pilot's
was ~85MB, so budget proportionally more transfer time at 200+
participants (roughly 1.4MB/participant based on the pilot).

### 3. Set up the environment (only if this is the very first run ever)

Skip this step for the second and later batches - `_shared/` already has
what it needs.

```
ssh <your_sunet_id>@login.sherlock.stanford.edu
cd $GROUP_HOME/mediapipe_pipeline/<RUN_NAME>
bash setup_env.sh
```

(No `sh_dev`/GPU node needed here, unlike the kids pipeline - this all runs
on CPU, so the login node is fine for setup too.)

### 4. Build the participant list and submit the array

```
cd $GROUP_HOME/mediapipe_pipeline/<RUN_NAME>
python make_participant_list.py videos.csv test_order.csv
```

This prints the exact `--array=0-N` range to use, and warns about any
workerid present in one CSV but not the other.

```
sbatch --array=0-N run_mediapipe_array.sbatch
squeue -u $USER -r
```

**At 200+ participants**, throttle concurrency so you're not flooding the
shared `normal` partition with hundreds of tiny jobs simultaneously:

```
sbatch --array=0-N%40 run_mediapipe_array.sbatch
```

Your laptop going to sleep or losing its SSH connection does **not** affect
the array job - it runs entirely on Sherlock's compute nodes. Just
reconnect and check `squeue` whenever.

### 5. Check for failures, then merge

Once `squeue -u $USER -r` comes up empty:

```
ls results/ | wc -l                         # should equal your participant count
sacct -j <jobid> --format=JobID,State,ExitCode -X | awk '{print $2}' | sort | uniq -c
```

If some tasks show `FAILED` or the `results/` count is short, check that
task's log before merging:

```
cat slurm_logs/mediapipe_<jobid>_<arrayindex>.err
```

Once satisfied:

```
ml load python/3.9.0
source $GROUP_HOME/mediapipe_pipeline/_shared/venv/bin/activate
python merge_results.py results participants.txt mediapipe_summary_combined.csv
```

### 6. Retrieve results

From your **Mac** Terminal:

```
cd ~/Desktop/sherlock_mediapipe_pipeline
bash retrieve_results.sh
```

Lands in `~/Desktop/mediapipe_results_<RUN_NAME>/` - a separate folder per
batch.

## Known quirks

One of these was caught by actually decoding and running real pilot
footage through ffmpeg while building this pipeline (see below); the rest
are pre-applied from the sibling kids/iCatcher+ pipeline's real-world
Sherlock debugging, rather than waiting to rediscover them live:

- **The webcam recordings have bogus frame-rate container metadata, and
  the original script's ffmpeg command doesn't handle it.** Tested on real
  pilot data: `raw_frame_rate` reports `1000/1` (garbage - an artifact of
  browser `MediaRecorder` output, not a real capture rate). Without an
  explicit vsync setting, ffmpeg duplicates frames to fill that bogus
  declared rate: a genuine ~300-frame, ~15fps, 20-second clip became a
  ~20,000-frame output that was over 95% duplicate frames. Every one of
  those duplicates still costs a full MediaPipe inference pass, so this
  isn't just wasted compute - at 200+ participants it risks blowing past
  the sbatch time limit. `process_videos_mediapipe_sherlock.py` adds
  `-vsync vfr` to pass frames through as actually decoded, with no
  duplication. This is a bug in the original pilot script too, not a
  Sherlock-specific issue - worth pulling upstream into
  `process_videos_mediapipe.py` if you get a chance.
- **Sherlock's `ffmpeg` has no `libx264`** (no `--enable-gpl` in that
  build). The original pilot script (`process_videos_mediapipe.py`) uses
  `libx264`; `process_videos_mediapipe_sherlock.py` uses the built-in
  `mpeg4` encoder instead. If you ever see `Unknown encoder 'libx264'`,
  something reverted this.
- **Even `opencv-python-headless` still needs `libGL.so.1` in some
  builds** - confirmed live, this is a known packaging quirk (the headless
  variant avoids GTK/Qt GUI bindings, but the wheel can still dynamically
  link libGL). Since there's no root access to install a system package,
  `setup_env.sh` and `run_mediapipe_array.sbatch` both `ml load system
  mesa` (loaded *before* the python module, to avoid a libffi
  version-conflict warning between the two).
- **Sherlock's default compiler (`gcc` 4.8.5, RHEL7-era) can't build
  modern C++.** Confirmed live: `ml-dtypes` (a transitive mediapipe
  dependency) needs `-std=c++17`, which 4.8.5 doesn't support at all.
  `setup_env.sh` loads `gcc/12.4.0` (the same version Sherlock's own
  `ffmpeg` module was built with) before any pip install.
- **`pandas>=2.3` has no prebuilt wheel for Python 3.9** (EOL upstream),
  which forces a source build that fails on Sherlock's compiler toolchain
  regardless of the gcc fix above (it's a `meson`/`cython` issue, not
  just a C++ standard issue). `setup_env.sh` pins `pandas<2.3`.
- **A `$GROUP_HOME`-style path stored as a literal string needs a*second*
  expansion pass, and it's easy to get only one of the two places that
  need it.** `config.sh` stores `SHERLOCK_BASE_DIR` single-quoted (e.g.
  literally containing the text `$GROUP_HOME`) so the same file works on
  both your Mac (no `$GROUP_HOME`) and Sherlock. That means anything that
  *uses* it must force a second expansion - confirmed live, getting this
  wrong silently creates/references a directory literally named
  `$GROUP_HOME` instead of the real path, with no error. Two different
  fixes for two different contexts: Mac-side scripts resolve it once via
  `ssh host 'echo $GROUP_HOME/...'` (ssh always runs the remote command
  through a real shell); Sherlock-native scripts (`setup_env.sh`,
  `run_mediapipe_array.sbatch`) use `eval echo "$SHERLOCK_BASE_DIR"`. Also
  note: modern rsync (3.x, e.g. from Homebrew) defaults to
  `--protect-args`, which deliberately skips remote shell expansion for
  its own path arguments - so `rsync` in particular can't rely on the ssh
  trick above; only plain `ssh` can be used for that resolution step.
- **Spaces/`$VAR`s in remote paths break macOS's default `rsync`/`scp`.**
  `transfer_to_sherlock.sh` and `retrieve_results.sh` route everything
  through `rsync` over an explicit `ssh` invocation (never bare `scp`,
  which defaults to SFTP mode on modern macOS and also skips shell
  expansion).
- **`ml load` inside a script doesn't persist to your shell.** If you run
  Python commands manually after a script like `setup_env.sh` finishes,
  you'll need to `ml load system mesa`, `ml load python/3.9.0`, and
  `ml load system ffmpeg` yourself first in that shell, or you'll silently
  fall back to the ancient system Python (or hit the libGL error again).
- **Per-participant temp directories.** The original pilot script used one
  shared `temp_mediapipe_processing/` folder; running many participants in
  parallel (the whole point of the array) would have them delete each
  other's in-progress files. `process_videos_mediapipe_sherlock.py` uses a
  unique temp directory per process instead.
- **Job arrays with many pending tasks collapse in `squeue`'s default
  output** (e.g. one line reading `32166386_[10-72]` represents 63 tasks,
  not 1). Use `squeue -u $USER -r` to force one line per task when you
  need an accurate count.

## If something about the study design changes

`process_videos_mediapipe_sherlock.py` exposes `--crop_start` (default
21.76s, matching this study's 3s bullseye + 18.76s animation before the
freeze frame) and `--sensitivity` (default 0.012, the gaze-classification
threshold) as CLI flags in `run_mediapipe_array.sbatch` if the study's
timing or calibration needs adjusting in a future version.
