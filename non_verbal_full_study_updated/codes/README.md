# Non-Verbal Looking Time Study Animation Codes

This directory contains the Python scripts used to generate and reproduce all the counterbalanced visual stimuli (Familiarization and Test Trial GIFs/PNGs) for the unified **`non_verbal_full_study`** experiment.

All animations use the bubbly/glossy 3D visual style (with sphere highlights, gradient shading, and custom facial expressions) and feature the yellow star "authority" character carrying out star yanks using a magic wand.

**Anticipatory-cue shake mechanics (post-David-feedback revision):** the star's brief angry shake (the moment the sound cue fires, in `anticipatory_cue()` in all three of `warmup_single_character_trials.py`, `generate_causal_chains_test_trials.py`, and `generate_single_cause_test_trials.py`) is a **rotation-only wobble** of the star's points around its own center (`Agent.shake_rotation`, consumed by `Renderer.draw_star`'s `rotation` argument) -- the star's x/y position is never touched during the shake, so it never visibly shifts. All three scripts use the identical `SHAKE_ROTATION_AMPLITUDE = 0.14` (radians) and phase step, so the shake looks the same in warmup and test. The test-trial scripts also now call `dither()` (the same frame-collapse fix warmup already used) once on the full animation before any GIF is saved, so Pillow can no longer silently merge near-identical shake frames -- test-trial shakes now render every frame, same as warmup. Note: the *separate*, later shake during star removal (`give_punishment()` / `reveal_and_punish()`) is unrelated to the sound cue and still moves the star slightly toward the target -- only the anticipatory-cue shake was changed.

---

## Script Registry

### 1. [familiarization_trials.py](familiarization_trials.py)
*   **Intention**: Generates the 8 familiarization combo sequence animations (`Fam_Combo_1.gif` to `Fam_Combo_8.gif`) by interleaving the baseline scenarios (Trash, Tower, Toy, Flower) with alternating reward and punishment outcomes.
*   **Execution**:
    ```bash
    python3 familiarization_trials.py
    ```
*   **Outputs**: Creates the `.gif` animations in this directory and copies them automatically to `../materials/`.

### 2. [extract_familiarization_freezes.py](extract_familiarization_freezes.py)
*   **Intention**: Extracts the final frame from each of the 8 familiarization combo animations and saves it as a static freeze PNG image (`Fam_Combo_1_freeze.png` to `Fam_Combo_8_freeze.png`). These are used as debrief/freeze screens in Lookit trials.
*   **Execution**: *(Run after familiarization_trials.py has completed)*
    ```bash
    python3 extract_familiarization_freezes.py
    ```
*   **Outputs**: Saves the freeze `.png` files in this directory and copies them to `../materials/`.

### 3. [generate_single_cause_test_trials.py](generate_single_cause_test_trials.py)  *(post SECOND lab-meeting revision, David's anticipation-cue redesign)*
*   **Intention**: Generates standard and reverse mirrored test trial animations representing the **single-cause** condition. The proximal agent directly collides with and breaks the gray cube. Before that, the distal/bystander agent makes a small, clearly irrelevant hop-in-place (temporally separated by pauses on both sides, `HOP_PRE_PAUSE`/`HOP_POST_PAUSE` around `AnimationHelper.jump()`), so it isn't the only character that never moves at all -- the critical difference stays "part of the causal chain or not," not "moved or not." The causal event is shown **once** (no longer repeated ×3). Characters are drawn **eyes-only**; the star authority keeps its full expressions.
*   **Punishment sequence** (shared with the chains script and the warmup script; see `anticipatory_cue()` / `reveal_and_punish()`): almost immediately after the cube breaks, the star goes angry and briefly shakes in place (still dead-centered) -- this is also where the non-directional sound cue fires (`sound_frame`, reported per-clip) -- then the star settles, staying angry and centered. That settled moment is the **part1/part2 split point** (`split_frame`, computed dynamically, no longer hardcoded), and is exactly where the anticipatory-freeze PNG is extracted. The 2-2.5s anticipatory hold itself lives on the JS side (`antic_duration`), not baked into the GIF. Part2 then has the star approach the target and remove its star, unchanged from before.
*   **Execution**:
    ```bash
    python3 generate_single_cause_test_trials.py
    ```
*   **Outputs**: Exports standard/reverse animations and freeze PNGs, automatically copying them to `../materials/` under the prefix `single_cause_` (e.g. `single_cause_distal_test_final.gif`), plus `single_cause_timing.json` (per-clip `split_frame`/`sound_frame`/`part1_ms`/`sound_ms`).

### 4. [generate_causal_chains_test_trials.py](generate_causal_chains_test_trials.py)  *(post SECOND lab-meeting revision, David's anticipation-cue redesign)*
*   **Intention**: Generates standard and reverse mirrored test trial animations representing the **causal chain** condition. The distal agent rushes violently into the proximal agent, propelling it into the gray cube to break it -- shown **once** (no longer repeated ×3). A fixed `CHAINS_PAD` pause at the start of `run_chain()` keeps this script's part1 length frame-identical to `generate_single_cause_test_trials.py`'s (both currently split at frame 135 / 5.4s), since the JS uses one shared `part1_duration`/`antic_duration` pair across both contexts. Characters are drawn **eyes-only**; the star authority keeps its full expressions.
*   **Punishment sequence**: identical architecture to the single-cause script above (`anticipatory_cue()` centered angry+shake+sound, settle, dynamic split; `reveal_and_punish()` approach + removal).
*   **Execution**:
    ```bash
    python3 generate_causal_chains_test_trials.py
    ```
*   **Outputs**: Exports standard/reverse animations and freeze PNGs, automatically copying them to `../materials/` under the prefix `chains_` (e.g. `chains_distal_test_final.gif`), plus `chains_timing.json` (per-clip `split_frame`/`sound_frame`/`part1_ms`/`sound_ms`).

### 5. [warmup_single_character_trials.py](warmup_single_character_trials.py)  *(post SECOND lab-meeting revision, David's anticipation-cue redesign)*
*   **Intention**: Generates the 3 single-character punishment warmup animations used in the revised study design (replacing the old two-character familiarization combos as the warmup phase). Reuses the exact punishment choreography (approach → steal/damage → carry back) from `familiarization_trials.py`'s trash/tower/flower scenes, but with a single pink-circle character. The character is drawn **eyes-only**; the star authority keeps its full expressions, exactly as in the test trials.
*   **Left/center/right labeling**: the `left`/`center`/`right` in each output filename refers to the pink circle's x-position **at the punish moment**, not the prop's position. The character rests at exactly two x-positions per clip: the punish-moment position (also its start/end position -- `home_x` in `SCENES`) and the position beside/over the prop while committing the bad action. Each prop is kept close (70px away) to the character's home/punish-moment position. Current assignment: **tower** scene → `left` (x=200, tower at x=270), **trash** scene → `center` (x=400, exact canvas center; bin at x=330), **flower** scene → `right` (x=600, mirror of `left`; flower at x=530). Edit the `SCENES` dict to change any of this.
*   **Punishment sequence** (`anticipatory_cue()` / `give_punishment()`): after the bad action, almost immediately the star goes angry and briefly shakes in place at center (`PRE_SHAKE_PAUSE`=0.3s, `SHAKE_DURATION`=0.48s -- this is when the sound cue fires, `sound_cue_offset_ms` per position, reported in `warmup_timing.json`), then holds angry+centered for `ANTICIPATORY_PAUSE`=2.5s (baked directly into the warmup GIF, since warmups are a single continuous clip with no separate JS-side freeze phase), then approaches and removes the star as before.
*   **Execution**:
    ```bash
    python3 warmup_single_character_trials.py
    ```
*   **Outputs**: `warmup_punish_left.gif`, `warmup_punish_center.gif`, `warmup_punish_right.gif` (~16.7-17.1 s each, loop=1, holds last frame), plus `warmup_timing.json` (`durations_ms`/`sound_cue_offset_ms` per position), automatically copied to `../materials/`.

---

## Replication Guide

To generate and sync all material assets (test stimuli, warmups, and their
timing JSONs):
1. Make sure you have python `pillow` installed (`pip install Pillow`).
2. Run the scripts in order:
    ```bash
    python3 familiarization_trials.py
    python3 extract_familiarization_freezes.py
    python3 generate_single_cause_test_trials.py
    python3 generate_causal_chains_test_trials.py
    python3 warmup_single_character_trials.py
    ```
3. The non-directional sound cue (`../materials/punish_cue.mp3` /
   `punish_cue.wav`, played by the JS at the shake-onset offsets recorded in
   `chains_timing.json` / `single_cause_timing.json` / `warmup_timing.json`)
   is a static synthesized asset, not produced by any of the scripts above --
   it only needs to be regenerated if the cue sound itself should change.
