# Didban Tala o Sekke — Iran Gold Workbook Updater and Telegram Bot

`دیدبان طلا و سکه` is a cloud-hosted system that maintains a macro-enabled Excel workbook with daily Iranian 18K gold prices and exposes its analytical values through a Persian Telegram bot.

The project combines TGJU market data, a personal OneDrive workbook, Microsoft Graph, Vercel Cron, encrypted Vercel Blob state, and a role-controlled Telegram interface. It runs without an always-on personal computer.

Production application: `https://iran-gold-price-tracker.vercel.app`

## What the project does

### Daily 18K gold workbook maintenance

- Reads TGJU's daily **Highest Price** for `geram18`.
- Converts TGJU's rial value to the workbook's toman unit by dividing by 10.
- Adds every Tehran calendar date to `اسناد/Geram18-tahlil-updated.xlsm`.
- Carries the last available price forward when TGJU has no observation for a date.
- Rechecks and reconciles the most recent 14 days on every run, exceeding the original previous-week requirement.
- Propagates corrected observations through later carry-forward dates.
- Recalculates the workbook's analytical columns and their cached values.
- Extends shared formula ranges and all six chart ranges/caches.
- Preserves the embedded VBA project byte-for-byte.
- Validates ZIP integrity and the VBA hash before upload.
- Uses the Microsoft Graph eTag with `If-Match` to avoid overwriting a concurrent workbook edit.
- Runs daily through Vercel Cron at 17:30 UTC, which is 21:00 Tehran.

The historical TGJU source is `https://api.tgju.org/v1/market/indicator/summary-table-data/geram18`. The official browser history page is `https://www.tgju.org/profile/geram18/history`.

### Persian Telegram reporting bot

- Persian display name, descriptions, introduction, commands, and branded avatar.
- Approval-only access: unapproved users cannot open reports.
- Two roles: `user` and `admin`.
- A protected numeric root administrator that cannot be demoted or removed through the bot.
- Every new access request notifies all approved administrators with Approve and Deny buttons.
- Approved and denied users receive the corresponding decision notification.
- Persistent Telegram bottom keyboard for the main menu.
- `📊 گزارش` for every approved user.
- `⚙️ داشبورد مدیریت` for administrators.
- Focused admin dashboard with approved-user and pending-request counts.
- User management: approve, deny, promote, demote, remove, reactivate, and add by numeric ID or a username already known to the bot.
- Numbered user lists with 10 accounts per page, role/status labels, action buttons, and page navigation.
- User messages are never deleted.
- Only the preceding transient bot answer is removed when a new menu/admin answer is sent.
- Cleanup is best-effort, so a bot message already deleted by the user does not stop the next response.
- Reports are retained in Telegram as report history.
- Returning to `منوی اصلی` shows a compact menu instead of repeating the full welcome message.

The bot handles private chats. A username can be used for member management only after the bot has previously learned it; otherwise the administrator can use the user's numeric Telegram ID or ask the user to send `/start`.

## Telegram report contents

The report intentionally combines two independent sources:

1. TGJU's live 18K quote for `آخرین قیمت`.
2. The latest cached analytical row in the Excel workbook.

If the live quote is unavailable, the bot says so instead of silently presenting a historical value as current.

| Workbook column | Persian label | Meaning shown to users |
| --- | --- | --- |
| E | قیمت آربیتراژی | خرید چشم بسته که معمولاً در صورت دیده شدن بسیار کوتاه مدت خواهد بود |
| F | قیمت تعادلی جاری | قیمت منصفانه فعلی |
| G | کران محاسباتی بالا | قیمتی که حباب خیلی بالا است و ارزش خرید در مقطع کنونی ندارد |
| I | کف محاسباتی | پایین ترین قیمتی که در مقطع کنونی میتوان متصور شد |
| L | قیمت حرکت چرخه ای | قیمتی که معمولاً در صورت دیده شدن از همانجا یا کمی پایینتر قیمت برمیگردد |

The report omits the old `محاسبات فایل اکسل` heading, `ارزش حدودی مقطعی`, and the 85-day moving average. Values are formatted in Persian digits and toman. The report includes a short analytical disclaimer.

## Workbook calculations

The project preserves and refreshes the workbook's established calculation model:

| Column | Calculation |
| --- | --- |
| C | Excel calendar date |
| D | Daily TGJU Highest Price in toman |
| E | 240-row average of D |
| I | 370-row average of D |
| F | I × 1.3 |
| G | I × 1.6 |
| H | I × 1.1 |
| K | 85-row average of D |
| L | 65-row average of D |

