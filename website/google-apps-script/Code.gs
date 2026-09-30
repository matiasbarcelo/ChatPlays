/**
 * ChatPlays mailing list -> Google Sheet.
 *
 * Paste this into Extensions > Apps Script on the sign-up spreadsheet, then
 * Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
 * Put the resulting /exec URL in the form's data-endpoint in website/index-v2.html.
 * See README.md next to this file for the full walkthrough.
 */

const SHEET_NAME = 'Signups';

// Column order in the sheet. Keys match the fields the website sends.
const COLUMNS = [
  ['received', 'Received'],
  ['email', 'Email'],
  ['duplicate', 'Already signed up'],
  ['country', 'Country'],
  ['region', 'Region'],
  ['city', 'City'],
  ['timezone', 'Timezone'],
  ['localTime', 'Visitor local time'],
  ['language', 'Language'],
  ['device', 'Device'],
  ['screen', 'Screen'],
  ['userAgent', 'Browser (user agent)'],
  ['page', 'Page'],
  ['referrer', 'Referrer'],
  ['utmSource', 'UTM source'],
  ['utmMedium', 'UTM medium'],
  ['utmCampaign', 'UTM campaign'],
  ['secondsOnPage', 'Seconds on page'],
  ['visitCount', 'Visit #'],
  ['firstVisit', 'First visit'],
];

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function doPost(e) {
  const params = (e && e.parameter) || {};

  // Honeypot: the "website" field is hidden from people, so only bots fill it.
  // Answer as if it worked so they don't retry.
  if (params.website) return json_({ ok: true });

  const email = String(params.email || '').trim().toLowerCase();
  if (!EMAIL_PATTERN.test(email) || email.length > 254) {
    return json_({ ok: false, error: 'invalid_email' });
  }

  // Serialise writes so two sign-ups at once can't interleave rows.
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const sheet = getSheet_();
    const duplicate = emailExists_(sheet, email);
    const values = Object.assign({}, params, {
      received: new Date(),
      email: email,
      duplicate: duplicate ? 'yes' : '',
    });
    sheet.appendRow(COLUMNS.map(([key]) => cell_(values[key])));
    return json_({ ok: true, duplicate: duplicate });
  } finally {
    lock.releaseLock();
  }
}

// Visiting the /exec URL in a browser confirms the deployment is live.
function doGet() {
  return json_({ ok: true, service: 'ChatPlays mailing list' });
}

function getSheet_() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);
  if (!sheet) {
    // Reuse a new spreadsheet's blank first tab rather than leaving it empty beside ours.
    const first = spreadsheet.getSheets()[0];
    sheet = first.getLastRow() === 0 ? first.setName(SHEET_NAME) : spreadsheet.insertSheet(SHEET_NAME);
  }
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(COLUMNS.map(([, header]) => header));
    sheet.getRange(1, 1, 1, COLUMNS.length).setFontWeight('bold');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function emailExists_(sheet, email) {
  const rows = sheet.getLastRow() - 1;
  if (rows < 1) return false;
  const emailColumn = COLUMNS.findIndex(([key]) => key === 'email') + 1;
  return sheet
    .getRange(2, emailColumn, rows, 1)
    .getValues()
    .some(([value]) => String(value).toLowerCase() === email);
}

// Keeps visitor-supplied text inert: Sheets treats a leading = + - @ as a formula.
function cell_(value) {
  if (value instanceof Date) return value;
  if (value === undefined || value === null) return '';
  const text = String(value).slice(0, 500);
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function json_(body) {
  return ContentService.createTextOutput(JSON.stringify(body))
    .setMimeType(ContentService.MimeType.JSON);
}
