# Operations and development runbook

This runbook describes the established application, not a framework migration. All dates/times shown to the owner use Asia/Tehran.

## Read-only takeover acceptance

1. Read the handoff documents and inspect `git status`, branch and latest commits. The source baseline is `273fe7d`; included continuity files may be uncommitted overlays. Preserve other work.
2. Confirm exact Vercel team/project and production alias. Check deployment SHA/state and cron configuration. A READY deployment is build health, not daily source health.
3. Confirm workbook item ID, name, size, eTag and last modified time. Download raw XLSM bytes and inspect offline; keep the download as a dated backup.
4. Run `python tools/inspect_workbook.py <downloaded.xlsm> --days 14`. It emits recent rows, formula ranges, chart references, VBA/file hashes, ZIP integrity and cached calculation checks. It does not contact providers or modify the workbook.
5. For a daily-price health check, independently fetch TGJU history, select the high column, convert rial to toman, compare dates, and apply carry-forward to days absent from the source. Distinguish a truly missing observation from an incomplete/stale HTTP response. Log source availability and date coverage, without credentials.
6. Interpret today's expected row relative to 21:00 Tehran. A pre-run absence of today's row is normal. Recent logs, version history and price comparisons together are stronger evidence than a file timestamp alone.
7. Run the unit suite after setup. Confirm any missing access with a concrete read attempt. Do not trigger write/setup endpoints to prove access.

## Development setup

Python 3.12 was used in the prior environment. Create a virtual environment, install `requirements.txt` plus pytest, and run:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt pytest
PYTHONPATH=. .venv/bin/python -m pytest -q
```

Windows PowerShell equivalents after installing Python with the Windows timezone database available:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pytest tzdata
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe -m pytest -q
```

`tzdata` is a Windows setup aid, not a change to deployed requirements. Follow the environment's network/installation policy. No production secrets are needed for these tests.

Pinned application dependencies: cryptography 50.0.2, httpx 0.28.1, vercel-blob 0.5.0, vercel-connect 0.2.2. Re-check `requirements.txt` if source has changed. The snapshot test suite has 23 tests.

## API contract

| Route | Method | Authentication | Effect |
| --- | --- | --- | --- |
| `/api/health` | GET | No application auth; platform protection may apply | Returns `{"ok":true}`; no downstream checks |
| `/api/daily_update` | GET | Bearer `CRON_SECRET` or `SETUP_SECRET` | Reads source and writes XLSM if changed |
| `/api/oauth_device` | POST | Bearer `SETUP_SECRET` | Stores encrypted device state; returns owner login instructions |
| `/api/oauth_complete` | POST | Bearer `SETUP_SECRET` | Polls device auth and persists encrypted tokens |
| `/api/telegram_setup` | GET | Bearer `SETUP_SECRET` | Registers webhook/commands and synchronizes branding |
| `/api/telegram` | POST | Telegram secret header | Processes messages/callbacks and can modify bot/user state |

Cron success response is `{ok:true, ...audit}`. Audit contains `updated`, `last_date`, `last_row`, appended/carried/reconciled date lists, VBA hash, changed package parts, source eTag/name and source availability. Some keys only exist on changed output. Error responses return a type name, while logs may include provider detail. Never expose provider tokens, authorization headers or raw OAuth token responses when diagnosing.

The cron uses maxDuration 300 seconds; Telegram uses 60 seconds. Source retries can consume significant time; sequential Graph/source/Blob calls can exceed limits in degraded conditions. Check actual plan limits/settings before changing them.

## Source contracts

Historical HTTP query: `lang=fa`, `draw=1`, `start` offset, `length=200`, empty search, `order_col=timestamp`, `order_dir=desc`, `convert_to_ad=1` against the summary-table API. Parsed `data` rows use index 2 for high and index 6 for Gregorian date (`%Y/%m/%d`); commas removed and rial divided by 10. Pagination stops when cutoff reached or returned total exhausted. Headers include browser User-Agent, official history Referer and JSON Accept.

Live source fallback order: `https://call2.tgju.org/ajax.json`, then call3, then call1. Uses `current.geram18.p` (or top-level `geram18.p` if `current` absent). Divide rial by 10. This is the report's `آخرین قیمت`, not a daily workbook input. If all live sources fail, show unavailability rather than silently relabelling a historical high as current.

## Workbook modification contract

