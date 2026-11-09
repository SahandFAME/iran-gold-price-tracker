# Project handover: دیدبان طلا و سکه

Updated 2026-11-08 (Asia/Tehran). This is a model-independent, curated continuity record from the available conversation and checked repository, not a verbatim transcript or a clone of model memory. Pair it with the owner's exported conversation for fuller historical context. Never infer current production health solely from this document. Start with `START_HERE.md` for all companion documents, including operations, recovery and technical limitations.

## Goal and owner preferences

Cloud-only daily maintenance of the owner's macro-enabled 18K gold workbook and an approval-only Persian Telegram reporting bot. More instruments, particularly Bahar Azadi and Emami coins, are intended later; they are not implemented here.

The owner wants smooth continuation across chats, concise English explanations, and implementation carried through when authorized. The bot itself is Persian. Avoid repeatedly asking for approval already given for the current task. Protect unrelated projects: this application has its own Vercel project, separate from `portfolio-agent-telegram`. Windows was the owner's local platform, but no always-on local computer is required.

## Exact resources (identifiers are not credentials)

| Resource | Identifier |
| --- | --- |
| Git repository | https://github.com/SahandFAME/iran-gold-price-tracker.git |
| Working branch | `work` |
| Source commit at handover | `273fe7d64127a6205d098360d7ccade8fa2498ef` |
| Local checkout in original environment | `/workspace/iran-gold-price-tracker` (not portable) |
| Vercel project | `iran-gold-price-tracker` / `prj_LS44me3kkj8uFZIW9KrgRvL2omEQ` |
| Vercel team | `team_vmBch9HaWhgdXhVB1Xa8UNdj`, slug `sahand-r5-6417` |
| Production URL | https://iran-gold-price-tracker.vercel.app |
| Last deployment seen on 2026-11-08 | `dpl_2wZEsgwQWUcnVJu8f1HQYR3isTLs`, READY, production |
| Deployment hostname | `iran-gold-price-tracker-fa446lten-sahand-r5-6417.vercel.app` |
| Microsoft app/client ID supplied by owner | `e275459e-299b-41ea-a520-79a88e1a019b` (verify configured `MS_CLIENT_ID`) |
| OneDrive workbook | `اسناد/Geram18-tahlil-updated.xlsm` |
| Graph drive | `0DAEF687B3C624F3` |
| Workbook item | `DAEF687B3C624F3!sde344ae14e91495397b344c5c8bbdbe4` |
| Documents folder item | `DAEF687B3C624F3!105` |
| Protected Telegram owner ID supplied by owner | `118116943` (verify configured `TELEGRAM_ADMIN_ID`) |

Workbook browser link:
https://onedrive.live.com/personal/0daef687b3c624f3/_layouts/15/doc.aspx?resid=de344ae1-4e91-4953-97b3-44c5c8bbdbe4&cid=0daef687b3c624f3

Telegram public name: `دیدبان طلا و سکه | گزارش بازار`. Do not guess the bot's @username or connector identifier; query existing configured bot identity if needed. Branding is in `gold_updater/telegram_profile.py`; the approved first profile picture is `assets/didban-tala-sekke-profile.jpg`.

## Architecture and code map

- `vercel.json`: platform cron, `30 17 * * *` UTC = daily 21:00 Tehran. Hobby scheduling is not evidence of exact-to-the-minute execution.
- `api/daily_update.py`: authenticated GET, accepts `CRON_SECRET` or `SETUP_SECRET` bearer token. This GET **writes the workbook**; it is not a read-only health check.
- `gold_updater/service.py`: Microsoft token, metadata/eTag, download, TGJU historical observations, workbook reconciliation, Graph PUT with `If-Match`.
- `gold_updater/workbook.py`: edits OOXML ZIP parts directly; extends shared formulas and cached calculations plus six chart ranges/caches; validates ZIP and identical VBA hash. Avoid generic XLSM re-saving that may lose package parts.
- `gold_updater/tgju.py`: historical highs and separate live quote fetchers.
- `gold_updater/microsoft.py`: personal-account Microsoft OAuth device authorization and encrypted private Blob token storage.
- `api/oauth_device.py`, `api/oauth_complete.py`: setup-secret-protected POST routes to begin and complete device authorization.
- `api/telegram.py`: webhook validates `X-Telegram-Bot-Api-Secret-Token`.
- `gold_updater/telegram_bot.py`: access checks, menu flows, pagination, bot-answer cleanup.
- `gold_updater/telegram_store.py`: encrypted users, audit events, profile marker in Blob.
- `gold_updater/telegram_api.py`: token from Vercel Connect using project OIDC. HTTPX INFO logging disabled to avoid logging bot tokens in URLs.
- `gold_updater/report.py`: independent live quote and latest workbook calculation snapshot.
- `api/telegram_setup.py`: protected GET which sets webhook/commands/profile; this **mutates Telegram configuration**.
- `api/health.py`: read-only health endpoint, returns `{"ok": true}`. It does not prove source/Graph/cron success.
- `gold_updater/cli.py`: downloaded local workbook update; inspect flags before use.

