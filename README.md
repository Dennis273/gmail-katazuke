# gmail-katazuke

Gmail inbox analyzer and organizer. Analyze your email patterns first, then clean up with batch operations.

## Features

**Analysis** (`analyze` command):
- Top senders ranking
- Subscription / newsletter detection
- Label distribution
- Email age distribution
- Monthly volume trends
- Largest emails by size
- Unread email statistics

**Organization** (`organize` command):
- Archive old emails
- Batch mark as read
- Apply labels by sender
- Trash emails by sender
- Interactive subscription management (trash / archive / label each)

**Quick actions**:
- `archive` — Archive emails older than N days
- `mark-read` — Mark emails as read (optionally by sender)
- `trash` — Trash all emails from a sender

## What has been done (by the tool author)

The following steps have already been completed:

1. Project scaffolding (`pyproject.toml`, package structure)
2. All source code (`auth.py`, `fetcher.py`, `analyzer.py`, `organizer.py`, `cli.py`)
3. Dependency installation (`pip install -e .`)
4. CLI verification — `gmail-katazuke --help` runs successfully

## What you (the user) must do, and why

There are exactly **2 things** that require your manual action. Both are unavoidable for technical reasons explained below.

### Step 1: Create a Google Cloud OAuth credential file

**What to do:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API**: navigate to **APIs & Services > Library**, search "Gmail API", click **Enable**
4. Go to **APIs & Services > Credentials**, click **Create Credentials > OAuth client ID**
5. If prompted, configure the OAuth consent screen:
   - Choose **External** user type
   - Fill in required fields (app name, your email)
   - Add scopes: `gmail.readonly` and `gmail.modify`
   - Add your email as a test user
6. For Application type, select **Desktop app**
7. Download the JSON file and save it as `credentials.json` in this project's root directory

**Why this cannot be automated:**

- Google Cloud Console requires you to log in with **your Google account** in a browser. I have no access to your browser session or Google account credentials, nor should I — that would be a security risk.
- OAuth credentials are tied to a specific Google Cloud project under your account. Creating them programmatically would require a pre-existing service account key, which is itself a credential you'd have to create manually first — a chicken-and-egg problem.
- Google intentionally requires human interaction for credential creation to prevent automated abuse.

### Step 2: Authorize the app on first run

**What to do:**

Run any command (e.g. `gmail-katazuke analyze`). A browser window will automatically open asking you to sign in with your Google account and grant the app access to your Gmail. Click "Allow". This only needs to be done once — the token is saved to `token.json` for future use.

**Why this cannot be automated:**

- OAuth2 authorization requires you to authenticate with Google in a browser and explicitly consent to granting this app access to your email. This is a security mechanism — no program should be able to access your email without your explicit, interactive consent.
- The authorization flow involves a redirect URI that the local server captures. This requires a browser environment with an active Google session, which I do not have access to.

### After these 2 steps

Once `credentials.json` is in place and you've completed the OAuth flow, **everything else is automated**. You can run:

```bash
# Analyze your inbox (default: 500 most recent emails)
gmail-katazuke analyze

# Analyze more emails with a filter
gmail-katazuke analyze -q "is:unread" -n 1000

# Interactive mode: analyze first, then organize
gmail-katazuke organize

# Quick actions
gmail-katazuke archive --older-than 180
gmail-katazuke mark-read --sender "notifications@example.com"
gmail-katazuke trash --sender "spam@example.com"
```

## Security

- `credentials.json` and `token.json` are in `.gitignore` and will never be committed
- The tool requests `gmail.readonly` (for analysis) and `gmail.modify` (for organizing) scopes
- All destructive actions (trash, archive, mark read) require interactive confirmation before execution
- No email content is stored locally — only metadata (sender, subject, date, size, labels) is processed in memory