Main data sheet part: `xl/worksheets/sheet1.xml`; VBA: `xl/vbaProject.bin`; workbook calculation flags in `xl/workbook.xml`. Excel date epoch is 1899-12-30. Read positive dated D rows starting at row 7. Shared formula IDs: I=421, E=422, F=423, G=424, H=425, K=426, L=427. Preserve style IDs and original unrelated package parts.

Recalculate every affected row from the earliest change through the last row. Extend shared formula anchors and rebuild numeric chart references/caches. Force Excel full recalculation on load while supplying cached values for Telegram. ZIP integrity and VBA hash equality must pass before upload.

The production Graph uploader uses the source metadata eTag in `If-Match`. On a concurrent change, fetch the new bytes and recalculate rather than forcing overwrite. The SharePoint `update_file_exact` tool used in the historical manual repair did not expose an atomic `If-Match` parameter; checking metadata immediately before its use reduces but does not eliminate a race. Prefer the application's conditional Graph path for controlled writes when accessible.

Offline update command (writes only the specified local output, but contacts TGJU):

```bash
.venv/bin/python -m gold_updater.cli source.xlsm --output updated.xlsm --as-of 2026-11-08 --audit-file audit.json
```

Choose the date explicitly for a historical repair; do not reuse the example date as a future default. The inspector and audit identify changes; compare source/output ZIP parts and VBA hash before any live replacement.

## Deployment and rollback

Use the existing project/team and an exact reviewed commit. Git push did not automatically deploy this project during the last repair. Verify whether Git integration is now connected; avoid duplicate/manual deployments if it is.

The last successful API deployment used create-deployment with explicit team and this request shape (replace SHA with the intended full commit):

```json
{
  "name": "iran-gold-price-tracker",
  "project": "prj_LS44me3kkj8uFZIW9KrgRvL2omEQ",
  "target": "production",
  "gitSource": {
    "type": "github",
    "org": "SahandFAME",
    "repo": "iran-gold-price-tracker",
    "ref": "work",
    "sha": "<reviewed-full-commit-sha>"
  }
}
```

Equivalent CLI approach from another model: install an appropriate reviewed Vercel CLI version, authenticate to the owner's account, link explicitly to `iran-gold-price-tracker` in scope `sahand-r5-6417`, verify `.vercel/project.json` IDs, and deploy the reviewed checkout with production selected. Use `vercel ... --help` / current official docs for the installed version. Keep credentials in secure environment/CLI storage, not command arguments or committed files. Do not link by an ambiguous default team.

Watch build state until READY or failure. Verify intended SHA, production alias, read-only health and new runtime errors. A protected URL can require authenticated Vercel fetch or `vercel curl`; do not disable protection just to test. Vercel protection bypass does not satisfy the application's bearer auth on mutating routes.

Code rollback: select the previous known-good deployment from the same project and verify aliases after rollback. Workbook rollback: use a dated backup or OneDrive version history, preserving a copy of current data first. They are separate rollback operations: changing code does not undo data writes, and restoring an older file may reintroduce stale prices. Do not treat all old commits as safe production targets; some contain superseded navigation or temporary setup routes.

## Troubleshooting

| Symptom | Checks / response |
| --- | --- |
| Current input date stale | Tehran run time, cron schedule/route auth, function errors, Graph expiry/eTag, source coverage |
| Price wrong despite successful write | Compare TGJU high versus close/live; rial/toman factor; source-date mapping; carry-forward chain; stale/partial response |
| Graph refresh failure | Distinguish app OAuth from chat connector; inspect safe error code; owner device reauthorization when needed |
| Graph 412 / eTag conflict | Fetch current workbook again; recompute; never force stale overwrite |
| Fernet decryption failure | Confirm original matching key/store; do not regenerate key as a quick fix |
| Report works but is stale | Workbook snapshot age separately from live TGJU quote; successful quote does not update workbook |
| Bot stops after message deletion | Confirm deployed cleanup catches errors; callback acknowledgement best-effort; don't delete user messages |
| Bot never responds | Webhook URL/secret header, Telegram webhook errors, function logs, Connect credential/OIDC, approved status |
| Admin lacks menu | Numeric root ID versus username; persisted approval/role; current keyboard version |
| Add-by-username fails | User must be known to bot; use numeric ID or ask user to `/start` |
| HTTP 403 | Identify whether environment proxy, Vercel protection or application auth generated it; use authorized path |
| No old runtime logs | Retention may have expired; compare file versions and data rather than inventing a successful cron trace |

Avoid a fresh `/start` as a substitute for fixing cleanup crashes. Retain test coverage for existing roles, root protection, callbacks, paging, reports and best-effort cleanup when changing Telegram code.
