// ════════════════════════════════════════════════════════════════════
//  NON-VERBAL ADULTS SINGLE CAUSE — CHS jsPsych version
//
//  Paste the contents of this file directly into the
//  "jsPsych Experiment Code" editor on childrenhelpingscience.com.
//
//  CHS automatically loads all standard jsPsych v8 plugins and these
//  custom packages:
//    chsRecord  — VideoConfigPlugin, VideoConsentPlugin,
//                 StartRecordPlugin, StopRecordPlugin, TrialRecordExtension
//    chsSurvey  — ExitSurveyPlugin
// ════════════════════════════════════════════════════════════════════


// ── Inject CSS (CHS provides the HTML page; we inject styles at runtime) ──
const _style = document.createElement('style');
_style.textContent = `
    .jspsych-content-wrapper {
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
    }
    .jspsych-content {
        max-width: 98% !important;
        width: 98% !important;
        margin: 0 auto !important;
    }

    /* All full-screen videos and gifs */
    .trial-visual {
        display: block;
        width: 100%;
        max-height:70vh;
        margin: 0 auto;
        object-fit: contain;
    }

    /* Instructions */
    .instructions-box {
        max-width: 680px;
        margin: 30px auto;
        font-size: 1.1em;
        line-height: 1.7;
        text-align: left;
    }
    .instructions-box h2 { margin-bottom: 10px; }
    .instructions-box ul  { padding-left: 1.4em; }

    /* Continue button: larger, fixed to bottom-right corner */
    .continue-btn-group {
        position: fixed !important;
        bottom: 24px !important;
        right: 28px !important;
        margin: 0 !important;
        justify-content: flex-end !important;
        z-index: 9999 !important;
    }
    .continue-btn-group .jspsych-btn {
        font-size: 1.3em !important;
        padding: 14px 44px !important;
    }
`;
document.head.appendChild(_style);

// ════════════════════════════════════════════════════════════════════
//  CONFIG
// ════════════════════════════════════════════════════════════════════

const BASE = 'https://raw.githubusercontent.com/SunnyZ-cs/non_verbal_adults/main/non_verbal_single_cause/materials/';

// ════════════════════════════════════════════════════════════════════
//  SCENARIOS & RANDOMIZATION
// ════════════════════════════════════════════════════════════════════

const fam_combo_index = Math.floor(Math.random() * 8) + 1; // Random 1-8
const fam_combo_url = BASE + `Fam_Combo_${fam_combo_index}.gif`;
const fam_freeze_url = BASE + `Fam_Combo_${fam_combo_index}_freeze.png`;

const fam_durations = {
    1: 120960, 2: 118480, 3: 118480, 4: 120960,
    5: 120960, 6: 118480, 7: 118480, 8: 120960
};
const fam_duration = fam_durations[fam_combo_index];
const fam_freeze_duration = 4000; // 4 seconds freeze for fam trials

// Test Trials Details
const distal_anim = BASE + 'distal_test_final.gif';
const distal_freeze = BASE + 'distal_test_final_freeze.png';

const proximal_anim = BASE + 'proximal_test_final.gif';
const proximal_freeze = BASE + 'proximal_test_final_freeze.png';

const test_anim_duration = 18760;
const freeze_duration = 20000; // 20 seconds

// Randomize Test Order
const test_order = Math.random() < 0.5 ? 
    [{name: 'distal', anim: distal_anim, freeze: distal_freeze}, {name: 'proximal', anim: proximal_anim, freeze: proximal_freeze}] :
    [{name: 'proximal', anim: proximal_anim, freeze: proximal_freeze}, {name: 'distal', anim: distal_anim, freeze: distal_freeze}];

// ════════════════════════════════════════════════════════════════════
//  INIT jsPsych
// ════════════════════════════════════════════════════════════════════

const jsPsych = initJsPsych();

// ════════════════════════════════════════════════════════════════════
//  CHS-SPECIFIC FRAMES
// ════════════════════════════════════════════════════════════════════

const video_config = {
    type: chsRecord.VideoConfigPlugin
};

const video_consent = {
    type: chsRecord.VideoConsentPlugin,
    PIName:      'Ellen Markman',
    institution: 'The Markman Lab of Stanford University',
    PIContact:   'Ellen Markman at markman@stanford.edu',
    purpose:     'This study is about how children perceive causal chains and responsibility.',
    procedures:  'Your child will watch short animated sequences. We will record their eye movements to measure their looking times.',
    risk_statement: 'There are no expected risks to participation.',
    payment:     'After you finish the study, we will email you a $5 Amazon gift card within approximately 3–5 business days.',
    research_rights_statement: 'This research has been reviewed and approved by an Institutional Review Board (“IRB”), a group of people who oversee research involving humans as participants. Information to help you understand research is on-line at https://irb.stanford.edu/. You may talk to a IRB staff member at (650) 723-2480 or irb2-manager@lists.stanford.edu for any of the following: 1) Your questions, concerns, or complaints are not being answered by the research team; 2) you cannot reach the research team; 3) you want to talk to someone besides the research team; 4) you have questions about your rights as a research subject; 5) you want to get information or provide input about this research.',
    include_databrary: true
};

