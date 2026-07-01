// ── CONFIG & BASE MATERIAL PATHS ──
const BASE = 'https://raw.githubusercontent.com/SunnyZ-cs/non_verbal_adults/main/pilot_kids_version/materials/';

// ── TESTING MODE CONFIG ──
const urlParams = new URLSearchParams(window.location.search);
const is_testing = urlParams.has('test');

// ── RANDOMIZATION ──
const fam_combo_index = Math.floor(Math.random() * 8) + 1; // Random 1-8
const fam_combo_url = BASE + `Fam_Combo_${fam_combo_index}.gif`;
const fam_freeze_url = BASE + `Fam_Combo_${fam_combo_index}_freeze.png`;

const fam_durations = {
    1: 120960, 2: 118480, 3: 118480, 4: 120960,
    5: 120960, 6: 118480, 7: 118480, 8: 120960
};
const fam_duration = is_testing ? 1000 : fam_durations[fam_combo_index];
const fam_freeze_duration = is_testing ? 500 : 4000; // 4 seconds freeze for fam trials

// Test Trials Details
const distal_anim = BASE + 'distal_test_final.gif';
const distal_freeze = BASE + 'distal_test_final_freeze.png';
const proximal_anim = BASE + 'proximal_test_final.gif';
const proximal_freeze = BASE + 'proximal_test_final_freeze.png';

const test_anim_duration = is_testing ? 1000 : 18760;
const freeze_duration = is_testing ? 1000 : 20000; // 20 seconds freeze for test trials

// Randomize Test Order
const test_order = Math.random() < 0.5 ? ['distal', 'proximal'] : ['proximal', 'distal'];

// Generate unique participant ID using timestamp and random number
const participant_id = `P${Date.now()}_${Math.floor(Math.random() * 100000)}`;

// ── INIT jsPsych ──
const jsPsych = initJsPsych({
    show_progress_bar: true,
    override_safe_mode: true,
    on_finish: function() {
        const data = jsPsych.data.get();
        
        // Extract demographics
        const survey = data.filter({page_type: 'participant_survey'}).values()[0]?.response || {};
        let gender = survey.gender;
        if (!gender && survey.other_gender_text) {
            gender = survey.other_gender_text;
        }
        let race = survey.race;
        if (!race && survey.other_race_text) {
            race = survey.other_race_text;
        }
        
        const demographics = {
            "age": parseInt(survey.age) || null,
            "gender": gender || null,
            "race": race || null,
            "ethnicity": survey.ethnicity || null
        };
        
        // Extract feedback
        const feedback = data.filter({page_type: 'final_feedback'}).values()[0]?.response?.feedback || "";

        // Extract webcam videos
        const videos = [];
        data.filter({page_type: 'webcam_video'}).values().forEach(v => {
            videos.push({
                trial_idx: v.trial_idx,
                mime_type: v.mime_type,
                base64: v.video_base64
            });
        });

        // Compile final payload
        const final_data = {
            "participant_id": participant_id,
            "fam_combo": fam_combo_index,
            "test_order": test_order,
            "demographics": demographics,
            "feedback": feedback,
            "videos": videos // Contains Base64 video strings for offline extraction
        };

        console.log("Submitting final data:", final_data);
        proliferate.submit(final_data);

        // Terminate webcam stream
        if (webcamStream) {
            webcamStream.getTracks().forEach(track => track.stop());
        }

        // Show redirecting layout
        document.body.innerHTML = `
            <div style="margin: 100px auto; text-align: center; font-family: Arial, sans-serif; max-width: 600px;">
                <h3>Thank you for participating!</h3>
                <p>Your responses and webcam data have been successfully saved.</p>
                <p>Redirecting you back to Prolific...</p>
            </div>
        `;
    }
});

// ── TIMELINE CONSTRUCTOR ──
const timeline = [];

// Preload Images & Animations
const images_to_preload = [
    fam_combo_url,
    fam_freeze_url,
    distal_anim,
    distal_freeze,
    proximal_anim,
    proximal_freeze
];
timeline.push({
    type: jsPsychPreload,
    auto_preload: true,
    images: images_to_preload
});

// Fullscreen start
timeline.push({
    type: jsPsychFullscreen,
    fullscreen_mode: true
});

// Consent & Instructions
timeline.push(consent);
timeline.push(instructions);

// Webcam Permission & Calibration Preview
timeline.push(webcam_setup);

// Randomization info trial (saves condition variables to jsPsych data)
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: '',
    choices: [],
    trial_duration: 0,
    data: {
        page_type: 'randomization_info',
        fam_combo: fam_combo_index,
        test_order: test_order
    }
});

