# Complete handoff package contents

Prepared 2026-11-08. Keep the archive private: it includes the owner's workbook, project details and identifiers.

## Included

- Full current source, tests and approved avatar, based on commit `273fe7d64127a6205d098360d7ccade8fa2498ef`.
- Local handoff overlays: `START_HERE.md`, `AGENTS.md`, `CLAUDE.md`, `.env.example`, detailed `docs/` and portable `tools/`.
- `HANDOFF_COMPLETE.md`: complete combined project context for chat-only models; source is included separately rather than pasted into it.
- `RESTART_PROMPT.md`: first message for any model.
- `history/COMMITS.txt`: committed development chronology.
- `history/project-work.bundle` when history export selected: offline recoverable Git history for branch `work`.
- `backups/Geram18-tahlil-updated.xlsm`: raw OneDrive snapshot downloaded 2026-11-08, provider last modified 2026-11-08 17:39:00 UTC / 21:09:00 Tehran, 6,724,754 bytes.
- `verification/WORKBOOK_INSPECTION.json`: offline inspection, recent rows, cached-calculation checks, formula/chart references and hashes.
- `verification/TEST_RESULTS.txt`: test suite results at packaging.
- `verification/SECRET_PATTERN_SCAN.json`: bounded common-format scan of selected history/source, with no credential values printed. This is not a comprehensive secret audit.
- `verification/PACKAGE_MANIFEST.json`: baseline, local overlays and payload-file hashes.
- `SHA256SUMS.txt`: checksums covering archive payload files.

Workbook snapshot SHA-256: `a226f697f3f7a93b75c1736117222db2058b542f1a71ada30ebed05c5cc4d880`.

## Not included

- Full original conversation export, inaccessible/compacted exchanges, original screenshot attachments or account memories (export and retain separately).
- Environment variables/secret values, credentials, provider sessions or Vercel Connect bot token.
- Private Blob contents: Microsoft token, user approvals/roles, admin events and profile marker.
- A live runtime, installed packages, or inherited account permissions.

This archive is usable as a source/context/history backup, not a complete disaster-recovery image of external services. Source overlays are included as files even if not committed or pushed. Preserve provider accounts and encrypted-state/key backups described in `ACCESS_AND_RECOVERY.md` separately. The snapshot is not to be uploaded over the live workbook just to resume development.

Download the archive outside the old chat/workspace now. Do not rely on its workspace path or this chat's download link remaining available after deletion.

Rebuild after updating dated context and capturing a fresh workbook:

```bash
.venv/bin/python tools/build_handoff.py --workbook /path/to/snapshot.xlsm --output-dir /path/to/new-output-directory --include-history
```

The builder refuses an existing archive path, scans selected source/history for common credential formats, runs the unit suite, inspects the workbook, creates a combined context and verifies ZIP checksums. Its package date/name is specific to this handoff; update that and the dated documents for a future release. It never requests provider credentials or private Blob data.
