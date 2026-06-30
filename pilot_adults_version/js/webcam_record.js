// Global variables to manage webcam stream and recording
let webcamStream = null;
let mediaRecorder = null;
let recordedChunks = [];
let videoIndex = 1;

// Webcam alignment/setup trial
const webcam_setup = {
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; text-align: center;">
            <h2 style="color: #2C3E50;">Webcam Calibration</h2>
            <p>Please grant webcam permissions when prompted. Align your face so that it is in the center of the box below before clicking Continue.</p>
            
            <div style="width: 320px; height: 240px; margin: 25px auto; border: 3px solid #34495E; border-radius: 8px; background: #34495E; position: relative; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
                <!-- Live webcam preview -->
                <video id="webcam-preview" width="320" height="240" autoplay muted playsinline style="transform: scaleX(-1); object-fit: cover; width: 100%; height: 100%;"></video>
                
                <!-- Alignment Target Overlay -->
                <div style="position: absolute; top: 15%; left: 15%; width: 70%; height: 70%; border: 2px dashed #E74C3C; border-radius: 50%; box-sizing: border-box; pointer-events: none;">
                    <div style="position: absolute; top: calc(50% - 10px); left: calc(50% - 10px); width: 20px; height: 20px; border: 2px solid #E74C3C; border-radius: 50%;"></div>
                </div>
            </div>
            <p style="font-size: 0.95em; color: #7F8C8D;">Your face should be centered inside the red dashed circle.</p>
        </div>
    `,
    choices: ['Continue'],
    on_load: function() {
        const btn = document.querySelector('.jspsych-btn');
        if (btn) btn.disabled = true;

        navigator.mediaDevices.getUserMedia({
            video: {
                width: { max: 640, ideal: 320 },
                height: { max: 480, ideal: 240 },
                frameRate: { max: 15, ideal: 15 }
            },
            audio: false
        })
        .then(function(stream) {
            webcamStream = stream;
            const video = document.getElementById('webcam-preview');
            if (video) {
                video.srcObject = stream;
            }
            if (btn) btn.disabled = false;
            console.log("Webcam stream initialized successfully.");
        })
        .catch(function(err) {
            console.error("Failed to access camera:", err);
            alert("This study requires camera access. Please reload the page, ensure no other application is using your camera, and grant permissions.");
        });
    }
};

// Trial to start MediaRecorder
const start_recording = {
    type: jsPsychCallFunction,
    func: function() {
        if (!webcamStream) {
            console.warn("No active webcam stream. Recording skipped.");
            return;
        }
        recordedChunks = [];
        
        // Select standard codec options (VP8 is highly compatible with iCatcher/FFmpeg)
        let mimeType = 'video/webm;codecs=vp8';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/webm';
        }
        if (!MediaRecorder.isTypeSupported(mimeType)) {
            mimeType = 'video/mp4';
        }
        
        const options = { 
            mimeType: mimeType, 
            videoBitsPerSecond: 150000 // 150 Kbps targets ultra-low bandwidth suitable for web uploads
        };
        
        try {
            mediaRecorder = new MediaRecorder(webcamStream, options);
            mediaRecorder.ondataavailable = function(event) {
                if (event.data && event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };
            mediaRecorder.start(1000); // Record chunks of 1 second
            console.log("Webcam recording started.");
        } catch (e) {
            console.error("Could not start MediaRecorder:", e);
        }
    }
};

// Trial to stop MediaRecorder and save the video as a Base64 string in jsPsych data
const stop_recording = {
    type: jsPsychCallFunction,
    async: true,
    func: function(done) {
        if (!mediaRecorder || mediaRecorder.state === "inactive") {
            console.warn("MediaRecorder is not active.");
            done();
            return;
        }
        
        let finished = false;
        
        // Safety fallback timeout to prevent experiment from freezing if onstop hangs
        const timeoutId = setTimeout(function() {
            if (!finished) {
                finished = true;
                console.warn("Safety timeout reached while saving video. Advancing trial.");
                done();
            }
        }, 10000);
        
        mediaRecorder.onstop = function() {
            const mimeType = mediaRecorder.mimeType || 'video/webm';
            const blob = new Blob(recordedChunks, { type: mimeType });
            
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = function() {
                if (!finished) {
                    finished = true;
                    clearTimeout(timeoutId);
                    
                    const base64Data = reader.result; // Data URL format (base64)
                    
                    // Write base64 video stream data to jsPsych data store
                    jsPsych.data.write({
                        page_type: 'webcam_video',
                        trial_idx: videoIndex,
                        video_base64: base64Data,
                        mime_type: mimeType
                    });
                    
                    console.log(`Video ${videoIndex} successfully recorded and saved (${blob.size} bytes).`);
                    videoIndex++;
                    done();
                }
            };
        };
        
        mediaRecorder.stop();
    }
};
