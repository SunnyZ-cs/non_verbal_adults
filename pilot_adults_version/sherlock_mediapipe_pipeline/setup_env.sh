#!/bin/bash
# setup_env.sh
#
# Run this ON SHERLOCK, inside a run's directory (i.e. after
# transfer_to_sherlock.sh, do `cd $GROUP_HOME/mediapipe_pipeline/<run_name>`
# first). It builds the Python environment needed to run MediaPipe gaze
# estimation.
#
# You only need to do this ONCE PER SHERLOCK ACCOUNT, not once per batch of
# data - the venv lives in a shared location
# ($GROUP_HOME/mediapipe_pipeline/_shared) and every run's directory reuses
# it. Re-running this script later is safe (it skips work that's already
# done) in case a dependency needs updating.
#
# Sherlock's own docs explicitly recommend AGAINST using conda/Anaconda
# (https://www.sherlock.stanford.edu/docs/software/using/anaconda/) because
# it tends to fill up $HOME and ship non-optimized binaries. We use a plain
# Python venv + Sherlock's module system instead, per their recommendation.
# This mirrors the sibling iCatcher+/kids pipeline's setup_env.sh.
#
# You can run this on a plain login-node shell (no GPU needed - see the
# note in run_mediapipe_array.sbatch about why this pipeline uses the CPU
# `normal` partition, not `gpu`). A dev node is still a reasonable place to
# do a first-time sanity test, just not required:
#   $ sh_dev
#   $ bash setup_env.sh

set -e

if [ ! -f ./config.sh ]; then
  echo "ERROR: run this from inside a run directory that has config.sh in it"
  echo "(i.e. cd \$GROUP_HOME/mediapipe_pipeline/<run_name> first)."
  exit 1
fi
source ./config.sh

# NOTE: SHERLOCK_BASE_DIR is intentionally stored as a literal, unexpanded
# string in config.sh (e.g. containing "$GROUP_HOME" as literal characters,
# not a live reference) so the same config.sh works whether it's read on
# your Mac (which has no $GROUP_HOME) or on Sherlock. That means a plain
# "${SHERLOCK_BASE_DIR}/_shared" substitution here would NOT expand
# $GROUP_HOME - bash only expands variables once per token and does not
# re-scan an already-substituted value for further $ references. Confirmed
# by direct testing: it silently creates a literal directory called
# "$GROUP_HOME" instead of resolving it. `eval echo` forces the needed
# second expansion pass, on this Sherlock-native shell where $GROUP_HOME
# really is set.
SHARED_DIR="$(eval echo "${SHERLOCK_BASE_DIR}")/_shared"
mkdir -p "$SHARED_DIR"
echo "Shared environment dir (reused across all runs): $SHARED_DIR"

# mesa provides libGL.so.1, which opencv-python-headless still dynamically
# links against in some builds despite being the "headless" variant (a
# known packaging quirk, confirmed live - the import fails with
# "libGL.so.1: cannot open shared object file" without this). Load it
# FIRST: loading it after python/3.9.0 pulls in a different libffi version
# and triggers an Lmod dependency warning (harmless in practice, but
# loading mesa first avoids it entirely).
ml load system mesa

echo "=== Checking available Python modules (pick the newest 3.9+ you see if this needs updating) ==="
ml spider python || true

# Adjust this version if `ml spider python` above shows a newer one you'd
# rather use for a fresh setup, AND if MediaPipe publishes wheels for it -
# MediaPipe's PyPI wheels only cover specific Python versions, so check
# https://pypi.org/project/mediapipe/#files before jumping to a much newer
# Python than 3.9 here.
PY_MODULE="python/3.9.0"
echo "Loading module: $PY_MODULE"
ml load "$PY_MODULE"
ml load system ffmpeg

# Sherlock's default system compiler is gcc 4.8.5 (RHEL7-era, 2015), which
# can't build modern C++ (confirmed live: mediapipe's ml-dtypes dependency
# needs -std=c++17, which 4.8.5 doesn't support at all, and separately
# pandas>=2.3's build needs a newer toolchain too). Load a modern gcc
# before any pip install that might need to compile something. 12.4.0 is
# the same version Sherlock's own ffmpeg module was built with, so it's
# known-good on this system.
ml load gcc/12.4.0

VENV_DIR="$SHARED_DIR/venv"
if [ -d "$VENV_DIR" ]; then
  echo "Venv already exists at $VENV_DIR - skipping creation, will just verify it below."
else
  echo "Creating venv at $VENV_DIR ..."
  # NOTE: use python3 explicitly here, not python - Sherlock's python module
  # only provides a `python3` binary, and falling through to the system
  # default `python` (very old, no venv/f-string support) is a common trap.
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip -q

# opencv-python-headless, NOT opencv-python: this runs on a headless
# compute node with no display server. Plain opencv-python pulls in GUI
# bindings (GTK/Qt) that commonly fail to import on headless Linux servers
# due to missing shared libraries (e.g. libGL.so.1) that aren't installed
# on minimal HPC node images. The script never calls cv2.imshow or any
# other GUI function, so headless is a strict improvement with no downside.
#
# pandas>=2.3 dropped prebuilt wheels for Python 3.9 (EOL upstream), which
# forces pip to compile from source - and that fails on Sherlock's older
# system compiler toolchain (confirmed live: "Compiler cython cannot
# compile programs"). Pin below 2.3 to stay on a wheel - same fix as the
# sibling iCatcher+ pipeline's setup_env.sh.
pip install -q "pandas<2.3" numpy opencv-python-headless mediapipe

echo "=== Checking for ffmpeg ==="
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg not found on PATH even after 'ml load system ffmpeg'."
  echo "Run 'ml spider ffmpeg' yourself and load the right one, or email srcc-support@stanford.edu."
fi
ffmpeg -version | head -1

# Sherlock's ffmpeg build does NOT include libx264 (no --enable-gpl), so
# process_videos_mediapipe_sherlock.py uses the built-in `mpeg4` encoder
# instead - that's already baked into the script, nothing to configure
# here. If you ever see "Unknown encoder 'libx264'", something reverted
# that fix.

echo ""
echo "=== Sanity check: confirm MediaPipe + OpenCV import cleanly ==="
python -c "
import cv2
import mediapipe as mp
print('OpenCV version:', cv2.__version__)
print('MediaPipe version:', mp.__version__)
fm = mp.solutions.face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)
print('FaceMesh initialized OK')
fm.close()
"

echo ""
echo "Setup complete."
echo "Shared dir:  $SHARED_DIR"
echo "Venv:        $VENV_DIR"
echo ""
echo "Next: python make_participant_list.py videos.csv test_order.csv, then submit the array job (see README.md)."
