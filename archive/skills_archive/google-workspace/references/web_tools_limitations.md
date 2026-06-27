# Web-Only AI Tools Management (NotebookLM, Perplexity, etc.)

## The Barrier: Personal Account Auth
Most advanced AI research tools like Google NotebookLM and Perplexity Pro are locked behind user-specific Google/SAML logins.

### Limitations
- **No API/OAuth**: Unlike Gmail or Calendar, there is no standardized API or OAuth scope for an agent to "log in" and read your private Notebooks.
- **Browser State Isolation**: The agent's automation browser does not share the user's cookies or session state.
- **2FA/Security**: Direct login via agent is blocked by Google's anti-bot/2FA mechanisms.

## Workflow: Data Extraction & Analysis
When a user provides a private NotebookLM link, do not attempt to log in. Follow this "Bridge" workflow:

1. **Acknowledge the Barrier**: Explain that the content is private and non-accessible via automation.
2. **Request Material Export**: Ask the user to copy/paste the specific notes, summary, or "Audio Overview" transcript into the chat.
3. **Analyze Locally**: Once the text is provided, perform the requested analysis (summarization, structured extraction, cross-referencing).
4. **Source Grounding**: If the user has the original source files in Google Drive, use the `google-workspace` tool to read the *raw sources* instead of the NotebookLM processed version.
