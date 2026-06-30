#!/usr/bin/env python3
import os
import sys
import json
import base64
import subprocess
import shutil
import pandas as pd
import numpy as np
import cv2

try:
    import mediapipe as mp
except ImportError:
    print("Error: MediaPipe is not installed. Please run: pip install mediapipe")
    sys.exit(1)

def run_mediapipe_gaze(video_path, output_txt_path, threshold_right=0.42, threshold_left=0.53):
    """
    Executes gaze tracking using MediaPipe Face Mesh iris landmarks on a video clip.
    Saves frame-by-frame annotations to output_txt_path.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  Error: Could not open video file '{video_path}'")
        return 0, 0, 0, 0
        
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    frame_idx = 0
    left_count = 0
    right_count = 0
    center_count = 0
    noface_count = 0
    
    out_lines = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_idx += 1
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            
            # Right eye coordinates: outer 33, inner 133, iris center 468
            r_outer = landmarks[33]
            r_inner = landmarks[133]
            r_iris = landmarks[468]
            
            # Left eye coordinates: inner 362, outer 263, iris center 473
            l_inner = landmarks[362]
            l_outer = landmarks[263]
            l_iris = landmarks[473]
            
            # Compute horizontal gaze ratios (0.0 = extreme right, 1.0 = extreme left)
            ratio_right = (r_iris.x - r_outer.x) / (r_inner.x - r_outer.x)
            ratio_left = (l_iris.x - l_inner.x) / (l_outer.x - l_inner.x)
            avg_ratio = (ratio_right + ratio_left) / 2.0
            
            # Classify based on thresholds
            if avg_ratio < threshold_right:
                gaze = "right"
                right_count += 1
            elif avg_ratio > threshold_left:
                gaze = "left"
                left_count += 1
            else:
                gaze = "center"
                center_count += 1
                
            out_lines.append(f"{frame_idx},{gaze},{avg_ratio:.4f}\n")
        else:
            noface_count += 1
            out_lines.append(f"{frame_idx},noface,-1.0000\n")
            
    cap.release()
    face_mesh.close()
    
    # Write annotations file
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
        
    return left_count, right_count, center_count, noface_count

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 process_videos_mediapipe.py <proliferate_responses.json> [output_dir]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "mediapipe_output"

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    # Load response data
    responses = []
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content.startswith('['):
                responses = json.loads(content)
            elif content.startswith('{'):
                responses = [json.loads(content)]
            else:
                for line in content.split('\n'):
                    if line.strip():
                        responses.append(json.loads(line))
    except Exception as e:
        print(f"Error loading response payload: {e}")
        sys.exit(1)

    print(f"Loaded {len(responses)} response(s) from '{input_path}'.")
    
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = "temp_mediapipe_processing"
    os.makedirs(temp_dir, exist_ok=True)
    
    summary_results = []
    
    for i, resp in enumerate(responses):
        pid = resp.get("participant_id")
        if not pid:
            pid = resp.get("results", {}).get("participant_id") or f"participant_{i+1}"
            
        test_order = resp.get("test_order") or resp.get("results", {}).get("test_order")
        videos = resp.get("videos") or resp.get("results", {}).get("videos") or []
        
        if not videos:
            print(f"No webcam videos found for participant '{pid}'. Skipping.")
            continue
            
        print(f"\nProcessing participant '{pid}' (test order: {test_order})...")
        
        for video in videos:
            trial_idx = video.get("trial_idx")
            mime_type = video.get("mime_type", "video/webm")
            base64_data = video.get("base64")
            
            if not base64_data:
                continue
                
            # Strip data URL header
            if "," in base64_data:
                base64_data = base64_data.split(",", 1)[1]
                
            video_bytes = base64.b64decode(base64_data)
            
            # Save raw webm
            webm_path = os.path.join(temp_dir, f"raw_{pid}_t{trial_idx}.webm")
            with open(webm_path, 'wb') as f:
                f.write(video_bytes)
                
            # Convert and crop using ffmpeg (slice to last 20 seconds, starting at 21.76s)
            mp4_path = os.path.join(temp_dir, f"crop_{pid}_t{trial_idx}.mp4")
            print(f"  Cropping trial {trial_idx} video stream to freeze frame...")
            
            cmd = [
                "ffmpeg", "-y", "-ss", "21.76", "-i", webm_path,
                "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                mp4_path
            ]
            
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except Exception as e:
                print(f"  Error converting video for trial {trial_idx}: {e}")
                continue
                
            # Construct output path
            condition = "unknown"
            if test_order and isinstance(test_order, list):
                try:
                    condition = test_order[trial_idx - 1]
                except IndexError:
                    pass
                    
            output_txt = os.path.join(output_dir, f"videoStream_adult_{pid}_{trial_idx}_{condition}.txt")
            
            # Execute MediaPipe gaze estimation
            left, right, center, noface = run_mediapipe_gaze(mp4_path, output_txt)
            total = left + right + center
            
            left_pct = (left / total * 100) if total > 0 else 0
            right_pct = (right / total * 100) if total > 0 else 0
            
            print(f"  Finished gaze analysis: Left={left} ({left_pct:.1f}%), Right={right} ({right_pct:.1f}%), Center={center}, NoFace={noface}")
            
            summary_results.append({
                "ParticipantID": pid,
                "TrialIndex": trial_idx,
                "Condition": condition,
                "Left Looking Frames": left,
                "Right Looking Frames": right,
                "Center Looking Frames": center,
                "NoFace Frames": noface,
                "Left Looking %": round(left_pct, 2),
                "Right Looking %": round(right_pct, 2),
                "Annotation File": output_txt
            })
            
    # Cleanup temp directory
    shutil.rmtree(temp_dir)
    
    # Save summary results
    if summary_results:
        summary_df = pd.DataFrame(summary_results)
        summary_csv = "mediapipe_summary_results.csv"
        summary_df.to_csv(summary_csv, index=False)
        print(f"\nSaved detailed summary to {summary_csv}")
        print("\n--- Summary Gaze Results ---")
        print(summary_df.to_string(index=False))
    else:
        print("\nNo participant data was processed.")

if __name__ == "__main__":
    main()
