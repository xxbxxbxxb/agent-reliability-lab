# Learning Progress Ledger

This file is the repository-side source of truth for the guided implementation. Chat messages and reference implementations are supporting evidence, not completion records.

## Status vocabulary

- `NOT_STARTED`: the Task has not been implemented by the learner.
- `IN_PROGRESS`: the learner has started implementation, but the acceptance gate is incomplete.
- `REVIEW_CHANGES_REQUESTED`: code exists, but Review identified required changes.
- `READY_FOR_ACCEPTANCE`: implementation and tests are submitted; the learner still needs to explain the design and receive final acceptance.
- `COMPLETED`: implementation, tests, Review and understanding evidence are all present.

`REFERENCE_VERIFIED` describes a teacher/reference implementation only. It never changes `YOUR_PROGRESS`.

## Completion gate

A Task may advance only when all four learner-side checks are true:

- [ ] `IMPLEMENTED_BY_USER`: the learner wrote or materially repaired the implementation in the working repository.
- [ ] `TESTED`: the learner ran the relevant focused and full test commands and recorded the result.
- [ ] `REVIEWED`: Review findings are resolved, with the final diff or commit identified.
- [ ] `UNDERSTOOD`: the learner can explain the design, trade-offs and one independent variation.

Passing tests alone is not enough. A reference implementation, a green historical run, or a generated answer is not learner evidence.

## Current snapshot

| Phase | Task | Reference/repository state | Your progress | Gate |
| --- | --- | --- | --- | --- |
| Phase 1A | Task 1 — project skeleton | Commit `63d63f0`; package import and version tests pass | `COMPLETED` based on the prior accepted Review | Complete |
| Phase 1A | Task 2 — domain models and TraceSink | Commit `b7776ea`; 3 Task 2 tests and full `5 passed` run | `REVIEW_CHANGES_REQUESTED` based on the latest recorded Review; revalidate in this checkout | Blocked until fixes and explanation |
| Phase 1A | Task 3 — Run/Step lifecycle | Not started | `NOT_STARTED` | Do not begin yet |

## Task 2 acceptance checklist

- [ ] Rename `Run.stared_at` to `started_at` and add the approved Run fields.
- [ ] Rename `TraceEvent.occured_at` to `occurred_at`.
- [ ] Add a test proving two Runs do not share `metadata`.
- [ ] Add tests for UTC-aware event timestamps and model serialization.
- [ ] Run the focused Task 2 tests.
- [ ] Run the full test suite.
- [ ] Submit the diff for Review.
- [ ] Explain why Step and TraceEvent are separate, why TraceSink is a Protocol, why Failure is structured, and why timestamps are UTC-aware.
- [ ] Complete one small independent variation without copying the reference test.

Until these boxes are checked and accepted, Task 3 remains `NOT_STARTED`.

## Evidence log

| Date | Evidence | Interpretation |
| --- | --- | --- |
| 2026-09-26 | Commits `ae8cd23` and `63d63f0`; package tests passed | Task 1 repository baseline |
| 2026-09-29 | Commit `b7776ea update0929`; full suite reported `5 passed` | Task 2 code exists, but green tests do not cover the Review issues |
| 2026-09-30 | Pulled `origin/main`; current `main` matches `origin/main` | Repository is synchronized; learning gate is still open |

## Next action

Work only on Task 2 until its checklist is complete. After each session, update this file with the commit, focused test result, full test result, Review status and the learner's own explanation. Do not change the Task 3 row early.