Columns H and K remain part of the workbook and charts but are not displayed in the current Telegram report.

## System flow

```text
Vercel Cron (21:00 Tehran)
        |
        v
TGJU history -----> daily highs + 14-day reconciliation
        |                         |
        |                         v
        |                macro-enabled XLSM updater
        |                         |
        |                         v
        +----------------> Microsoft Graph / OneDrive
                                  |
                                  v
                     formulas, cached values, charts, VBA

Telegram user -----> signed webhook -----> approval and role checks
                                              |
                         +--------------------+--------------------+
                         |                                         |
                         v                                         v
                   TGJU live quote                      latest workbook row
                         |                                         |
                         +--------------------+--------------------+
                                              v
                                      Persian analytical report
```

## Architecture and source layout

| Path | Responsibility |
| --- | --- |
| `api/daily_update.py` | Authenticated Vercel Cron handler |
| `api/telegram.py` | Telegram webhook and secret-header validation |
| `api/telegram_setup.py` | Protected webhook, commands, and profile synchronization |
| `api/oauth_device.py` | Starts Microsoft personal-account device authorization |
| `api/oauth_complete.py` | Completes authorization and stores encrypted tokens |
| `api/health.py` | Lightweight application health response |
| `gold_updater/tgju.py` | TGJU historical-high and live-quote clients |
| `gold_updater/workbook.py` | OOXML/XLSM formulas, cached values, charts, and VBA-safe updates |
| `gold_updater/service.py` | End-to-end Graph download, reconciliation, and conditional upload |
| `gold_updater/microsoft.py` | Microsoft device OAuth and encrypted token refresh |
| `gold_updater/report.py` | Live quote plus latest workbook snapshot |
| `gold_updater/telegram_bot.py` | Persian menus, approval workflow, roles, reports, and pagination |
| `gold_updater/telegram_store.py` | Encrypted user records, audit events, and interaction state |
| `gold_updater/telegram_api.py` | Telegram Bot API using a project-bound Vercel Connect token |
| `gold_updater/telegram_profile.py` | Versioned Persian branding and approved avatar |
| `gold_updater/cli.py` | Controlled local workbook update command |
| `tools/inspect_workbook.py` | Read-only offline XLSM integrity and calculation inspection |
| `tools/build_handoff.py` | Portable project handoff package builder |
| `vercel.json` | Function limits and daily cron schedule |

## Security and data protection

- The Microsoft app supports personal Microsoft accounts and uses OAuth device authorization.
- No Microsoft client secret is required by the current implementation.
- Microsoft access/refresh tokens and temporary device state are encrypted with Fernet before storage in a private Blob store.
- Telegram user records, role state, audit events, and profile synchronization state are also encrypted before Blob storage.
- The Telegram BotFather token is held by Vercel Connect and requested at runtime with the deployment's project OIDC identity.
- The bot token is not stored in source or a normal project environment variable.
- HTTPX INFO logging is disabled for Telegram requests because Bot API URLs contain the token.
- Telegram webhook calls must contain the configured Telegram secret header.
- Cron and setup endpoints require bearer authentication.
- Workbook uploads use an eTag to prevent stale overwrites.
- Secrets, populated `.env` files, private Blob state, and tokens must never be committed.

## Required production configuration

Configure actual values securely in Vercel. `.env.example` contains names only.

| Variable | Purpose |
| --- | --- |
| `MS_CLIENT_ID` | Personal Microsoft application ID |
| `GRAPH_DRIVE_ID` | Exact OneDrive drive containing the workbook |
| `GRAPH_ITEM_ID` | Exact XLSM drive item |
| `TOKEN_ENCRYPTION_KEY` | Fernet key for encrypted Microsoft and Telegram state |
| `BLOB_READ_WRITE_TOKEN` | Private Vercel Blob access |
| `SETUP_SECRET` | Protects setup and authorization routes |
| `CRON_SECRET` | Protects the daily cron route |
| `TELEGRAM_CONNECTOR` | Existing Vercel Connect Telegram connection |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram webhook verification secret |
| `TELEGRAM_ADMIN_ID` | Protected numeric root administrator |

`TOKEN_ENCRYPTION_KEY` must be preserved together with the encrypted Blob data. Replacing the key without migrating the data makes stored tokens and users unreadable.

## API routes

