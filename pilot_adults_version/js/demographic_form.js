const demographic_form = {
    type: jsPsychSurveyHtmlForm,
    data: {
        "page_type": "participant_survey",
    },
    html: '<div style="max-width:700px; text-align:center; font-family: Arial, sans-serif;"> <p>' +
        'Please provide the following information to complete the study.' +
        ' </p> <div style="text-align:center; margin-top: 30px; margin-bottom: 30px;"> ' +
        '<div style="text-align:left; display:inline-block; margin-right:20px; line-height:2.2em; font-weight: bold;"> <ol>' +
            '<li>Age:</li> <br>' +
            '<li>Gender:</li> <br><br>' +
            '<li>Race:</li> <br><br><br><br><br><br>' +
            '<li>Ethnicity:</li>' +
        '</ol> </div>' +
        '<div style="text-align:left; display: inline-block; line-height:2.2em;">' +
            // age text box
            '<input name="age" type="number" min="18" max="100" required /> <br> <br>' +
            // gender options
            '<input name="gender" type="radio" id="female" value="Female" required /> <label for="female"> Female </label>' +
            '<input name="gender" type="radio" id="male" value="Male" /> <label for="male"> Male </label>' +
            '<input name="gender" type="radio" id="nonbinary" value="Non-binary" /> <label for="nonbinary"> Non-binary </label> <br>' +
            '<input name="gender" type="radio" id="other_gender" value="other_gender" /> <label for="other_gender"> Other: <input type="text" name="other_gender_text" /> </label> <br><br>' +
            // race options
            '<input name="race" type="radio" id="white" value="White" required /> <label for="white"> White </label> <br>' +
            '<input name="race" type="radio" id="black" value="Black/African American" /> <label for="black"> Black/African American </label> <br>' +
            '<input name="race" type="radio" id="am_ind" value="American Indian/Alaska Native" /> <label for="am_ind"> American Indian/Alaska Native </label> <br>' +
            '<input name="race" type="radio" id="asian" value="Asian" /> <label for="asian"> Asian </label> <br>' +
            '<input name="race" type="radio" id="pac_isl" value="Native Hawaiian/Pacific Islander" /> <label for="pac_isl"> Native Hawaiian/Pacific Islander </label> <br>' +
            '<input name="race" type="radio" id="other_race" value="other_race" /> <label for="other_race"> Other: <input type="text" name="other_race_text" /> </label> <br><br>' +
            // ethnicity options
            '<input name="ethnicity" type="radio" id="hisp" value="Hispanic" required /> <label for="hisp"> Hispanic </label>' +
            '<input name="ethnicity" type="radio" id="nonhisp" value="Non-Hispanic" /> <label for="nonhisp"> Non-Hispanic </label>' +
            '</div> </div>' +
            '<p> Please press the Finish button to complete the experiment. </p> </div>',
    button_label: 'Finish',
};
