# Access portability, backups and recovery

An AI model can understand the project from files. It can operate the live services only through separately authorized accounts/tools. Keep access instructions portable; a particular ChatGPT tool name is not a dependency of the deployed app.

## Equivalent capabilities in any environment

| Service | Previous access path | Portable alternative | What the owner retains |
| --- | --- | --- | --- |
| Source | Authenticated Git operations in Codex | Git + owner-approved GitHub authentication, GitHub CLI/MCP or local source archive | Repository ownership/access |
| Vercel | Connected Vercel tools | Vercel CLI, REST API or authorized Vercel MCP integration scoped to exact team/project | Vercel account/team access and existing project |
| OneDrive XLSM | SharePoint connector | Microsoft Graph with owner's delegated personal-account authorization, or manual OneDrive download/upload | Microsoft account access and exact drive/item IDs |
| Telegram bot | App's Vercel Connect connection | Existing app configuration; authorized Telegram Bot API for diagnostics where needed | BotFather ownership and existing connection |
| App storage | Encrypted private Vercel Blob | Vercel dashboard/Blob SDK with approved store access | Store access plus matching Fernet key |
| TGJU | Runtime public HTTPS endpoints | Standard HTTPS client/browser using the same public contracts | No account credential in current implementation |

Claude Code or another model does not need the original ChatGPT SharePoint plugin if it has equivalent authorized Graph or owner-assisted file access. Check its actual tools rather than pretending connector functions are globally available. Do not extract application refresh tokens into a new agent's context just to emulate the old connector.

## External resource inventory

Exact IDs are in `PROJECT_HANDOFF.md`. For secure owner records, fill these **outside this archive**:

- GitHub login/repository access and recovery methods.
- Vercel team account/recovery, project ID, private Blob store ID, project bindings, production environment variables and existing Connect connection ID.
- Microsoft account/recovery, Entra app registration, supported personal-account setting and existing delegated consent.
- Telegram owner/BotFather account/recovery and actual bot @username. Verify identity; do not assume the display name uniquely identifies a bot.
- A vault entry for `TOKEN_ENCRYPTION_KEY` matching the saved encrypted state. This is essential for existing approvals and refresh tokens.
- An inventory of other required credentials/configuration by name, with secure vault references rather than secret values pasted into the handoff.

The owner should not regenerate a working app's encryption key, bot token or client ID simply because the development assistant changed. Preserve working resource identities. Rotate only for a concrete reason, then coordinate all dependent settings and backups.

## What this archive can recover

Source tree, accepted requirements, branding, tests, exact resource locations, development history when Git bundle is present, operational procedures and a dated workbook backup. It can seed development in another coding environment without the old chat.

It cannot automatically restore external permissions, encrypted Blob objects, the matching key, current user approvals, current OAuth grants, a working account session, every original screenshot or the full chat transcript. Securely preserve those separately. A manual workbook snapshot is not an ongoing backup policy.

## Secure external-state backup procedure

1. Retain the existing resources while changing development tools. No migration is required for normal continuation.
2. Through authorized Vercel/Blob tools, record store ID, project association and all encrypted objects under `oauth/` and `telegram/`. Export original encrypted bytes plus object path names/metadata into access-controlled owner storage. Capture a consistent snapshot; pause writes or account for changes if taking a true disaster-recovery backup.
3. Store the matching original Fernet key and other recovery credentials in a separate secure vault. Verify a controlled decryption test without printing plaintext tokens/users. Record only success and backup/key identifiers.
4. Preserve production configuration (environment scopes, cron, function limits, domains/protection and Connect association). Use provider-supported secure export/transfer for secrets; never make the ordinary source archive a secret dump. A Telegram Connect credential may need the owner to recreate the connection if provider export is unavailable.
5. Keep dated workbook downloads with hashes and OneDrive version history. Test ZIP integrity and VBA hash; do not execute unknown macros while verifying backup bytes.
6. Record the date of the last successful restore test. An untested secret inventory is not proof of complete recoverability.

This handoff task does not claim an encrypted Blob or vault backup has been performed. It provides the recovery plan and names the remaining owner-controlled inputs honestly.

## If all infrastructure must be recreated

This is a distinct migration, not the default restart path. First inspect current provider documentation and available plan features. At a high level: restore source, create/link intended isolated Vercel resources, restore private Blob objects with the original matching key, configure environment scopes, restore/recreate project-bound Telegram Connect, authorize the personal Microsoft app as needed, verify the exact workbook ID in the intended account, deploy, verify read-only behavior, then deliberately register webhook and activate one scheduler. Avoid sending live requests from two simultaneous schedulers/bots during cutover.

If the original key or encrypted state is unavailable, recover the owner account and reauthorize Microsoft; user approvals and audit history may require a separate recovery/reconstruction. Do not fabricate old approvals or claim source files contain them. Changing OneDrive account, file copy or drive can change item IDs even when the filename remains the same.

## Network/environment portability

Original Codex environment used a restricted proxy with package-manager destinations and connectors; provider access through tools was separate from direct shell egress. A new environment has its own policy and credentials. Never copy the old proxy address, runtime environment ID or placeholder token as portable authentication.

Expected service domains include GitHub, Vercel API/deployment/Blob/Connect endpoints, `login.microsoftonline.com`, `graph.microsoft.com`, OneDrive download redirect hosts, `api.telegram.org`, `api.tgju.org`, `www.tgju.org` and call1/call2/call3.tgju.org. Redirect/storage/SDK endpoints can vary: determine exact required hosts from the configured service and approved requests instead of broadly weakening network controls. Allow credential transmission only to its intended providers.
