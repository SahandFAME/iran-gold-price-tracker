# دیدبان طلا و سکه — start here

Portable handoff prepared 2026-11-08 (Asia/Tehran) for Codex, Claude Code, or another coding assistant.

If you only have a chat interface, upload **HANDOFF_COMPLETE.md** and **RESTART_PROMPT.md** from the generated package. If file limits permit, also provide the source ZIP. If you have a coding workspace, unpack the package and read this file, `AGENTS.md`, and the documents below. Claude Code can start with `CLAUDE.md`.

Read in this order:

1. `docs/PROJECT_HANDOFF.md`: identity, architecture, exact Persian requirements, resource IDs, state and access inventory.
2. `docs/HISTORY_AND_DECISIONS.md`: project evolution, rejected approaches, previous failures and open questions.
3. `docs/OPERATIONS.md`: setup, API contract, deployment, verification, incident response and rollback.
4. `docs/ACCESS_AND_RECOVERY.md`: equivalent access from any AI environment, secure credential recovery and external-state backup.
5. `docs/STATE_AND_LIMITATIONS.md`: dated verification and concrete technical limitations. Never mistake a documented limitation for a newly authorized feature request.
6. `docs/RESTORE.md` and `docs/RESUME_PROMPT.md`: practical restart instructions and first message.
7. `CONTRIBUTING.md`: mandatory code, test, documentation, and GitHub update workflow for every new feature.

Production: `https://iran-gold-price-tracker.vercel.app`.
Repository: `https://github.com/SahandFAME/iran-gold-price-tracker.git`, branch `work`.

The archive includes source, tests, avatar, an XLSM snapshot, generated checksums, and (when selected) Git history. Use `tools/inspect_workbook.py` for offline inspection without production access. Optional Git history is in `history/project-work.bundle`; the normal source tree does not require it to start.

This is a curated reconstruction of available conversation and repository history, not a verbatim chat export. Preserve an account export and original screenshots separately. Secrets, authentication grants, private Blob state and live provider resources are not copied by uploading this package. Reading it does not confer permissions. Retaining the existing external resources is the easiest way to continue.

The package's `SHA256SUMS.txt` covers its payload files. Validate those after extraction with `sha256sum -c SHA256SUMS.txt` on Linux or compare with `Get-FileHash -Algorithm SHA256` on Windows. All metadata is a dated snapshot; inspect actual live state before repairs or releases.
