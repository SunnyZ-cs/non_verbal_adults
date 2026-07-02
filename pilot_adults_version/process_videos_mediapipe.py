#!/usr/bin/env python3
import os
import sys
import json
import base64
import subprocess
import shutil
import argparse
import pandas as pd
import numpy as np
import cv2

try:
    import mediapipe as mp
except ImportError:
    print("Error: MediaPipe is not installed. Please run: pip install mediapipe")
    sys.exit(1)

def run_mediapipe_gaze(video_path, output_txt_path, sensitivity_offset=0.012):
    """
    Executes gaze tracking using MediaPipe Face Mesh iris landmarks on a video clip.
    Saves frame-by-frame annotations to output_txt_path.
    """
    # 1. First pass to calculate baseline mean_ratio for this specific clip
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
    
    ratios = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            ratio_right = (landmarks[468].x - landmarks[33].x) / (landmarks[133].x - landmarks[33].x)
            ratio_left = (landmarks[473].x - landmarks[362].x) / (landmarks[263].x - landmarks[362].x)
            avg_ratio = (ratio_right + ratio_left) / 2.0
            ratios.append(avg_ratio)
    cap.release()
    
    if not ratios:
        print(f"  Warning: No faces detected in '{video_path}'")
        face_mesh.close()
        return 0, 0, 0, 300
        
    mean_ratio = np.mean(ratios)
    print(f"  Baseline calibrated: mean_ratio = {mean_ratio:.4f}, sensitivity_offset = {sensitivity_offset:.4f}")
    
    # 2. Second pass to annotate and count
    cap = cv2.VideoCapture(video_path)
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
            ratio_right = (landmarks[468].x - landmarks[33].x) / (landmarks[133].x - landmarks[33].x)
            ratio_left = (landmarks[473].x - landmarks[362].x) / (landmarks[263].x - landmarks[362].x)
            avg_ratio = (ratio_right + ratio_left) / 2.0
            
            # Classify gaze relative to the participant's dynamic mean
            if avg_ratio < mean_ratio - sensitivity_offset:
                gaze = "right"
                right_count += 1
            elif avg_ratio > mean_ratio + sensitivity_offset:
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
    parser = argparse.ArgumentParser(description="MediaPipe Adult Gaze Estimation (Dynamic Calibration)")
    parser.add_argument("responses_json", help="Path to Proliferate response JSON file")
    parser.add_argument("output_dir", nargs="?", default="mediapipe_output", help="Output folder")
    parser.add_argument("-s", "--sensitivity", type=float, default=0.012, help="Gaze sensitivity offset (default: 0.012)")
    parser.add_argument("-t", "--test-order-csv", help="Path to Proliferate test order CSV file")
    
    args = parser.parse_args()
    
    input_path = args.responses_json
    output_dir = args.output_dir
    sensitivity_offset = args.sensitivity
    test_order_csv = args.test_order_csv

    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.")
        sys.exit(1)

    # Load test order map if provided
    test_order_map = {}
    if test_order_csv:
        if os.path.exists(test_order_csv):
            try:
                to_df = pd.read_csv(test_order_csv)
                # Group by workerid and convert test_order column values to list
                for pid, group in to_df.groupby('workerid'):
                    test_order_map[str(pid)] = [str(x).strip() for x in group['test_order'].tolist() if pd.notna(x)]
                print(f"Loaded test orders for {len(test_order_map)} participant(s) from '{test_order_csv}'.")
            except Exception as e:
                print(f"Error reading test order CSV: {e}")
        else:
            print(f"Warning: Test order CSV '{test_order_csv}' not found.")

    # Load response data
    responses = []
    if input_path.lower().endswith('.csv'):
        try:
            df = pd.read_csv(input_path)
            # Group by workerid to form responses structured similarly to the JSON
            grouped = df.groupby('workerid')
            for pid, group in grouped:
                videos = []
                pid_str = str(pid)
                # Retrieve test order from test_order_map or default to the CSV columns
                if pid_str in test_order_map:
                    test_order = test_order_map[pid_str]
                else:
                    test_order = []
                    for _, row in group.iterrows():
                        cond = row.get('proliferate.condition', 'unknown')
                        test_order.append(str(cond))
                
                for _, row in group.iterrows():
                    videos.append({
                        'trial_idx': int(row['trial_idx']),
                        'mime_type': row.get('mime_type', 'video/webm'),
                        'base64': row['base64']
                    })
                
                responses.append({
                    'participant_id': pid_str,
                    'test_order': test_order,
                    'videos': videos
                })
            print(f"Loaded {len(responses)} participant(s) from CSV '{input_path}'.")
        except Exception as e:
            print(f"Error loading response CSV: {e}")
            sys.exit(1)
    else:
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
            
            # Override test order from map if provided
            if test_order_map:
                for resp in responses:
                    pid = resp.get("participant_id")
                    if not pid:
                        pid = resp.get("results", {}).get("participant_id")
                    if pid and str(pid) in test_order_map:
                        resp["test_order"] = test_order_map[str(pid)]
                        
            print(f"Loaded {len(responses)} response(s) from JSON '{input_path}'.")
        except Exception as e:
            print(f"Error loading response JSON payload: {e}")
            sys.exit(1)
    
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
            
            # Execute MediaPipe gaze estimation with sensitivity offset
            left, right, center, noface = run_mediapipe_gaze(mp4_path, output_txt, sensitivity_offset)
            total = left + right + center
            
            left_pct = (left / total * 100) if total > 0 else 0
            right_pct = (right / total * 100) if total > 0 else 0
            
            print(f"  Finished gaze analysis: Left={left} ({left_pct:.1f}%), Right={right} ({right_pct:.1f}%), Center={center}, NoFace={noface}")
            
            summary_results.append({
                "ParticipantID": pid,
                "TrialIndex": trial_idx,
                "TrialType": condition,
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
