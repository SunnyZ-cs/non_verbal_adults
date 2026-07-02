#!/bin/bash
# config.sh
#
# EDIT THIS FILE before each new data-collection round, then leave everything
# else in this folder alone. Every script (transfer, setup, the SLURM array,
# retrieve) reads its settings from here, so there's exactly one place to
# update when you have a new batch of participants.
#
# This file gets rsynced up to Sherlock along with everything else, and gets
# sourced there too - so Mac-side and Sherlock-side scripts always agree on
# where things live.

# Your SUNet ID.
export SUNET_ID="ouzhao"

# A short label for THIS batch of data, e.g. "adult_pilot61", "prereg_run1".
# Each run gets its own directory on Sherlock
# ($GROUP_HOME/mediapipe_pipeline/<RUN_NAME>), so old and new batches never
# mix, and you can always go back and re-check an old run's results.
export RUN_NAME="adult_pilot61"

# Exact filenames of this batch's data, as they sit on your Desktop right
# now. Change these two lines for each new export from the Proliferate
# dashboard.
export VIDEOS_CSV_FILENAME="looking_time_formal_pilot-videos.csv"
export TEST_ORDER_CSV_FILENAME="looking_time_formal_pilot-test_order.csv"

# ---- Usually no need to touch anything below this line ----

# Where all runs live on Sherlock (each in its own $RUN_NAME subfolder).
# Deliberately a SEPARATE namespace from the kids/iCatcher pipeline
# ($GROUP_HOME/icatcher_pipeline) - different study, different venv
# (mediapipe vs. torch), no reason for them to share a directory tree.
#
# IMPORTANT: this must stay single-quoted / unexpanded here. $GROUP_HOME
# only exists as an environment variable on SHERLOCK, not on your Mac - so
# this literal string is passed through untouched by the Mac-side scripts
# and only gets expanded once it reaches a remote shell on Sherlock (via
# ssh/rsync) or is used directly inside the sbatch script, which runs on
# Sherlock itself.
export SHERLOCK_BASE_DIR='$GROUP_HOME/mediapipe_pipeline'

# No $GROUP_HOME on your account (no PI lab allocation)? Comment out the
# line above and uncomment this one instead. Note $SCRATCH auto-purges
# files after 90 days of inactivity, so move final results off promptly:
# export SHERLOCK_BASE_DIR='$SCRATCH/mediapipe_pipeline'
