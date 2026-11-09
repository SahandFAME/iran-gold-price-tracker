# State, verification and known limitations

Snapshot prepared 2026-11-08, Asia/Tehran. This is a development handoff, not a new end-to-end production health certification.

## Verified resource metadata

- Source HEAD: `273fe7d64127a6205d098360d7ccade8fa2498ef`, branch `work`.
- Vercel exact project read: existing production deployment `dpl_2wZEsgwQWUcnVJu8f1HQYR3isTLs` READY; production aliases still present. Same deployment as the November 2 repair.
- OneDrive metadata read on November 8: file last modified `2026-11-08T17:39:00Z` (21:09 Tehran), eTag `"{DE344AE1-4E91-4953-97B3-44C5C8BBDBE4},24"`, size 6,724,754 bytes, SHA-256 `a226f697f3f7a93b75c1736117222db2058b542f1a71ada30ebed05c5cc4d880`.
- The archive's `backups/` directory holds the raw workbook snapshot downloaded in this session. `verification/WORKBOOK_INSPECTION.json` records offline inspection; `verification/TEST_RESULTS.txt` records the new test run. Do not confuse file modification time with download time.
- Offline inspection of that snapshot: latest date 2026-11-08, row 4019; no gaps in the last 14 calendar dates or duplicate populated dates; all six charts present. Cached calculations agree with the implemented formulas to floating-point rounding (maximum observed absolute difference approximately 0.0000000485 toman). VBA SHA-256 is still `db0cb50f67b4ac80f1afe1e8e535b42821c8798bf636d128c5f7dae67e15d20f`, identical to the November 2 checkpoint. These checks do not independently establish TGJU source-price accuracy.
- The handoff, documentation policy, and maintainer tools are versioned in the repository after the documentation commit that added them. Their presence in a checkout is not evidence of a newer production deployment.

No latest-week independent TGJU comparison, live Telegram interaction, secret/vault backup, Blob-state export, scheduler invocation or new production release is claimed by this handoff. The workbook timestamp is consistent with scheduled writes, but correctness requires price-by-price validation.

## Important implementation limits visible in source

These are maintenance considerations, not newly implemented fixes or approved feature changes:

1. **Workbook template coupling.** The updater assumes sheet1, exact existing shared-formula IDs, numeric chart references, compatible XML formatting and pre-existing placeholder worksheet rows for appends. It raises `Missing worksheet row` if no future placeholder exists. It is not an arbitrary-workbook engine and cannot append indefinitely without verifying template capacity.
2. **Historical source completeness.** Empty source observations preserve existing history, but a partial non-empty response can cause missing existing observations after the first observed date to be treated as carry-forward. The current code has no completeness/provenance marker to distinguish a holiday from a truncated source response. Validate coverage before a broad repair.
3. **Retry scope.** TGJU handles selected network/timeouts, 429 and server failures as temporary outages. Other HTTP failures and malformed JSON/data can raise ordinary exceptions and fail the cron instead of carrying forward. The owner's broad fallback requirement is wider than all currently handled error paths.
4. **Reconciliation boundary.** The repair window is measured from the workbook's previous latest date, and correction starts at the first observed existing date inside that window. Missing observations before that anchor are not recomputed. Corrections older than the configured window may need an explicit historical repair.
5. **Existing date gaps.** The updater appends after the latest date; it does not reconstruct arbitrary missing rows inside previously populated history. Check sequence continuity separately.
6. **Chart shapes.** All six charts end at the latest row, but some original chart ranges have different start rows and potentially different category/value lengths. Extending them preserves those starts; matching end rows alone does not establish that every chart pairing is ideal. Inspect the actual source template before changing it.
7. **Blob concurrency.** User/session/profile records use whole-object overwrites without application-level transactions/CAS. Concurrent webhook requests can race; there is no durable update-ID deduplication or global queue in this source. Do not promise exactly-once approvals/messages.
8. **Token refresh concurrency.** OAuth token refresh and encrypted token-object writes are not protected by a distributed lock. Diagnose refresh races before rotating grants or keys.
9. **Observability.** No persistent per-run cron audit store or autonomous alerting was added. Audit data is returned by the update function; platform logs have limited retention. A health endpoint only proves handler availability.
10. **Access model.** Admin controls are application role checks, not independent per-action delegated provider permissions. Root administrator is restored from configured numeric ID on user ensure. Use the existing checks and tests when modifying callbacks.
11. **Private chat scope.** Normal message handling requires private chats. Do not assume Telegram group/channel support is implemented.
12. **Profile operations.** Setup and `/start` can synchronize branding by profile-version marker; changing version or restoring an empty store can trigger provider profile calls. Recreating state is not a harmless health check.
13. **External SDK/runtime.** Project-bound Vercel Connect/OIDC is part of runtime behavior. Local Python execution with source alone does not reproduce that identity. Use supported authenticated dev/runtime setup or mocks.

## What a new assistant should do first

Read requirements and verify actual tools/accounts. Run offline inspector and tests. Explain the specific next owner-requested task and current evidence. Preserve working provider resources. Make implementation changes only in scope, verify them proportionately, and record the exact commit/deployment/data changes made. A model change does not justify rearchitecting this established application.

For any newly discovered gap, distinguish source-confirmed behavior, a reproduced fault and an unverified hypothesis. The historical November 1 incident remains partially unexplained even though one reconciliation weakness was fixed and the data corrected.
