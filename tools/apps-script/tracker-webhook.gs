/**
 * MPP Assistant → Project Tracker webhook (Google Apps Script)
 * ------------------------------------------------------------
 * No Google Cloud, no service account, no credentials file. The assistant just POSTs here and this
 * script appends a row to the "AI MT LOG RECS" tab of whatever sheet this script is bound to.
 *
 * SETUP (one time, ~3 minutes):
 *   1. Open your Project Tracker Google Sheet.
 *   2. Extensions → Apps Script. Delete whatever is there and paste this whole file. Save.
 *   3. Deploy → New deployment → gear icon → Web app.
 *        - Description: MPP Assistant tracker
 *        - Execute as: Me
 *        - Who has access: Anyone
 *      → Deploy. (Authorize it when asked — it's your own script on your own sheet.)
 *   4. Copy the "Web app URL" it gives you.
 *   5. On the PC, set a Windows environment variable:
 *        MPP_TRACKER_WEBHOOK_URL = <that URL>
 *      (same place you set ANTHROPIC_API_KEY). Restart the assistant.
 *   6. Click "Add to Project Tracker" on a card → a new row appears in the tab below.
 *
 * OPTIONAL shared secret (stops random POSTs): set SECRET below to any word, and also set a Windows
 * env var MPP_TRACKER_SECRET to the same word. Leave SECRET = "" to skip.
 */

var TAB_NAME = 'AI MT LOG RECS';
var SECRET = ''; // set to a word to require ?secret=... ; leave "" to allow any POST

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents || '{}');
    if (SECRET && (!e.parameter || e.parameter.secret !== SECRET)) {
      return ContentService.createTextOutput('forbidden');
    }
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(TAB_NAME) || ss.insertSheet(TAB_NAME);
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(['When', 'Suggestion', 'Why', 'Urgency']); // header on first write
    }
    sheet.appendRow([
      data.time || new Date(),
      data.title || '',
      data.why || '',
      data.urgency || ''
    ]);
    return ContentService.createTextOutput('ok');
  } catch (err) {
    return ContentService.createTextOutput('error: ' + err);
  }
}

// Lets you test the URL in a browser (should say "MPP tracker webhook is live").
function doGet() {
  return ContentService.createTextOutput('MPP tracker webhook is live');
}
