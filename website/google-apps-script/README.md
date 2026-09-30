# Mailing list → Google Sheet

The sign-up form in `website/index-v2.html` posts each email, plus visit details, to a
Google Apps Script web app, which appends a row to a Google Sheet. It's free and needs
no server.

## One-time setup (about 5 minutes)

1. Create a new Google Sheet (for example, "ChatPlays mailing list") in the Google
   account that should own the sign-ups.
2. In the sheet, open **Extensions → Apps Script**.
3. Delete the starter code, paste in everything from [`Code.gs`](Code.gs), and save.
4. Click **Deploy → New deployment**, pick the gear icon → **Web app**, then set:
   - **Execute as:** Me
   - **Who has access:** Anyone

   Click **Deploy** and approve the permissions prompt. The script only touches the
   spreadsheet it's attached to.
5. Copy the **Web app URL**. It ends in `/exec`.
6. In `website/index-v2.html`, paste that URL into the form's `data-endpoint=""`
   attribute.

To check the deployment, open the `/exec` URL in a browser. It should show
`{"ok":true,"service":"ChatPlays mailing list"}`. The `Signups` tab and its header row
are created on the first sign-up.

## Updating the script later

Edit the code in the Apps Script editor, then use **Deploy → Manage deployments →
edit (pencil) → Version: New version → Deploy**. That keeps the same `/exec` URL, so the
website doesn't need changing. Creating a *new deployment* gives a new URL instead.

## What each row contains

| Column | Where it comes from |
| --- | --- |
| Received | Time Google received the sign-up (the sheet's timezone) |
| Email | What the visitor typed, trimmed and lowercased |
| Already signed up | `yes` if that email is already in the sheet |
| Country / Region / City | Approximate, from the visitor's IP via geojs.io. The IP itself is not stored |
| Timezone, Visitor local time, Language | The visitor's browser settings |
| Device, Screen, Browser (user agent) | The visitor's browser |
| Page, Referrer | The page they signed up on, and the site that sent them there |
| UTM source / medium / campaign | From `?utm_source=…` links, for tracking campaigns |
| Seconds on page | Time between the page loading and them pressing Send |
| Visit #, First visit | Counted in the visitor's own browser, so they reset if the visitor clears site data |

## Protections built in

- The email format is checked on the server; invalid ones are rejected.
- A hidden "website" field catches bots. Rows where it's filled are silently dropped.
- Values starting with `=`, `+`, `-` or `@` are stored as text, so nothing a visitor
  types can run as a spreadsheet formula.
- Writes are locked one at a time, so simultaneous sign-ups can't collide.

## Privacy

The form shows a one-line notice that it records approximate location, device, and
referral source. If the site gets visitors from the EU/UK or California, you'll want
a privacy policy page covering this, and a way for people to ask to be removed.