const instructions = {
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <div class="instructions-box">
            <h2>Overview</h2>
            <ul>
                <li>The study takes about 5–10 minutes.</li>
                <li>Your child will watch short animated clips.</li>
                <li><strong>IMPORTANT:</strong> Please position your child's head so that they face the center of the screen directly.</li>
            </ul>
            <p><strong>For parents:</strong> Please help keep your child's attention on the screen.</p>
        </div>`,
    choices: ['Start ▶'],
    data: { trial_type: 'instructions' }
};

const start_recording = { type: chsRecord.StartRecordPlugin };
const stop_recording  = { type: chsRecord.StopRecordPlugin  };

// ════════════════════════════════════════════════════════════════════
//  TRIAL BUILDERS
// ════════════════════════════════════════════════════════════════════

// Familiarization Animation (Play GIF once then freeze). 
const fam_trial = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `<img id="fam-visual" src="${fam_combo_url}" class="trial-visual">`,
    choices: "NO_KEYS",
    trial_duration: fam_duration + fam_freeze_duration,
    on_load: function() {
        const img = new Image();
        img.src = fam_freeze_url;
        
        setTimeout(function() {
            const el = document.getElementById('fam-visual');
            if (el) el.src = fam_freeze_url;
        }, fam_duration);
    },
    data: { trial_type: 'familiarization', combo_used: fam_combo_index }
};

// Helper function to build video trials that auto-advance
function buildVideoTrial(filename, trial_name) {
    return {
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<video id="${trial_name}-vid" class="trial-visual" autoplay><source src="${BASE}${filename}" type="video/mp4"></video>`,
        choices: "NO_KEYS",
        on_load: function() {
            const vid = document.getElementById(`${trial_name}-vid`);
            if (vid) {
                vid.onended = function() { jsPsych.finishTrial(); };
                vid.onerror = function() { jsPsych.finishTrial(); };
            } else { 
                setTimeout(jsPsych.finishTrial, 5000); 
            }
        },
        data: { trial_type: trial_name }
    };
}

// Helper function to build video trials that require a 'Next' button click
function buildVideoTrialWithNext(filename, trial_name) {
    return {
        type: jsPsychHtmlButtonResponse,
        stimulus: `<video id="${trial_name}-vid" class="trial-visual" src="${BASE}${filename}" autoplay playsinline></video>`,
        choices: ['Next'],
        on_load: function() {
            const group = document.getElementById('jspsych-html-button-response-btngroup');
            if (group) group.classList.add('continue-btn-group');
            const btn = group && group.querySelector('button');
            if (btn) {
                // Wait for video to finish before allowing the user to proceed
                btn.disabled = true;
                const vid = document.getElementById(`${trial_name}-vid`);
                if (vid) {
                    vid.addEventListener('ended', () => { btn.disabled = false; });
                    vid.addEventListener('error', () => { btn.disabled = false; }); // Fallback
                }
            }
        },
        data: { trial_type: trial_name }
    };
}

const intro_video = buildVideoTrialWithNext('overall_study_intro.mp4', 'overall_study_intro');
const warmup_practice = buildVideoTrial('warmup_practice.mp4', 'warmup_practice');
const warmup_finish = buildVideoTrialWithNext('warmup_finish.mp4', 'warmup_finish');
const outro_video = buildVideoTrial('overall_study_end.mp4', 'overall_study_end');

