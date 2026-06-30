# Non-Verbal Looking Time Study - Adult Pilot Version

This folder contains the standalone **jsPsych (v7.3.1)** experiment pipeline for the adult version (ages 18+) of the non-verbal social interaction study. It is designed to be hosted on **Proliferate** and recruited via **Prolific**.

---

## Experiment Structure

1.  **Consent Form**: Standard research consent script (replicated from `Cause_Fault_Punishment/exp1/adults`).
2.  **Written Instructions**: Written guidelines explaining the webcam setup, camera calibration, positioning, and task sequence.
3.  **Webcam Calibration & Preview**: Displays a live webcam preview box with a circular centering target. Participants must align their face inside the target box before the "Continue" button is enabled.
4.  **Familiarization Phase**: Plays a randomized introduction combo GIF (`Fam_Combo_1.gif` to `Fam_Combo_8.gif` based on the selected index) followed by a 4-second freeze frame.
5.  **Test Phase 1 & 2**:
    *   Webcam recording automatically **starts** before the 3-second bullseye target.
    *   The test clip animation plays (18.76 seconds) followed by a static freeze frame (20 seconds).
    *   Webcam recording automatically **stops** and converts the video stream to a Base64 string saved directly to jsPsych.
6.  **Demographics**: Final questionnaire gathering age, gender, race, and ethnicity.
7.  **Submission**: Sends all response data and the Base64-encoded webcam video files directly to Proliferate (`proliferate.submit`).

---

## Data Collection & Extraction Workflow

Because Proliferate is a static-file hosting platform, it does not support native video uploads. Instead, this pipeline packages the webcam recordings directly inside the JSON response payload. 

Once your study is complete, follow these steps to extract the video files for analysis:

### Step 1: Download Responses
Download your experiment results from Proliferate (as a JSON file, e.g., `results.json`).

### Step 2: Extract the Video Files
Run the included python script to decode the Base64 streams back into standard `.webm` (or `.mp4`) files:

```bash
python3 extract_videos.py results.json
```

By default, this will create a directory called `videos_extracted/` containing files named in the following format:
`videoStream_adult_[ParticipantID]_[TrialIndex]_[Condition].webm`

*Example:* `videoStream_adult_P171569_1_distal.webm`

### Step 3: Run Gaze Tracking (iCatcher)
You can then run the extracted videos folder directly through your `iCatcher` processing pipeline:

```bash
python3 pilot_kids_version/process_icatcher.py
```
This naming schema ensures that the extraction is fully compatible with the existing gaze processing utilities.
