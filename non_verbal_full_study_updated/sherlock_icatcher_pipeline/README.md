# iCatcher+ gaze-coding pipeline for Sherlock (GPU)

Runs iCatcher+ gaze coding for this study's Lookit videos on Sherlock's GPU
partition, one SLURM array task per participant. Originally built and
tested end-to-end on the 73-participant pilot; designed to be reused as-is
for the preregistered full study (200+ participants) and any batch after
that - the only thing that should ever need editing between batches is
`config.sh`.

## How it's organized

Each batch of data ("run") gets its own directory on Sherlock, named after
`RUN_NAME` in `config.sh`:

```
$GROUP_HOME/icatcher_pipeline/
  _shared/                  <- venv + downloaded iCatcher+ model (built once, reused by every run)
  pilot73/                  <- this pilot's data + results (RUN_NAME="pilot73")
  prereg_run1/               <- next batch, once you preregister and collect more data
  prereg_run2/                <- etc.
```

This keeps different batches of data (and their results) from ever
overwriting each other, while the expensive one-time setup (environment,
model download) is shared across all of them.

## Files in this folder

| File | Purpose | Runs on |
|---|---|---|
| `config.sh` | **The only file you edit between batches.** SUNet ID, run name, data filenames. | sourced by everything, both machines |
| `process_icatcher_sherlock.py` | The analysis script (GPU-enabled, one-participant-at-a-time) | Sherlock |
| `make_participant_list.py` | Builds `participants.txt` (the array index) from the JSON | Sherlock |
| `merge_results.py` | Combines all per-participant CSVs into one | Sherlock |
| `setup_env.sh` | One-time-per-account environment build | Sherlock |
| `run_icatcher_array.sbatch` | The SLURM job array definition | Sherlock |
| `transfer_to_sherlock.sh` | rsyncs a batch's data + these scripts up | your Mac |
| `retrieve_results.sh` | rsyncs results back down | your Mac |

## One-time setup (do this once, ever)

### 0. Confirm Sherlock login works

```
ssh <your_sunet_id>@login.sherlock.stanford.edu
```

Approve the Duo push. `exit` once confirmed.

### 1. Build the shared environment

This only needs to happen once per Sherlock account - `setup_env.sh`
installs into a shared location (`_shared/`) that every future run reuses.
You still need at least one run's data transferred first (below) so the
script has a sample video to trigger the iCatcher+ model download, but you
won't need to repeat this step for later batches unless a dependency needs
updating (the script is safe to re-run - it skips work already done).

## Every new batch of data (the repeatable recipe)

### 1. Point config.sh at the new batch

Open `config.sh` and update:

- `RUN_NAME` - a short label for this batch, e.g. `prereg_run1`
- `JSON_FILENAME` - the exact filename of the new Lookit export, as it sits on your Desktop
- `VIDEOS_FOLDER_NAME` - the exact folder name containing that batch's videos, as it sits on your Desktop

Leave `SUNET_ID` and everything below the "usually no need to touch" line
alone unless your Sherlock setup changed (e.g. you got a PI lab allocation
and want to switch from `$SCRATCH` to `$GROUP_HOME`).

### 2. Transfer the data

From your **Mac** Terminal:

```
cd ~/Desktop/sherlock_icatcher_pipeline
bash transfer_to_sherlock.sh
```

One Duo prompt (the script reuses a single authenticated connection for
everything). This creates `$GROUP_HOME/icatcher_pipeline/<RUN_NAME>/` on
Sherlock and fills it with the videos folder, the JSON (renamed to the
stable `data.json` on the remote side), and the pipeline scripts.

Rough timing: transfer time scales with your video data's size and your
home upload bandwidth, not file count - budget more time for 200+
participants than the pilot's ~2GB/225 files took.

### 3. Set up the environment (only if this is the very first run ever)

Skip this step for the second and later batches - `_shared/` already has
what it needs.

```
ssh <your_sunet_id>@login.sherlock.stanford.edu
cd $GROUP_HOME/icatcher_pipeline/<RUN_NAME>
sh_dev -g 1
bash setup_env.sh
exit   # leave the GPU dev session once it finishes
```

### 4. Build the participant list and submit the array

Back on the Sherlock **login node** (not the dev GPU session):