// Build Test Timeline for a specific test block
function buildTestTimeline(testObj) {
    const trials = [];
    
    // 0. Start webcam recording FIRST. 
    // This plugin takes ~1 second to initialize and shows a blue spinner. 
    // Placing it here ensures the spinner happens BEFORE the animation,
    // so the transition from animation to freeze is perfectly seamless!
    trials.push(start_recording);

    // 0.5. Pulsing Bullseye to refixate gaze (1 second)
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
        data: { trial_type: testObj.name + '_bullseye' }
    });

    // 1. Play the animation AND the freeze in a single trial to completely eliminate screen flashing.
    trials.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<img id="test-visual" src="${testObj.anim}" class="trial-visual">`,
        choices: "NO_KEYS",
        trial_duration: test_anim_duration + freeze_duration,
        on_load: function() {
            // Preload the freeze image immediately to ensure zero delay
            const img = new Image();
            img.src = testObj.freeze;
            
            // Swap the GIF to the static PNG exactly when the animation finishes its loop
            setTimeout(function() {
                const el = document.getElementById('test-visual');
                if (el) el.src = testObj.freeze;
            }, test_anim_duration);
        },
        data: { trial_type: testObj.name + '_full_test' }
    });
    
    // 2. Stop webcam recording
    trials.push(stop_recording);

    return trials;
}

// ════════════════════════════════════════════════════════════════════
//  RUN THE EXPERIMENT
// ════════════════════════════════════════════════════════════════════

const debrief_page = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `
        <div class="instructions-box" style="max-width: 800px; margin: 40px auto; text-align: left; line-height: 1.7; font-family: Arial, sans-serif;">
            <h1 style="text-align: center; margin-bottom: 30px; font-size: 2.2em; font-weight: normal; color: #333;">Thank you!</h1>
            
            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;">This study is a follow-up to our previous research examining how children trace fault and responsibility. In contrast to our previous studies with two causes in a chain (where a distal cause hits a proximal cause, which in turn hits the object), this study examines a single-cause scenario where there is only one active agent (the proximal cause) that directly causes the cube to break, while the other agent (the distal cause) remains inactive.</p>
            
            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;">In our previous studies, we examined children's judgments about causal responsibility in situations with multiple agents operating in chains. For example, Andy hits Suzy with his bike, Suzy falls into the fence, and the fence breaks. We found that younger children tend to focus on the direct, proximal cause (the agent that physically contacts the object), while older children can trace responsibility back to the initial, distal cause (the agent that started the chain reaction).</p>
            
            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;">With this new study, we are using a non-verbal eye-tracking design in a single-cause baseline context. By measuring where children look on the screen while watching shapes interact, we are testing how children evaluate attention and responsibility when an agent is physically present but causally uninvolved (the distal cause does nothing, while only the proximal cause hits the cube).</p>
            
            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;"><strong>How this study answers the question:</strong> We record where your child looks during the final moments of the videos. By observing whether children look longer or more frequently at the active proximal cause (the agent that directly broke the cube) or the inactive distal cause, and comparing this to the looking patterns from our chain-event studies, we can understand how children evaluate responsibility and blame when only one agent is causally responsible.</p>
            
            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;"><strong>A note on child behavior:</strong> Please note that there are many reasons a child might look more or less at a particular shape on any given trial (such as a preference for a certain color or shape, or simply looking around), and that is completely normal and okay! That is why we average looking times over many children to find general patterns rather than looking at individual responses.</p>
            
            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;"><strong>Compensation:</strong> As a reminder, you will receive a $5 Amazon.com gift card via email within approximately a week of completing the study.</p>
            
            <p style="margin-bottom: 2em; font-size: 1.05em; color: #444;">If you are interested in learning more about this topic, please visit our lab website: <a href="https://markmanlab.stanford.edu" target="_blank" style="color: #337ab7; text-decoration: none;">markmanlab.stanford.edu</a>, or check out this paper: 
            <a href="https://davdrose.github.io/assets/pdf/cause_fault_cog_sci.pdf" target="_blank" style="color: #337ab7; text-decoration: none;">https://davdrose.github.io/assets/pdf/cause_fault_cog_sci.pdf</a>. Thank you again for your participation!</p>
            
            <div style="text-align: center; margin-top: 30px; margin-bottom: 20px;">
                <button id="fb-share-btn" class="jspsych-btn" style="background-color: #3b5998; color: white; border: none; padding: 12px 24px; font-size: 1.1em; border-radius: 4px; cursor: pointer; margin-right: 15px; font-weight: bold;">Share this study on Facebook!</button>
                <button id="exit-btn" class="jspsych-btn" style="background-color: #5cb85c; color: white; border: none; padding: 12px 24px; font-size: 1.1em; border-radius: 4px; cursor: pointer; font-weight: bold;">Exit</button>
            </div>
        </div>
    `,
    choices: "NO_KEYS",
    on_load: function() {
        const fbBtn = document.getElementById('fb-share-btn');
        if (fbBtn) {
            fbBtn.addEventListener('click', function() {
                const studyUrl = window.location.href;
                const fbShareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(studyUrl)}`;
                window.open(fbShareUrl, '_blank');
            });
        }
        const exitBtn = document.getElementById('exit-btn');
        if (exitBtn) {
            exitBtn.addEventListener('click', function() {
                window.location.href = "https://childrenhelpingscience.com/studies/history/";
            });
        }
    },
    data: { trial_type: 'debrief' }
};

jsPsych.run([
    // ── Setup ──
    { type: jsPsychFullscreen, fullscreen_mode: true },
    video_config,
    video_consent,
    instructions,

    // ── Intro Sequence ──
    intro_video,
    warmup_practice,
    warmup_finish,

    // ── Record randomizations ──
    {
        type: jsPsychHtmlButtonResponse,
        stimulus: '',
        choices: [],
        trial_duration: 0,
        data: {
            trial_type: 'randomization_info',
            fam_combo: fam_combo_index,
            test_order: [test_order[0].name, test_order[1].name]
        }
    },

    // ── Familiarization Phase ──
    fam_trial,

    // ── Test Phase 1 ──
    ...buildTestTimeline(test_order[0]),

    // ── Test Phase 2 ──
    ...buildTestTimeline(test_order[1]),

    // ── Outro Sequence ──
    outro_video,

    // ── End ──
    { type: jsPsychFullscreen, fullscreen_mode: false, delay_after: 0 },
    { type: chsSurvey.ExitSurveyPlugin },
    debrief_page
]);
