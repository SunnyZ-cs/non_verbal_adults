// ════════════════════════════════════════════════════════════════════
//  NON-VERBAL ADULTS PILOT KIDS VERSION — CHS jsPsych version
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
`;
document.head.appendChild(_style);

// ════════════════════════════════════════════════════════════════════
//  CONFIG
// ════════════════════════════════════════════════════════════════════

const BASE = 'https://raw.githubusercontent.com/SunnyZ-cs/non_verbal_adults/main/pilot_kids_version/materials/';

// ════════════════════════════════════════════════════════════════════
//  SCENARIOS & RANDOMIZATION
// ════════════════════════════════════════════════════════════════════

const fam_combo_index = Math.floor(Math.random() * 8) + 1; // Random 1-8
const fam_combo_url = BASE + `Fam_Combo_${fam_combo_index}.gif`;

const fam_durations = {
    1: 120960, 2: 118480, 3: 118480, 4: 120960,
    5: 120960, 6: 118480, 7: 118480, 8: 120960
};
const fam_duration = fam_durations[fam_combo_index];

// Test Trials Details
const distal_anim = BASE + 'distal_test_final.gif';
const distal_freeze = BASE + 'distal_test_final_freeze.png';

const proximal_anim = BASE + 'proximal_test_final.gif';
const proximal_freeze = BASE + 'proximal_test_final_freeze.png';

const test_anim_duration = 18760;

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

// Familiarization Animation (Play GIF once). Wait time based on precise GIF length.
const fam_trial = {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `<img src="${fam_combo_url}" class="trial-visual">`,
    choices: "NO_KEYS",
    trial_duration: fam_duration,
    data: { trial_type: 'familiarization', combo_used: fam_combo_index }
};

// Build Test Timeline for a specific test block
function buildTestTimeline(testObj) {
    const trials = [];
    
    // 0. Start webcam recording FIRST. 
    // This plugin takes ~1 second to initialize and shows a blue spinner. 
    // Placing it here ensures the spinner happens BEFORE the animation,
    // so the transition from animation to freeze is perfectly seamless!
    trials.push(start_recording);

    // 1. Play the animation part of the test (GIF).
    // The trial naturally ends exactly when the GIF completes.
    trials.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<img src="${testObj.anim}" class="trial-visual">`,
        choices: "NO_KEYS",
        trial_duration: test_anim_duration,
        data: { trial_type: testObj.name + '_animation' }
    });
    
    // 2. Display the final freeze frame for exactly 10 seconds.
    trials.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<img src="${testObj.freeze}" class="trial-visual">`,
        choices: "NO_KEYS",
        trial_duration: 10000,
        data: { trial_type: testObj.name + '_freeze_10s' }
    });
    
    // 4. Stop webcam recording
    trials.push(stop_recording);

    return trials;
}

// ════════════════════════════════════════════════════════════════════
//  RUN THE EXPERIMENT
// ════════════════════════════════════════════════════════════════════

jsPsych.run([
    // ── Setup ──
    { type: jsPsychFullscreen, fullscreen_mode: true },
    video_config,
    video_consent,
    instructions,

    // ── Intro Recording (Placeholder) ──
    // To be done later per instructions.

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

    // ── Outro Recording (Placeholder) ──
    // To be done later per instructions.

    // ── End ──
    { type: jsPsychFullscreen, fullscreen_mode: false, delay_after: 0 },
    { type: chsSurvey.ExitSurveyPlugin }
]);
