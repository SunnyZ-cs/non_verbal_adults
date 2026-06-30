const instructions = {
    type: jsPsychHtmlButtonResponse,
    stimulus: `
        <div class="instructions-box" style="font-family: Arial, sans-serif; max-width: 750px; margin: 30px auto; text-align: left; line-height: 1.6;">
            <h2 style="text-align: center; margin-bottom: 25px; color: #2C3E50;">Study Instructions</h2>
            
            <p>Please read these instructions carefully before starting the study:</p>
            
            <ul style="padding-left: 20px; margin-bottom: 25px;">
                <li style="margin-bottom: 12px;"><strong>Webcam Gaze Tracking:</strong> Because we are studying how people direct their attention, this study uses your webcam to track where you look on the screen.</li>
                <li style="margin-bottom: 12px;"><strong>Positioning:</strong> Please sit directly in front of the center of your screen, facing the camera. Try to remain still and look at the screen throughout the videos.</li>
                <li style="margin-bottom: 12px;"><strong>Lighting:</strong> Ensure your face is clearly visible and well-lit. Avoid strong backlighting (like sitting directly in front of a bright window).</li>
                <li style="margin-bottom: 12px;"><strong>Silent Clips:</strong> The animations you will watch do not contain any audio. Please watch them carefully anyway.</li>
                <li style="margin-bottom: 12px;"><strong>Full Screen:</strong> The study will run in full-screen mode to ensure accurate measurements.</li>
            </ul>
            
            <p style="background-color: #FCF8E3; border-left: 5px solid #F0AD4E; padding: 15px; border-radius: 4px;">
                <strong>Next Step:</strong> You will be prompted to grant webcam access and align your camera feed in a preview box.
            </p>
        </div>
    `,
    choices: ['Continue to Webcam Setup ▶'],
    data: { trial_type: 'instructions' }
};
