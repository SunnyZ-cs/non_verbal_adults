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

## Data Collection & Gaze Analysis Workflow

Because Proliferate is a static-file hosting platform, it does not support native video uploads. Instead, this pipeline packages compressed webcam recordings inside the participant's submission payload. 

Once your study is complete, follow these steps to extract and analyze the gaze data using **MediaPipe Face Mesh Iris Tracking**:

### Step 1: Download Results from Proliferate
Download the following CSV files from the Proliferate dashboard:
1.  **Videos CSV**: e.g., `looking_time_test_run_with_5-videos.csv` (contains the Base64 video streams).
2.  **Test Order CSV**: e.g., `looking_time_test_run_with_5-test_order.csv` (contains the condition sequence mapping).

### Step 2: Run Gaze Analysis Pipeline
Run the included python pipeline script `process_videos_mediapipe.py`. This script automatically decodes the Base64 streams, crops the videos using `ffmpeg` to target the last 20 seconds (the freeze-frame phase), runs high-precision iris tracking, and maps the conditions to `proximal` or `distal` trial types:

```bash
python3 process_videos_mediapipe.py <path_to_videos_csv> -t <path_to_test_order_csv> [output_directory]
```

*Example:*
```bash
python3 process_videos_mediapipe.py looking_time_test_run_with_5-videos.csv -t looking_time_test_run_with_5-test_order.csv mediapipe_output
```

### Output Files

1.  **Summary CSV (`mediapipe_summary_results.csv`)**: 
    A table compiling the gaze statistics for all participants.
    *   `ParticipantID`: Prolific/Proliferate worker ID.
    *   `TrialIndex`: Sequence index (`1` or `2`).
    *   `TrialType`: Evaluated condition (`proximal` or `distal`).
    *   `Left Looking Frames` / `Right Looking Frames` / `Center Looking Frames`: Frame counts for each gaze direction.
    *   `Left Looking %` / `Right Looking %`: Percentage of valid gaze frames spent looking left vs. right.
    
2.  **Detailed Annotation Files (`mediapipe_output/`)**:
    Contains frame-by-frame gaze classifications and raw horizontal iris ratios.
    *   File naming format: `videoStream_adult_[ParticipantID]_[TrialIndex]_[TrialType].txt`
    *   Inside: `[FrameNumber],[GazeDirection],[IrisRatio]`

### Dependencies
Before running the script, ensure you have the required packages:
```bash
pip install pandas numpy opencv-python mediapipe
```
And make sure `ffmpeg` is installed on your system.

