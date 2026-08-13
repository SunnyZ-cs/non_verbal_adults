// ════════════════════════════════════════════════════════════════════
//  NON-VERBAL FULL STUDY — CHS jsPsych version (REVISED after lab meeting)
//
//  Changes vs. previous version:
//   (1) Characters have eyes only (no mouths/expressions); star authority
//       keeps its expressions. All character stimuli re-rendered.
//   (2) Familiarization/warmup replaced: THREE punishment-only warmups,
//       each with a SINGLE character (left / center / right position),
//       order randomized and recorded (warmup_order in data).
//   (3) Test trials now include an ANTICIPATORY FREEZE: the animation
//       pauses just before the authority reveals its target — the star
//       turns angry at center ("getting ready to punish") and the scene
//       freezes for anticipatory looking. The scene then unfolds as
//       usual (approach + star removal) and ends with the outcome freeze
//       for post-punishment looking time.
//
//  Test trial timeline (recorded as one webcam segment):
//    bullseye 3.0 s
//    part1 GIF  (causal event x3, ends with static scene)   ~15.9 s
//    ANTICIPATORY FREEZE (angry star at center)               3.0 s
//    part2 GIF  (authority approaches target, removes star)  ~2.9 s
//    outcome freeze                                           8.0 s
//
//  Paste the contents of this file directly into the
//  "jsPsych Experiment Code" editor on childrenhelpingscience.com.
// ════════════════════════════════════════════════════════════════════


// ── Inject CSS ──
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
    .trial-visual {
        display: block;
        width: 100%;
        max-height:70vh;
        margin: 0 auto;
        object-fit: contain;
    }
    .instructions-box {
        max-width: 680px;
        margin: 30px auto;
        font-size: 1.1em;
        line-height: 1.7;
        text-align: left;
    }
    .instructions-box h2 { margin-bottom: 10px; }
    .instructions-box ul  { padding-left: 1.4em; }
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

const BASE = 'https://raw.githubusercontent.com/SunnyZ-cs/non_verbal_adults/main/non_verbal_full_study_updated/materials/';

// ── Warmup (punishment-only, single character; replaces familiarization) ──
const warmup_positions = ['left', 'center', 'right'];
// Fisher-Yates shuffle; the resulting order is RECORDED in the data
for (let i = warmup_positions.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [warmup_positions[i], warmup_positions[j]] = [warmup_positions[j], warmup_positions[i]];
}
const warmup_durations = {
    left: 13880,
    center: 13880,
    right: 13440
};
const warmup_gap = 1000;              // blank between warmups

// ── Context / direction / order randomization (unchanged) ──
const context = Math.random() < 0.5 ? 'chains' : 'single_cause';
const direction = Math.random() < 0.5 ? 'forward' : 'backward';
const is_forward = direction === 'forward';

function testFiles(cond) {
    const stem = `${context}_` + (is_forward ? '' : 'reverse_') + `${cond}_test`;
    return {
        part1:  BASE + stem + '_part1.gif',
        antic:  BASE + stem + '_anticipatory_freeze.png',
        part2:  BASE + stem + '_part2.gif',
        freeze: BASE + stem + '_final_freeze.png',
    };
}

// Phase durations (ms). part1/part2 match the exact GIF split points.
const part1_duration  = 15920;   // causal event x3 + static scene (pre-reveal)
const antic_duration  = 3000;           // ANTICIPATORY FREEZE: angry star at center
const part2_duration  = 2840;   // authority approaches target + removes star
const freeze_duration = 8000;           // outcome freeze (post-punishment looking) -- shortened from
                                         // 20s: window-comparison analyses (report_to_david.md) show
                                         // the unpunished-preference effect is strongest at 0-1s, still
                                         // present at 1-3s, and only weakens (not adds new signal) after
                                         // that, while away-looking roughly doubles (9-12% -> 20-21%)
                                         // over the later part of the old 20s window.

const test_order = Math.random() < 0.5 ?
    [{name: 'distal',  files: testFiles('distal')},  {name: 'proximal', files: testFiles('proximal')}] :
    [{name: 'proximal', files: testFiles('proximal')}, {name: 'distal',  files: testFiles('distal')}];

