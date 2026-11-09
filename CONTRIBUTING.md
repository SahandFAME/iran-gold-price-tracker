# Contributing and feature documentation policy

Every feature, fix, or operational change must leave the repository understandable to someone who has never seen the development conversation.

## Required workflow

1. Read `START_HERE.md`, `README.md`, and the relevant files under `docs/`.
2. Preserve the established Python/Vercel architecture unless the requested work explicitly changes it.
3. Implement the smallest complete change and add meaningful regression coverage for behavior that could fail again.
4. Run `PYTHONPATH=. .venv/bin/pytest -q` and any focused verification appropriate to the change.
5. Update documentation in the same commit as the implementation.
6. Commit and push the exact reviewed source to branch `work`.
7. Deploy only when the task authorizes production release; document the actual deployment and verification result.

## Documentation required with each change

| Change | Documentation to update |
| --- | --- |
| User-visible feature or bot behavior | `README.md`, feature/history details, exact Persian text when relevant |
| Workbook formula, column, chart, or source behavior | `README.md`, `docs/PROJECT_HANDOFF.md`, `docs/OPERATIONS.md`, tests |
| New provider, credential, environment variable, or permission | `.env.example`, README configuration table, access/recovery docs |
| Deployment, cron, route, or operational behavior | README routes/operations and `docs/OPERATIONS.md` |
| Security or data-storage behavior | README security section and `docs/ACCESS_AND_RECOVERY.md` |
| Known limitation discovered or resolved | README limitations and `docs/STATE_AND_LIMITATIONS.md` |
| Material incident or production repair | Dated evidence in project handoff/state docs without secrets |

Do not mark roadmap ideas as implemented. Do not copy credentials, private user data, access tokens, populated environment files, cookies, or raw OAuth responses into source, issues, commits, logs, or documentation.

## Pull request / commit checklist

- [ ] The feature or fix is complete for the requested scope.
- [ ] Tests and focused verification pass.
- [ ] README feature list and behavior are current.
- [ ] Architecture/operations/recovery docs are current where applicable.
- [ ] Exact Persian bot copy is documented when changed.
- [ ] New variables appear in `.env.example` with blank values.
- [ ] Planned and implemented features are clearly distinguished.
- [ ] No credentials or private user data are included.
- [ ] Production claims identify the actual commit/deployment and evidence.
