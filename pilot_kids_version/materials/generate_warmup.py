import math
from moviepy import VideoClip, AudioFileClip
from PIL import Image, ImageDraw
import numpy as np

# Durations perfectly snapped
t0 = 2.15
t1 = 12.45
t2 = 17.30
t3 = 25.08

def make_frame(t):
    img = Image.new('RGB', (1280, 720), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    if t < t0:
        # Blank screen (white)
        pass
    elif (t >= t0 and t < t1) or (t >= t2 and t < t3):
        # Bullseye
        scale = 0.8 + 0.4 * (0.5 - 0.5 * math.cos(t * 2 * math.pi))
        cx, cy = 640, 360
        base_radii = [150, 116, 83, 50, 16]
        colors = ['#000000', '#ffffff', '#000000', '#ffffff', '#000000']
        for r, c in zip(base_radii, colors):
            r_scaled = r * scale
            draw.ellipse([cx - r_scaled, cy - r_scaled, cx + r_scaled, cy + r_scaled], fill=c)
    elif t >= t1 and t < t2:
        # Left Object (Yellow bouncing circle)
        cx = 320
        cy = 360 - 50 * abs(math.sin(t * 2 * math.pi))
        r = 80
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#f1c40f')
    else:
        # Right Object (Green bouncing square)
        cx = 960
        cy = 360 - 50 * abs(math.sin(t * 2 * math.pi))
        r = 80
        draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill='#2ecc71')
        
    return np.array(img)

audio = AudioFileClip('warmup_practice_audio.m4a')
video = VideoClip(make_frame, duration=audio.duration)
video = video.with_audio(audio)
video.write_videofile('warmup_practice.mp4', fps=30, codec='libx264', audio_codec='aac')
