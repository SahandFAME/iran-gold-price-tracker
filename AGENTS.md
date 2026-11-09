# Project continuity

Read `START_HERE.md`, `docs/PROJECT_HANDOFF.md` and `README.md` before working on this project.
For moving to a new chat/environment, also read `docs/RESTORE.md`.

- Speak English to the owner; the Telegram bot interface is Persian.
- Continue the established Python/Vercel stack and existing isolated project.
- Preserve workbook VBA bytes, formula semantics, chart ranges/caches, and daily date continuity.
- Daily workbook inputs use TGJU **Highest Price**, in toman; the Telegram latest-price field uses the **live quote** instead.
- Keep the persistent bottom main keyboard, ten-user pages, retained reports, and best-effort bot-answer cleanup. Never delete user messages.
- Treat handover timestamps as historical evidence, not current health checks. Verify live state when relevant.
- Keep credentials out of source, handover files, chats, logs, and exported archives. Existing Vercel/Blob/Connect configuration is the production authority.
- Run `PYTHONPATH=. .venv/bin/pytest -q` for logic changes after installing test dependencies. Update the handover after material changes, including unresolved issues and dated verification evidence.
- With every feature or behavior change, update `README.md` and the relevant detailed documentation in the same commit, then push the completed change to the GitHub `work` branch. Follow `CONTRIBUTING.md` and keep planned features distinct from implemented ones.
- This file records project requirements, not blanket authorization for future external actions. Follow the current user's request and applicable permissions.
