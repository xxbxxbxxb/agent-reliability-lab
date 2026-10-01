# Task Acceptance Template

Copy this file for each guided Task. Fill it with evidence from the current repository; do not mark a box because a reference implementation exists.

## Task identity

- Phase:
- Task:
- Scope:
- Current branch:
- Commit under review:

## Implementation evidence

- [ ] I wrote or materially repaired the implementation myself.
- Files changed:
- What behavior did I implement?
- What did I intentionally leave for the next Task?

## Test evidence

Focused command:

```text
<command>
```

Focused result:

```text
<result>
```

Full command:

```text
<command>
```

Full result:

```text
<result>
```

- [ ] I saw the expected failing test before the implementation when the Task uses TDD.
- [ ] I added the required independent variation.

## Review evidence

- Review status: `CHANGES_REQUESTED` / `READY_FOR_ACCEPTANCE` / `ACCEPTED`
- Findings:
- Fixes made:
- Review commit or diff:

## Understanding evidence

Answer in my own words:

1. What problem does this Task solve?
2. Why was this boundary or interface chosen?
3. What failure mode or edge case is still uncovered?
4. What independent variation did I implement, and what did it prove?

## Gate decision

- [ ] `IMPLEMENTED_BY_USER`
- [ ] `TESTED`
- [ ] `REVIEWED`
- [ ] `UNDERSTOOD`

Only after all four boxes are checked should the next Task be opened.
