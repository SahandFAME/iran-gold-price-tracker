# Resume in Codex, Claude Code or another assistant

## Preserve outside the old chat

1. Download the complete handoff ZIP now and keep it in owner-controlled storage. It contains source at commit `273fe7d`, avatar, handoff documents, dated workbook snapshot, verification outputs and optional Git history bundle. It does **not** contain credentials, private Blob state, or the full conversation.
2. Keep GitHub as the ongoing development record. The package includes local handoff overlays; preserve them when switching to a clone. Keep these documents under version control through your normal workflow and update them after material changes.
3. Export the conversation while it is available: ChatGPT Settings → Data controls → Export data. Download the export and verify this conversation is present. Save the selected project conversation and relevant attachments securely; avoid uploading unrelated account conversations unnecessarily. An export used as reference does not restore native chat history or memory.
4. Preserve the existing Vercel project and deployment, private Blob store, Microsoft app registration/OAuth consent, Telegram bot/Connect connection, and OneDrive workbook. Save deployment/environment configuration and any recovery credentials in a secure vault separately. Preserve `TOKEN_ENCRYPTION_KEY` with a backup of encrypted Blob data. Never put these secrets in Git, chat, or this archive.

## Start the replacement workspace

1. Unpack the package in a workspace for your chosen assistant, or clone the **existing** GitHub repository and `work` branch and bring in the handoff overlays. A new development workspace does not require a new Vercel project.
2. Authorize repository access, Vercel for team `team_vmBch9HaWhgdXhVB1Xa8UNdj`, and OneDrive access for the same personal Microsoft account. Use connectors/MCP, CLI or Graph equivalents from `ACCESS_AND_RECOVERY.md`. Tools and permissions differ across platforms/accounts/plans.
3. If using ChatGPT Projects, put the handover and optional selected conversation export into project files and use the resume prompt as project instructions or the first message. If using Codex with a repository, `AGENTS.md` is the entry point. These are different context mechanisms; verify that the new agent can actually read the files.
4. Claude Code can start with `CLAUDE.md`; other coding assistants should read `START_HERE.md`. For chat-only models, upload `HANDOFF_COMPLETE.md` and the source ZIP as supported. Paste `docs/RESUME_PROMPT.md` (also packaged as `RESTART_PROMPT.md`). Have it confirm requirements, known state, and integrations it can actually access.
5. Let it inspect current code/branch, Vercel deployment, OneDrive metadata and, when relevant, live workbook rows and source prices. Historical dates are checkpoints, not today's values.

## Local development

To recover Git history offline when included, run from the extracted archive root into a new directory:

```bash
git clone --branch work history/project-work.bundle recovered-source
```

This restores committed source, not local handoff overlays. Copy `AGENTS.md`, `CLAUDE.md`, `START_HERE.md`, `.env.example`, `docs/` and `tools/` from the archive into the clone. Set the origin to the owner repository after verifying identity. The bundle contains no authentication. `git bundle verify history/project-work.bundle` can be run from inside a Git repository.

Use a compatible Python version (the previous environment used Python 3.12). In a fresh clone:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
PYTHONPATH=. .venv/bin/python -m pytest -q
```

Tests should not require live production credentials. Before changing price logic, verify VBA preservation, calculations, chart ranges, fallback chains and source outage behavior. Do not run `/api/daily_update` or `/api/telegram_setup` as read-only diagnostics: both can change live state.

## If credentials need repair

First distinguish the new chat's connector login from the deployed application's own OAuth/Connect state. Keep working configuration intact.

- Microsoft personal accounts: current code uses consumers OAuth device login with `offline_access Files.ReadWrite User.Read openid profile email`; no client secret is required by this implementation. Begin with protected POST `/api/oauth_device`, complete the owner sign-in at Microsoft's returned verification URI, then protected POST `/api/oauth_complete` following returned polling/expiry guidance. Supply the existing setup bearer secret securely, not in chat, URLs or committed scripts.
- Telegram: use the existing project-bound Vercel Connect connection and its configured `TELEGRAM_CONNECTOR`. Keep the same bot identity. BotFather ownership and tokens must be managed by the owner through secure provider settings. Only run setup when a webhook/profile change is actually required.
- Blob: restore encrypted state with its matching original encryption key, or carry out an explicit migration/re-authorization. Do not silently create an empty user store and call it a successful restore.

## References about conversation continuity

- Export: https://help.openai.com/en/articles/7260999-exporting-your-chatgpt-history-and-data
- Exported conversations as reference (not a full account/memory migration): https://help.openai.com/en/articles/9106926-transfer-exported-conversations-between-chatgpt-accounts
- Chat retention: https://help.openai.com/en/articles/8983778-chat-and-file-retention-in-chatgpt

Plan cancellation is different from account/chat deletion. New session access must still be authorized even when transcript/reference files are available.
