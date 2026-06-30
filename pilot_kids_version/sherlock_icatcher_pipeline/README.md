# Running process_icatcher.py on Sherlock's GPU partition

This is a ready-to-run package for processing all 73 participants'
videos through iCatcher+ on Sherlock, using one GPU job array task per
participant (much faster than one sequential job).

**Why this is a runbook and not something I ran for you:** Sherlock login
requires Duo two-factor approval on your phone, so I can't SSH in or submit
jobs on your behalf. Everything below is copy-paste-able from your own
Terminal.

## What I checked before building this

I validated your data against the original script's assumptions:

- JSON has 73 unique participant response UUIDs.
- The videos folder has 146 non-consent `.webm` files (2 per participant -
  frame 9 and frame 13), all 146 match the filename pattern the script
  expects, and all 146 UUIDs match exactly between the JSON and the videos
  (zero orphans either direction).
- Sample video durations are ~41.7-41.8s, consistent with the script's
  hardcoded assumption of a 41.76s clip (3s bullseye + 18.76s animation +
  20s freeze frame).
- Total videos folder size: **2.1 GB**.

So the data is clean - no filename or matching issues to fix before this can
run.

## What changed from your original script

`process_icatcher_sherlock.py` is `process_icatcher.py` with four changes:

1. `--gpu_id` is now a flag (default `0`), not hardcoded to `-1`. **This is
   the actual fix that makes it use a GPU at all** - the original always
   forced CPU regardless of what hardware you ran it on.
2. `--uuid` filters processing to one participant, so a SLURM job array can
   run all 73 in parallel.
3. The webm→mp4 temp directory is now unique per process (was a shared
   `temp_mp4/` folder that parallel jobs would have deleted out from under
   each other).
4. Each run writes its own `results/icatcher_summary_<uuid>.csv` instead of
   one shared file that parallel jobs would overwrite. `merge_results.py`
   combines them at the end.

## Files in this folder

| File | Purpose |
|---|---|
| `process_icatcher_sherlock.py` | The patched analysis script |
| `make_participant_list.py` | Builds `participants.txt` (the array index) |
| `merge_results.py` | Combines all 73 per-participant CSVs into one |
| `setup_env.sh` | One-time environment setup on Sherlock |
| `run_icatcher_array.sbatch` | The SLURM job array definition |
| `transfer_to_sherlock.sh` | rsyncs your data up from your Mac |
| `retrieve_results.sh` | rsyncs results back down to your Mac |

## Step-by-step

### 0. Confirm you can log in

```
ssh <your_sunet_id>@login.sherlock.stanford.edu
```

Approve the Duo push when prompted. Type `exit` once you're in - just
confirming this works before scripting around it.

### 1. Transfer your data and these scripts to Sherlock

From your **Mac** Terminal (not Sherlock):

```
cd ~/Desktop   # or wherever you saved this sherlock_icatcher_pipeline folder
bash sherlock_icatcher_pipeline/transfer_to_sherlock.sh <your_sunet_id>
```

This copies your `videos folder` (2.1 GB) and the JSON file from your
Desktop, plus all the scripts in this package, to
`$GROUP_HOME/icatcher_pipeline` on Sherlock. It'll prompt for Duo a couple
of times - that's normal, each rsync is a separate connection.

If your account doesn't have a `$GROUP_HOME` (likely, since you said this is
a brand-new personal account with no PI sponsorship yet), open
`transfer_to_sherlock.sh` and `run_icatcher_array.sbatch` and replace
`$GROUP_HOME` with `$SCRATCH` everywhere - `$SCRATCH` is available to every
account by default. (Note: files in `$SCRATCH` are subject to Sherlock's
auto-purge policy after a period of inactivity, so don't leave results
sitting there long-term - move final outputs back to your Mac when done.)

### 2. Set up the environment (one time only)

SSH into Sherlock, then grab an interactive GPU session so the setup script
can actually verify a GPU is visible:

```
ssh <your_sunet_id>@login.sherlock.stanford.edu
cd $GROUP_HOME/icatcher_pipeline   # or $SCRATCH/icatcher_pipeline
sh_dev -g 1
bash setup_env.sh
```

This creates a Python venv (Sherlock's docs explicitly recommend against
conda - see comments in the script), installs PyTorch + iCatcher+ + ffmpeg,
and prints whether a GPU was detected. Leave the GPU session
(`exit`) once it finishes.

Trigger the one-time model weights download (only needs to happen once,
shared across all 73 array tasks via `$ICATCHER_DATA_DIR`):

```
source venv/bin/activate
export ICATCHER_DATA_DIR=$GROUP_HOME/icatcher_pipeline/icatcher_models
icatcher "videos folder/<pick any one non-consent .webm or .mp4>" \
  --output_annotation /tmp/icatcher_test --gpu_id 0 --fd_model opencv_dnn
```

(Use `--gpu_id -1` here if you're not on a GPU node for this quick test -
the model download happens either way.)

### 3. Build the participant list

```
python make_participant_list.py "Whose-fault-is-it-_all-responses-identifiable.json" participants.txt
```

This prints `Use this for the SLURM array range: --array=0-72` - confirm it
says 72 (73 participants, zero-indexed).

### 4. Submit the job array

```
sbatch --array=0-72 run_icatcher_array.sbatch
```

Each of the 73 tasks requests 1 GPU on the public `gpu` partition (open to
any Sherlock account, no PI sponsorship needed) and processes one
participant's 2 videos. Expect some queue wait since `gpu` is shared
cluster-wide - check status with:

```
squeue -u $USER
```

Per-task logs land in `slurm_logs/icatcher_<jobid>_<arrayindex>.out` /
`.err`. A single participant (2 short clips) should take well under the
30-minute time limit set in the script; raise `--time` in
`run_icatcher_array.sbatch` if your queue waits suggest otherwise.

### 5. Merge results once the array finishes

```
python merge_results.py results participants.txt icatcher_summary_combined.csv
```

This combines all 73 per-participant CSVs and tells you if any are missing
(check that task's `.err` log if so - most likely cause is a corrupt/short
video or an out-of-memory GPU error, both visible in the log).

### 6. Pull results back to your Mac

From your **Mac** Terminal:

```
bash sherlock_icatcher_pipeline/retrieve_results.sh <your_sunet_id>
```

Lands in `~/Desktop/icatcher_results/`.

## If something needs adjusting

- **Job runs out of time/memory**: bump `--time` or `--mem` in
  `run_icatcher_array.sbatch`.
- **You get a PI/lab Sherlock allocation later**: switch `-p gpu` to your
  lab's owner partition in `run_icatcher_array.sbatch` for higher priority
  (no other changes needed).
- **iCatcher accuracy/options**: the analysis logic (which frames count as
  "left looking" etc.) is unchanged from your original script - I only
  touched GPU/parallelism plumbing, not the science.