Python dependency versions are pinned in `requirements.txt`. Tests use pytest (development dependency, not listed there).

## Daily prices and workbook invariants

Historical source: https://api.tgju.org/v1/market/indicator/summary-table-data/geram18

Official comparison page: https://www.tgju.org/profile/geram18/history

Use **Highest Price**, not opening, closing, lowest, or current price, for each calendar day's workbook input. TGJU publishes rial; divide by 10 for toman. Append every Tehran date; when unavailable for any reason, carry the last available price forward. Each run fetches from the workbook's latest date minus 14 days and reconciles the recent period (exceeds the requested previous week). Corrections must propagate to dependent carry-forward days and cached calculations/charts.

`C` = Excel date serial, `D` = daily high input in toman. Cached analytical columns:

| Column | Existing calculation | Report usage |
| --- | --- | --- |
| E | 240-row mean of D | Arbitrage |
| I | 370-row mean of D | Floor |
| F | I × 1.3 | Current equilibrium |
| G | I × 1.6 | Upper bound |
| H | I × 1.1 | Not shown in report |
| K | 85-row mean of D | Not shown in report |
| L | 65-row mean of D | Cyclical movement |

These are the workbook's existing definitions, not newly endorsed financial models. Preserve formulas and labels unless the owner changes them.

Retryable source outages use empty observations and append carry-forward rows without rewriting existing history. Other error paths should be diagnosed; do not claim every error type is handled. A successful HTTP response or file modification timestamp alone does not establish that TGJU highs are correct.

## Telegram UX: accepted requirements

- Only approved users can access reports. Roles: user/admin, with protected root administrator.
- Each access request notifies approved admins with approve/deny buttons.
- Main menu is a persistent Telegram **bottom reply keyboard**, outside the message content. Report for approved users; Admin Dashboard for admins.
- Submenus use appropriate numbered action buttons and the screenshot-inspired dashboard/list style. **Ten users per page**, with navigation and dashboard/main-menu return buttons.
- Admins list approved users and pending requests, add members by numeric ID or known username, promote/demote/remove. A username must already be known to the bot; Telegram bots cannot arbitrarily resolve every username or message someone who never started the bot.
- Going to `منوی اصلی` shows a compact menu, not the full welcome again. `/start` may show the introduction.
- Never delete user requests/prompts. Delete only the preceding transient **bot answer** on a new answer, best-effort. If the user already deleted it, continue normally; no mandatory `/start` recovery.
- Preserve report messages/history; reports are not deleted with transient menu cleanup.
- Keep unrelated dashboard concepts (financial advisers, access expiry, etc.) out unless implemented and requested.

## Exact accepted report fields

Current TGJU live quote label: **آخرین قیمت**. It uses the current quote, not the historical high or a fallback silently labelled live. If unavailable, say so.

Then show these workbook values, in order, with these explanations:

1. `E`: **قیمت آربیتراژی** — خرید چشم بسته که معمولاً در صورت دیده شدن بسیار کوتاه مدت خواهد بود
2. `F`: **قیمت تعادلی جاری** — قیمت منصفانه فعلی
3. `G`: **کران محاسباتی بالا** — قیمتی که حباب خیلی بالا است و ارزش خرید در مقطع کنونی ندارد
4. `I`: **کف محاسباتی** — پایین ترین قیمتی که در مقطع کنونی میتوان متصور شد
5. `L`: **قیمت حرکت چرخه ای** — قیمتی که معمولاً در صورت دیده شدن از همانجا یا کمی پایینتر قیمت برمیگردد

Omit the `محاسبات فایل اکسل` section heading, `ارزش حدودی مقطعی`, and the 85-day moving average. Persian number formatting, toman, and existing short analytical disclaimer remain. The owner previously requested a preview before publishing report-format changes; provide one for a future redesign.

## Access and state: two independent layers

**New Codex session access**: authorize GitHub/repository access, Vercel for the exact team/project, and SharePoint connector for the owner's OneDrive. Tool availability, scopes, plugins and environment network access belong to the new session/account and cannot be inherited by reading this file. The previous chat successfully used Vercel and SharePoint connectors; Git push used its environment's configured authentication. Never copy session cookies or access tokens to imitate the old chat.

**Existing application's access**: deployed Vercel environment variables, Blob state, Microsoft OAuth grant, Telegram Connect connection, and webhook remain external to the chat. Reusing the same deployment/resources can preserve them without issuing new tokens. Reauthorizing ChatGPT's SharePoint connector does not repair the application's separate Microsoft OAuth grant, or vice versa.

