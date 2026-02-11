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

## Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Gmail API**:
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API" and click **Enable**

### 2. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. If prompted, configure the OAuth consent screen:
   - Choose **External** user type
   - Fill in the required fields (app name, email)
   - Add scopes: `gmail.readonly` and `gmail.modify`
   - Add your email as a test user
4. For Application type, select **Desktop app**
5. Download the JSON file and save it as `credentials.json` in the project root

### 3. Install

```bash
pip install -e .
```

### 4. Usage

```bash
# Analyze your inbox (first 500 emails)
gmail-katazuke analyze

# Analyze with a query filter and higher limit
gmail-katazuke analyze -q "is:unread" -n 1000

# Interactive organize mode (analyze + clean up)
gmail-katazuke organize

# Quick actions
gmail-katazuke archive --older-than 180
gmail-katazuke mark-read --sender "notifications@example.com"
gmail-katazuke trash --sender "spam@example.com"
```

On first run, a browser window will open for Google OAuth authorization. The token is saved to `token.json` for subsequent runs.

## Security

- `credentials.json` and `token.json` are in `.gitignore` and should never be committed
- The tool requests `gmail.readonly` and `gmail.modify` scopes
- All destructive actions (trash, archive) require interactive confirmation
