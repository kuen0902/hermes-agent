# Google Workspace Setup (Hermes)

This guide provides detailed instructions for setting up Google Workspace OAuth credentials for use with Hermes.

## Shorthand Definition

```bash
GSETUP="python3 ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/setup.py"
```

### Step 0: Check if already set up
```bash
$GSETUP --check
```
If it prints `AUTHENTICATED`, skip to Usage — setup is already done.

### Step 1: Triage
Before starting OAuth setup, ask the user:
1. **"What Google services do you need?"** (Email only, Email + Calendar, etc.)
2. **"Does your account use Advanced Protection?"**

### Step 2: Create OAuth credentials
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/projectselector2/home/dashboard).
2. Enable APIs: Gmail, Calendar, Drive, Sheets, Docs, People.
3. Create "Desktop app" OAuth Client ID in [Credentials](https://console.cloud.google.com/apis/credentials).
4. Add user to [Test users](https://console.cloud.google.com/auth/audience).
5. Download JSON and provide the path.

```bash
$GSETUP --client-secret /path/to/client_secret.json
```

### Step 3: Get authorization URL
```bash
$GSETUP --auth-url --services all --format json
```
Copy the `auth_url` and send it to the user.

### Step 4: Exchange the code
The user will paste back the redirect URL or code.
```bash
$GSETUP --auth-code "THE_URL_OR_CODE" --format json
```

### Step 5: Verify
```bash
$GSETUP --check
```
Should print `AUTHENTICATED`.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `NOT_AUTHENTICATED` | Redo setup steps |
| `REFRESH_FAILED` | Redo Steps 3-5 |
| `HttpError 403` | API not enabled or scope missing |
| `ModuleNotFoundError` | Run `$GSETUP --install-deps` |