// Familiarization instructions
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; text-align: center; line-height: 1.6;">
            <h3>Introduction</h3>
            <p>You will now watch a clip where some shapes interact. Please look at the screen and watch them carefully.</p>
        </div>
    `,
    choices: ['Start ▶']
});

// Familiarization Animation Trial
const fam_trial = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `<img id="fam-visual" src="${fam_combo_url}" class="trial-visual">`,
    choices: "NO_KEYS",
    trial_duration: fam_duration + fam_freeze_duration,
    on_load: function() {
        // Preload the freeze image
        const img = new Image();
        img.src = fam_freeze_url;
        
        // Swap GIF to freeze image once animated sequence concludes
        setTimeout(function() {
            const el = document.getElementById('fam-visual');
            if (el) el.src = fam_freeze_url;
        }, fam_duration);
    },
    data: { page_type: 'familiarization', combo_used: fam_combo_index }
};
timeline.push(fam_trial);

// Transition to test trials instructions
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; text-align: center; line-height: 1.6;">
            <h3>First Part Complete</h3>
            <p>Great! You've finished the first part of the study.</p>
            <p>Next, you will watch two short clips. Before each clip, a pulsing target will appear. Please look directly at the center of the target.</p>
            <p><strong>Note:</strong> Webcam recording will run during the clips to capture your gaze.</p>
        </div>
    `,
    choices: ['Continue ▶']
});

// Build Test Timeline for a specific condition
function buildTestTimeline(test_name, trial_idx) {
    const trials = [];
    
    const anim_url = test_name === 'distal' ? distal_anim : proximal_anim;
    const freeze_url = test_name === 'distal' ? distal_freeze : proximal_freeze;
    
    // 1. Start webcam recording
    trials.push({
        type: jsPsychCallFunction,
        func: function() {
            if (!webcamStream) {
                console.warn("No active webcam stream. Recording skipped.");
                return;
            }
            recordedChunks = [];
            
            let mimeType = 'video/webm;codecs=vp8';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'video/webm';
            }
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'video/mp4';
            }
            
            const options = { 
                mimeType: mimeType, 
                videoBitsPerSecond: 150000 
            };
            
            try {
                mediaRecorder = new MediaRecorder(webcamStream, options);
                mediaRecorder.ondataavailable = function(event) {
                    if (event.data && event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                mediaRecorder.start(1000); // Record chunks of 1 second
                console.log("Webcam recording started for trial " + trial_idx);
            } catch (e) {
                console.error("Could not start MediaRecorder:", e);
            }
        }
    });

    // 2. Refixation bullseye (3 seconds)
    trials.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `
        <div style="display:flex; justify-content:center; align-items:center; height:70vh;">
            <svg width="200" height="200" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
              <style>
                @keyframes pulse-svg {
                  0% { transform: scale(0.8); opacity: 0.8; }
                  50% { transform: scale(1.1); opacity: 1; }
                  100% { transform: scale(0.8); opacity: 0.8; }
                }
                .bullseye-group {
                  animation: pulse-svg 1s infinite ease-in-out;
                  transform-origin: center;
                }
              </style>
              <g class="bullseye-group">
                <circle cx="100" cy="100" r="90" fill="#000000"/>
                <circle cx="100" cy="100" r="70" fill="#ffffff"/>
                <circle cx="100" cy="100" r="50" fill="#000000"/>
                <circle cx="100" cy="100" r="30" fill="#ffffff"/>
                <circle cx="100" cy="100" r="10" fill="#000000"/>
              </g>
            </svg>
        </div>`,
        choices: "NO_KEYS",
        trial_duration: 3000,
        data: { page_type: test_name + '_bullseye' }
    });

    // 3. Play animation (18.76s) and freeze (20s) in a single trial
    trials.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<img id="test-visual" src="${anim_url}" class="trial-visual">`,
        choices: "NO_KEYS",
        trial_duration: test_anim_duration + freeze_duration,
        on_load: function() {
            const img = new Image();
            img.src = freeze_url;
            
            // Swap animation to static freeze frame perfectly at end of sequence
            setTimeout(function() {
                const el = document.getElementById('test-visual');
                if (el) el.src = freeze_url;
            }, test_anim_duration);
        },
        data: { page_type: test_name + '_full_test' }
    });
    
    // 4. Stop webcam recording and save Base64 file
    trials.push({
        type: jsPsychCallFunction,
        async: true,
        func: function(done) {
            console.log("stop_recording called for trial " + trial_idx + ", type of done is: " + typeof done);
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
                            trial_idx: trial_idx,
                            video_base64: base64Data,
                            mime_type: mimeType
                        });
                        
                        console.log(`Video ${trial_idx} successfully recorded and saved (${blob.size} bytes).`);
                        done();
                    }
                };
            };
            
            mediaRecorder.stop();
        }
    });

    return trials;
}

// Add Test Trial 1
timeline.push(...buildTestTimeline(test_order[0], 1));

// Brief transition between test trials
timeline.push({
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; text-align: center; line-height: 1.6;">
            <h3>First Clip Finished</h3>
            <p>Click the button below when you are ready to continue to the second clip.</p>
        </div>
    `,
    choices: ['Ready ▶'],
    on_finish: function() {
        console.log("Ready button trial finished successfully!");
    }
});

// Add Test Trial 2
timeline.push(...buildTestTimeline(test_order[1], 2));

// Exit Fullscreen
timeline.push({
    type: jsPsychFullscreen,
    fullscreen_mode: false
});

// Final study feedback
timeline.push({
    type: jsPsychSurveyText,
    questions: [{ 
        prompt: "Did anything about the animations or the experiment seem unclear or confusing? (Optional)", 
        name: 'feedback', 
        rows: 5 
    }],
    data: { page_type: 'final_feedback' }
});

// Demographic Form
timeline.push(demographic_form);

// Execute timeline
jsPsych.run(timeline);