Production variables to check by **name**, never print their values:

| Name | Purpose / preservation |
| --- | --- |
| MS_CLIENT_ID | Personal Microsoft app ID |
| GRAPH_DRIVE_ID, GRAPH_ITEM_ID | Exact workbook target |
| TOKEN_ENCRYPTION_KEY | Fernet key for stored Microsoft tokens and Telegram state; preserve with encrypted data |
| BLOB_READ_WRITE_TOKEN | Existing private Blob store SDK credential; verify actual project binding |
| SETUP_SECRET | Auth for setup/authorization routes and controlled update |
| CRON_SECRET | Cron bearer auth |
| TELEGRAM_CONNECTOR | Existing Vercel Connect connection identifier |
| TELEGRAM_WEBHOOK_SECRET | Telegram webhook secret header |
| TELEGRAM_ADMIN_ID | Protected root ID |

The earlier screenshot also had `CONNECT_SUBJECT_ID`; current source does not directly read it. Inspect existing integration requirements rather than deleting it. `VERCEL_PROJECT_PRODUCTION_URL` and project OIDC are supplied by Vercel. The Telegram BotFather token is held by **Vercel Connect**, not a bot-token environment variable in this source.

Private Blob paths:

- `oauth/microsoft-token.json.enc` (access/refresh token and expiry)
- `oauth/microsoft-device.json.enc` (temporary authorization state)
- `telegram/users/{id}.json.enc` (roles, approval, interaction state)
- `telegram/audit/…json.enc` (administration audit)
- `telegram/profile/state.json.enc` (profile version marker)

Do not replace the encryption key with a new random key while retaining existing encrypted data: that makes tokens/users unreadable. Secure backups of the original key and encrypted Blob data must be managed together in the owner's vault, outside Git and ordinary handover archives. If recreating all resources becomes necessary, restoring source alone is insufficient.

## Dated incident and verification history

On 2026-11-02, comparison of 2026-10-26 through 2026-11-01 found six correct dates (including 2026-10-30 carry-forward) and one discrepancy. November 1 was 26,408,200 toman in row 4012 while TGJU Highest Price was 25,701,500. File modifications and no runtime errors had not proved correctness.

Commit `273fe7d` repairs the case where an earlier corrected observation must propagate through existing fallback rows. Regression tests cover corrected carry-forward and full source outage. 23 tests passed using `PYTHONPATH=. .venv/bin/pytest -q`. The dry run changed only November 1 and dependent cached calculations/charts; no November 2 row was appended early.

The code was pushed to GitHub and deployed explicitly with Vercel's create-deployment API from Git source (`SahandFAME/iran-gold-price-tracker`, branch `work`, exact SHA), because a Git push alone did not trigger this project's deployment. Preserve this distinction; do not assume automatic Git deployments are connected.

The live workbook was corrected through the SharePoint connector's exact-item replacement, then downloaded and verified. This was a **controlled manual workbook repair**, not evidence that an authenticated end-to-end cron update was manually invoked. All six charts and shared formulas ended at row 4012. VBA SHA-256 before/after:
`db0cb50f67b4ac80f1afe1e8e535b42821c8798bf636d128c5f7dae67e15d20f`.

Production health returned HTTP 200 `{"ok": true}` using Vercel's authenticated deployment fetch. The post-deployment runtime error scan was clean. Direct curl received 403; exact cause was not established in the transcript (network policy and Vercel protection both need checking). Use authorized access rather than weakening protection. Hobby runtime-log retention is short; lack of old logs is not proof of cron success.

Fresh **metadata-only** checks on 2026-11-07: Vercel still reported the same production deployment READY. OneDrive reported the workbook last modified on 2026-11-06 at 17:38:57 UTC / 21:08:57 Tehran, size 6,724,083 bytes, eTag `"{DE344AE1-4E91-4953-97B3-44C5C8BBDBE4},22"`. This does not independently verify its latest row or TGJU price accuracy.

## Open limitations and next work

- Verify live rows and TGJU history when asked about health; cached metadata is insufficient.
- No durable cron success journal/alerting was added in the last repair. Consider it if requested; no automatic monitoring by this chat is promised.
- Future rates/coins are a roadmap item, not an existing feature.
- Roles, stored user lists, refresh tokens, webhook, and connector permissions live outside source; restore/check separately.
- The original screenshots, full transcript, every attachment, and hidden/compacted context cannot be reconstructed from this curated document. Export the conversation and retain original assets separately.
- A fresh model/session may reason or respond differently even with the same files. The objective is preserved requirements and verifiable state, not identical internal memory.