const assigned_combo = `${context}_` + (is_forward ? '' : 'reverse_') + `${test_order[0].name}_test_final.gif`;

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
    purpose:     'This study is about how children perceive causal chains, single causes, and responsibility.',
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
                btn.disabled = true;
                const vid = document.getElementById(`${trial_name}-vid`);
                if (vid) {
                    vid.addEventListener('ended', () => { btn.disabled = false; });
                    vid.addEventListener('error', () => { btn.disabled = false; });
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

// ── Warmup punishment trial (single character, one of 3 positions) ──
// The GIF plays once (loop=1 encoded in the file) then holds its last frame.
function buildWarmupPunishTrial(position, index) {
    return {
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<img src="${BASE}warmup_punish_${position}.gif" class="trial-visual">`,
        choices: "NO_KEYS",
        trial_duration: warmup_durations[position],
        post_trial_gap: 0,
        data: { trial_type: 'warmup_punish', warmup_position: position, warmup_index: index }
    };
}

// ── Bullseye (attention refixation, 3 s) ──
function bullseyeTrial(tag) {
    return {
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
        data: { trial_type: tag + '_bullseye' }
    };
}

// ── Test trial: part1 -> ANTICIPATORY FREEZE -> part2 -> outcome freeze ──
// One <img> element; src swaps at exact phase boundaries. All phases are
// inside a single webcam recording segment (recording spans the whole
// timeline built in buildTestTimeline).
function buildTestTimeline(testObj) {
    const trials = [];
    const f = testObj.files;

    // 0. Start webcam recording FIRST.
    trials.push(start_recording);

    // 0.5. Pulsing bullseye (3 s)
    trials.push(bullseyeTrial(testObj.name));

    // 1. part1 + anticipatory freeze + part2 + outcome freeze in ONE trial
    //    (single <img>, zero-flash src swaps; all images preloaded first)
    trials.push({
        type: jsPsychHtmlKeyboardResponse,
        stimulus: `<img id="test-visual" src="${f.part1}" class="trial-visual">`,
        choices: "NO_KEYS",
        trial_duration: part1_duration + antic_duration + part2_duration + freeze_duration,
        on_load: function() {
            // Preload every later phase immediately so swaps are instant
            [f.antic, f.part2, f.freeze].forEach(src => { const im = new Image(); im.src = src; });
            const el = document.getElementById('test-visual');
            // ANTICIPATORY FREEZE: angry star at center, target not yet knowable
            setTimeout(function() { if (el) el.src = f.antic; }, part1_duration);
            // Reveal: authority flies to its target and removes the star
            setTimeout(function() { if (el) el.src = f.part2; }, part1_duration + antic_duration);
            // Outcome freeze: post-punishment looking time
            setTimeout(function() { if (el) el.src = f.freeze; }, part1_duration + antic_duration + part2_duration);
        },
        data: {
            trial_type: testObj.name + '_full_test',
            phase_durations: {
                bullseye: 3000,
                part1: part1_duration,
                anticipatory_freeze: antic_duration,
                part2: part2_duration,
                outcome_freeze: freeze_duration
            }
        }
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

            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;">This study is a follow-up to our previous research examining how children trace fault and responsibility. In this combined study, we examine and compare children's judgments in two different scenarios: causal chains (where a distal cause shape initiates an action that propagates through a proximal cause shape to break a cube) and single causes (where only the proximal cause shape directly breaks the cube while the distal cause shape remains inactive).</p>

            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;">In our previous work, we found that younger children tend to focus on the direct, proximal cause (the agent that physically contacts the object), while older children can trace responsibility back to the initial, distal cause (the agent that started the chain reaction).</p>

            <p style="margin-bottom: 1.5em; font-size: 1.05em; color: #444;">With this design, we use a non-verbal eye-tracking method. By measuring where children look on the screen while watching shapes interact — especially during the moment just before the star authority chooses which shape to punish — we are testing whether younger children can represent these causal structures implicitly, even when they struggle to express these relationships verbally.</p>

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

    // ── Record randomizations (incl. warmup order) ──
    {
        type: jsPsychHtmlButtonResponse,
        stimulus: '',
        choices: [],
        trial_duration: 0,
        data: {
            trial_type: 'randomization_info',
            warmup_order: warmup_positions.slice(),
            test_order: [test_order[0].name, test_order[1].name],
            direction: direction,
            assigned_combo: assigned_combo,
            context: context,
            phase_durations: {
                warmup: warmup_durations,
                part1: part1_duration,
                anticipatory_freeze: antic_duration,
                part2: part2_duration,
                outcome_freeze: freeze_duration
            }
        }
    },

    // ── Warmup Phase: 3 punishment-only warmups, single character,
    //    positions randomized (order recorded above) ──
    bullseyeTrial('warmup_0'),
    buildWarmupPunishTrial(warmup_positions[0], 0),
    bullseyeTrial('warmup_1'),
    buildWarmupPunishTrial(warmup_positions[1], 1),
    bullseyeTrial('warmup_2'),
    buildWarmupPunishTrial(warmup_positions[2], 2),

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