| Route | Method | Protection | Effect |
| --- | --- | --- | --- |
| `/api/health` | GET | Vercel deployment protection may apply | Returns `{"ok": true}` only |
| `/api/daily_update` | GET | `CRON_SECRET` or `SETUP_SECRET` bearer | Fetches prices and may write the workbook |
| `/api/oauth_device` | POST | `SETUP_SECRET` bearer | Starts Microsoft device authorization |
| `/api/oauth_complete` | POST | `SETUP_SECRET` bearer | Completes authorization and stores tokens |
| `/api/telegram_setup` | GET | `SETUP_SECRET` bearer | Registers webhook/commands and syncs profile |
| `/api/telegram` | POST | Telegram secret header | Processes private messages and callbacks |

`/api/daily_update` and `/api/telegram_setup` mutate live state. Do not use them as read-only connectivity tests.

## Local development

Python 3.12 was used for the current project.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
PYTHONPATH=. .venv/bin/python -m pytest -q
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest tzdata
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m pytest -q
```

The current suite contains 23 tests covering workbook updates, VBA preservation, formula/chart extension, source outage behavior, reconciled carry-forward rows, TGJU retry behavior, bot profile synchronization, roles, reports, menus, pagination, and cleanup failures.

Inspect a downloaded workbook without contacting providers or modifying it:

```bash
.venv/bin/python tools/inspect_workbook.py Geram18-tahlil-updated.xlsm --days 14
```

Run a controlled local update into a separate output file:

```bash
.venv/bin/python -m gold_updater.cli source.xlsm \
  --output updated.xlsm \
  --as-of 2026-11-08 \
  --audit-file audit.json
```

Choose the correct date for the intended repair; the example date is historical. Compare the audit, ZIP parts, VBA hash, formulas, and charts before replacing any live file.

## Deployment and operations

- Reuse the existing isolated Vercel project; do not deploy this application into unrelated projects.
- Deploy an exact reviewed commit from branch `work`.
- Verify the deployed commit, production alias, health response, and recent runtime errors.
- Verify actual workbook rows against TGJU history when assessing price correctness. A READY deployment, HTTP 200, or updated file timestamp is not sufficient evidence.
- Interpret today's workbook row relative to the 21:00 Tehran schedule.
- On a Graph eTag conflict, download the latest workbook and recompute instead of forcing an overwrite.
- Code rollback and workbook rollback are separate operations.

The detailed production runbook is in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Current limitations

- Only 18K gold is implemented. Bahar Azadi and Emami coins are planned future additions.
- The XLSM updater is coupled to the current workbook template, worksheet, shared formula IDs, placeholder rows, and chart structure.
- A partially returned TGJU history response can be difficult to distinguish from dates with no observation; broad repairs require source-coverage validation.
- No persistent per-run cron journal or autonomous failure alerting has been added.
- Telegram state uses encrypted whole-object Blob writes and does not provide exactly-once processing across concurrent webhook invocations.
- Normal Telegram interaction is designed for private chats.
- A username cannot be resolved if the bot has never seen that user.

See [docs/STATE_AND_LIMITATIONS.md](docs/STATE_AND_LIMITATIONS.md) for the complete technical list.

## Documentation map

| Document | Purpose |
| --- | --- |
| [START_HERE.md](START_HERE.md) | Entry point for a new maintainer or coding assistant |
| [docs/PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md) | Project identity, exact resources, accepted requirements, and verified history |
| [docs/HISTORY_AND_DECISIONS.md](docs/HISTORY_AND_DECISIONS.md) | Feature evolution and reasons behind the current design |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Setup, deployment, verification, rollback, and troubleshooting |
| [docs/ACCESS_AND_RECOVERY.md](docs/ACCESS_AND_RECOVERY.md) | Cross-platform access and disaster-recovery planning |
| [docs/STATE_AND_LIMITATIONS.md](docs/STATE_AND_LIMITATIONS.md) | Dated evidence and known technical constraints |
| [docs/RESTORE.md](docs/RESTORE.md) | Continue in Codex, Claude Code, or another assistant |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Required workflow for code, tests, and documentation updates |

## Documentation policy

Every feature change must update the repository documentation in the same commit:

- update this README when user-visible capabilities, setup, behavior, security, or limitations change;
- update the detailed runbook or handoff document when architecture, providers, resource requirements, recovery, or operations change;
- update tests for meaningful behavior changes;
- state explicitly when a capability is planned rather than implemented;
- never document a successful production release or verification that did not actually occur.

This policy keeps GitHub understandable to a new maintainer without requiring access to the original development chat.
