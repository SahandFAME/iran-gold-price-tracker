# History and decisions

Prepared 2026-11-08. Evidence: owner messages available in this conversation, earlier recorded tool results and local Git history. Dates on commits are implementation timestamps, not proof of when a user originally requested a feature. Some early assistant exchanges and original screenshots are unavailable as portable files; do not invent them.

## Project evolution

### 1. Workbook automation

Original request: open `اسناد/Geram18-tahlil-updated.xlsm`, preserve its macros, fill missing daily 18K gold data from TGJU **Highest Price**, carry forward the last available day for missing observations, and extend formulas/charts. The owner explicitly required ongoing daily updates and checking the previous week's entries against TGJU on every update. Current implementation uses a 14-day rolling reconciliation window.

The owner initially discussed Windows setup, then asked for an entirely cloud-hosted approach. The final architecture uses Python serverless functions, Vercel Cron, personal Microsoft Graph OAuth, private encrypted Blob storage and OneDrive. An old GitHub Actions workflow exists in history; it is not the active scheduler. Avoid running a second scheduler accidentally.

### 2. Personal Microsoft account authorization

The owner encountered a Microsoft connector that would not accept a personal account. They registered an application in Azure/Entra, added permissions and authorized it. The source uses the `consumers` device-authorization endpoints, rather than assuming an organization tenant or a client-secret-based service account. The app ID is recorded in the main handover.

The application's OAuth grant and the chat's SharePoint connector authorization are separate. The connector was usable for later exact-file inspection/replacement even though the earlier setup path had account-type difficulties.

### 3. Hosting isolation

The owner allowed an existing Vercel project only if it would not interfere with that project; otherwise use another. Final state is an isolated `iran-gold-price-tracker` project. Do not alter the unrelated `portfolio-agent-telegram` project. A new chat does not justify a new production project or new bot identity.

### 4. Telegram reporting and access

The owner requested a Persian bot with admin/user roles, admin-approved access only, Report and admin-only Dashboard, member lists, promotions/demotions/removal, and adding users by username or ID. They supplied Telegram owner ID `118116943`. They later required an approve/deny notification for every access request, a focused dashboard, and ten users per page.

Bot naming/branding was expanded beyond 18K gold to allow future Bahar Azadi and Emami coin rates. The approved name and text are implemented in `telegram_profile.py`. The first approved image is included as `assets/didban-tala-sekke-profile.jpg`; no image regeneration is necessary to restore it. The owner reported a credential rotation; no rotated credential value belongs in this handoff.

### 5. Menu and message lifecycle corrections

An initial desire to merge menu outputs led to single-panel/inline navigation. The owner later reported the bot would not start, asked to preserve user prompts, remove the previous bot answer after the next one, retain reports, and restore menu buttons **outside chat messages**. Final main menu is a persistent Telegram reply keyboard; admin submenus use inline action buttons. Preserve this combination rather than reverting every menu to inline-only.

The owner reported that manually deleting a previous bot message caused the bot to require `/start` again. Cleanup and callback acknowledgement are now best-effort, with tests for deleted messages. `/start` still deliberately shows the introduction. Returning to `منوی اصلی` should not repeat it. Reports stay in the chat as history.

The screenshot-inspired dashboard/list design is represented in text and implementation: relevant access statistics, approved/pending/member management, numbered user entries (name, username, ID, role), per-user action buttons, ten entries per page and navigation/return buttons. Original screenshot pixels are not reconstructed or included.

### 6. Report redesign accepted by owner

The owner requested a report preview, then approved it. `آخرین قیمت` must use TGJU's live quote. Remove the Excel-calculations heading and omit the intermediate value and 85-day average. Keep five analytical fields and exact explanations, mapped to E/F/G/I/L in the main handover and source. English is the owner's chat language; Persian remains the bot's language.

The live quote and workbook cached calculation row are intentionally independent. A successful live quote does not establish that the workbook's daily inputs are current.

### 7. 2026-11-02 diagnosis and repair

The owner asked whether daily input and prior-week checking worked. Read-only comparison found the November 1 high incorrect (26,408,200 versus TGJU's 25,701,500 toman), despite an apparently successful scheduled file modification and no recorded runtime errors. The owner then authorized necessary repairs.

`273fe7d` fixed one confirmed weakness: correcting an earlier observed price did not propagate through already existing days without observations. It added regression coverage. A local dry run with official highs changed only November 1 and dependent calculations/charts; the live file was replaced by exact item ID and re-downloaded to verify the correction and unchanged VBA hash. This was not a fresh authenticated invocation of the deployed cron route.

The precise original cause of the stale November 1 value was not conclusively established from retained logs. It could reflect source availability/timing or previously carried data; do not present the reconciliation defect alone as proven root cause of that exact observed value.

### 8. Continuity request

On November 7–8 the owner requested a portable handoff in case the chat/account subscription becomes unavailable, including use in Codex, Claude Code or another model. Initial continuity docs were created locally; this expanded package adds model-neutral operations/recovery guidance, chronology, source/history, inspector and checksums. It cannot transfer internal model state or grant external access automatically.

## Git milestones

The generated package includes `history/COMMITS.txt` with full commit chronology and, if selected, a restorable Git bundle. Main milestones:

| Commit | Result |
| --- | --- |
| f5085d1 | Daily OneDrive workbook updater |
| 17cf36b | Cloud-only personal Microsoft OAuth |
| ae3b438 | Graph diagnostics |
| ff00f64 | TGJU retries and outage carry-forward |
| 5a77d61 | Persian Telegram bot with role controls |
| 7b073f7, 51302f8, 83c4fc4 | Vercel Connect token integration and await handling |
| 128916d | Redact Telegram credentials from HTTP logs |
| 8344c94 | Persian branding and approved avatar |
| b213e04–5b9fb36 | Temporary profile setup routes removed; event-driven profile sync retained |
| f2ef0fe | Intermediate single-panel navigation (superseded) |
| 720790b | Revised report and retained report history |
| a7da8a7 | Retained user messages |
| 9041288 | Persistent bottom main menu restored |
| cbd073e | Approval notifications and relevant admin dashboard |
| 1ef4291, 13ec021 | Paginated users, ten-user pages and robust cleanup |
| 273fe7d | Existing carry-forward reconciliation repair |

## Roadmap versus completed work

Implemented: daily 18K historical inputs, rolling reconciliation, VBA/formula/chart preservation, live Telegram quote, five workbook analytical fields, approval/roles/dashboard, profile branding, ten-user lists and message cleanup safeguards.

Future/undecided: additional instruments/coin workbooks, durable cron audit history and alerts, stronger concurrency/idempotency, source completeness checks. These are not authorized deployments merely because they appear here.

Unknowns to discover safely when needed: bot @username, actual Connect connection identifier, Blob store ID, current environment values, current user counts and all external account recovery details. They are not recoverable from public resource IDs alone.