```
cd $GROUP_HOME/icatcher_pipeline/<RUN_NAME>
python make_participant_list.py data.json participants.txt
```

This prints the exact `--array=0-N` range to use (0-72 for 73
participants, 0-199 for 200, etc.) - always copy that number rather than
assuming, in case a participant has no UUID recorded.

```
sbatch --array=0-N run_icatcher_array.sbatch
squeue -u $USER -r
```

**At 200+ participants**, throttle concurrency so you're not requesting
200 GPUs at once - it schedules faster and avoids any per-user job/GPU
caps:

```
sbatch --array=0-N%20 run_icatcher_array.sbatch
```

(`%20` = never run more than 20 array tasks at a time; all 200 still get
queued and will run in batches of 20.)

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
cat slurm_logs/icatcher_<jobid>_<arrayindex>.err
```

Once satisfied:

```
ml load python/3.9.0
source $GROUP_HOME/icatcher_pipeline/_shared/venv/bin/activate
python merge_results.py results participants.txt icatcher_summary_combined.csv
```

(Both the `ml load` and `source .../activate` are needed in a fresh login
shell - the venv's Python binary depends on a shared library that only
resolves once the module is loaded.)

### 6. Retrieve results

From your **Mac** Terminal:

```
cd ~/Desktop/sherlock_icatcher_pipeline
bash retrieve_results.sh
```

Lands in `~/Desktop/icatcher_results_<RUN_NAME>/` - a separate folder per
batch, so old and new results sit side by side.

## Known quirks (already fixed in these scripts - here for context)

These were all discovered live while running the pilot. They're baked into
the scripts above, but documented here so future-you (or a collaborator)
understands *why* the scripts look the way they do, and doesn't
accidentally "simplify" one of these back into a bug:

- **Spaces in remote paths break macOS's default `rsync`/`scp`.** Older
  BSD rsync (what Apple ships) and newer OpenSSH's SFTP-mode `scp` both
  mishandle paths with spaces or `$VAR` references on the remote side.
  `transfer_to_sherlock.sh` and `retrieve_results.sh` route everything
  through `rsync` over an explicit `ssh` invocation (never bare `scp`) to
  avoid this.
- **A `$GROUP_HOME`-style path stored as a literal string needs a
  *second* expansion pass, and it's easy to get only one of the two
  places that need it.** `config.sh` stores `SHERLOCK_BASE_DIR`
  single-quoted (e.g. literally containing the text `$GROUP_HOME`) so the
  same file works on both your Mac (no `$GROUP_HOME`) and Sherlock. That
  means anything that *uses* it must force a second expansion - getting
  this wrong silently creates/references a directory literally named
  `$GROUP_HOME` instead of the real path, with no error (confirmed live).
  Two different fixes for two different contexts: Mac-side scripts
  resolve it once via `ssh host 'echo $GROUP_HOME/...'` (ssh always runs
  the remote command through a real shell); Sherlock-native scripts
  (`setup_env.sh`, `run_icatcher_array.sbatch`) use
  `eval echo "$SHERLOCK_BASE_DIR"`. Also note: modern rsync (3.x, e.g.
  from Homebrew) defaults to `--protect-args`, which deliberately skips
  remote shell expansion for its own path arguments - so `rsync` can't be
  used for the resolution step itself, only plain `ssh` can.
- **`icatcher --gpu_id` defaults matter.** The original pilot script had
  this hardcoded to `-1` (CPU-only) - `process_icatcher_sherlock.py` makes
  it a flag, defaulting to `0`.
- **Sherlock's `ffmpeg` module has no `libx264`** (no `--enable-gpl` in
  that build). The pipeline uses the built-in `mpeg4` encoder instead - if
  you ever see `Unknown encoder 'libx264'`, something reverted this.
- **`pandas>=2.3` has no prebuilt wheel for Python 3.9** (EOL upstream),
  which forces a source build that fails on Sherlock's compiler toolchain.
  `setup_env.sh` pins `pandas<2.3`.
- **`ml load` inside a script doesn't persist to your shell.** Running
  `bash setup_env.sh` loads modules only within that subprocess; if you
  then run Python commands manually in the same terminal afterward,
  you need to `ml load python/3.9.0` (and `ml load system ffmpeg`) yourself
  first, or you'll silently fall back to the ancient system Python.
- **`run_icatcher_array.sbatch` needs its own `ml load system ffmpeg`.**
  It's a separate process from your interactive shell, so module loads
  done there don't carry over either - the sbatch script loads everything
  it needs itself.
- **Job arrays with many pending tasks collapse in `squeue`'s default
  output** (e.g. one line reading `32166386_[10-72]` represents 63 tasks,
  not 1). Use `squeue -u $USER -r` to force one line per task when you
  need an accurate count.

## If something about the study design changes

`process_icatcher_sherlock.py` has CLI flags for the trial timing
(`--freeze_duration`, `--anim_duration`, `--bullseye_duration`) in case a
future version of the study changes clip length - defaults match this
study's current design (3s bullseye + 10.82s animation + 8s freeze). The
filename-parsing regex assumes Lookit's standard export naming convention
(`videoStream_..._<frame>-start-record-plugin-multiframe_<uuid>_...`) and
`frame_idx == 9` / `frame_idx == 13` mapping to the two trial conditions -
if the study's trial structure changes, `parse_video_filename()` and the
condition-assignment logic in `process_single_video()` are the two places
to update.

## Revised design (post SECOND lab meeting, David's anticipation-cue redesign) — timing cheat sheet

Per David: for both warmup and test, the punishment sequence now reads as
bad outcome -> almost immediately, the star (angry face + brief shake +
non-directional sound cue), still fully centered -> star settles, staying
angry and centered -> 2-2.5s anticipatory pause (the anticipatory-looking
window; both characters still matched, nothing indicates direction) -> star
moves over and takes the target's star. The causal event is now shown ONCE
(not ×3), so a repeated-viewing scan pattern can't carry into the
anticipatory window. In single_cause, the distal/bystander character makes a
small, clearly irrelevant hop-in-place before the proximal character acts.

Test-trial recording timeline (one webcam segment per test trial):

| phase | starts at | duration |
|---|---|---|
| bullseye | 0.00 s | 3.00 s |
| part1 (causal event ×1, angry+shake+sound, settles centered) | 3.00 s | 5.44 s |
| **anticipatory freeze** (angry star, static, centered; target unknowable) | 8.44 s | 2.50 s |
| part2 (authority approaches target, removes star) | 10.94 s | 2.88 s |
| outcome freeze (post-punishment looking) | 13.82 s | 8.00 s |

The non-directional sound cue fires **4.92 s into part1** (7.92 s into the
recording), at the onset of the star's brief shake.

Total recording length per test trial: ~21.82 s (down from ~32.76 s under
the first-round redesign, mainly from dropping the causal-event repeat and
tightening the pre-cue gap; the outcome freeze itself is unchanged at 8s
-- shortened from 20s in the first round after window-comparison analyses
showed the unpunished-preference effect concentrated in the first few
seconds and away-looking rising later in the window; see
`report_to_david.md`).

- `process_icatcher_sherlock.py` crops at **13.82 s** and scores the outcome freeze.
- For the **anticipatory window (8.44–10.94 s)** run the full-video pass:
  `sbatch --array=0-N run_icatcher_full_array.sbatch` (annotates uncropped videos into `icatcher_output_full/`).
- Warmup phase: three punishment-only warmups (single pink-circle character at left/center/right, order randomized).
  The order is recorded in the session JSON (`randomization_info.warmup_order` and per-trial `warmup_position`).
  Each warmup GIF now runs the same redesigned punishment sequence (immediate
  angry+shake+sound, 2.5s static angry hold, then approach+removal) and is
  ~16.7-17.1s long (was ~13.4-13.9s under the first-round redesign).
- The anticipatory-cue shake (all three GIF-generating scripts) is a
  rotation-only wobble of the star's points -- x/y position never changes --
  and ends with one extra "settled" frame at neutral rotation before holding,
  so it reads as a complete shake rather than getting cut off mid-tilt. Test
  trials no longer use `Shape.CIRCLE` or `Color.PINK` for any agent, since
  the warmup's single character is a pink circle.
- All characters are rendered with eyes only (no mouths/expressions); the star authority keeps its expressions.
- Exact per-clip split/sound-cue frame numbers live in `materials/chains_timing.json`, `materials/single_cause_timing.json`, and `materials/warmup_timing.json`.
