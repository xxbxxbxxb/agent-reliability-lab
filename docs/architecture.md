# Architecture

## Purpose and boundary

Agent Reliability Lab focuses on the execution boundary around a tool-using Agent. The Agent chooses what to do; the Reliability Runtime records, constrains and evaluates how that execution proceeds.

The current repository contains the domain vocabulary and an in-memory trace adapter. It does not yet contain a working Runtime, fault injector, recovery engine or benchmark harness.

## Core vocabulary

| Term | Meaning | Relationship |
| --- | --- | --- |
| Run | One complete Agent execution for one task | A Run contains many Steps and TraceEvents |
| Step | One logical operation inside a Run | A Step may produce many TraceEvents |
| TraceEvent | A time-ordered fact observed during execution | May point to a Run and optionally a Step |
| Failure | A classified failure attached to a Run and Step | Provides structured input to Recovery |
| RecoveryAttempt | One attempt to respond to a Failure | Points back to the Failure it addresses |
| TraceSink | Capability for recording a TraceEvent | Runtime depends on the Port, not storage details |

The distinction between `Step` and `TraceEvent` is deliberate: the Step is the logical operation, while events describe what happened while that operation ran.

## Planned data flow

```text
Agent / caller
     ↓ task
Runtime
     ├── Run lifecycle
     ├── Step executor
     ├── Fault injector
     ├── Recovery policy
     └── Idempotency guard
          ↓ events
       TraceSink (Port)
          ├── InMemoryTraceSink (tests)
          ├── PersistentTraceSink (planned)
          └── OpenTelemetryTraceSink (planned)
```

## Design decisions

1. **Domain objects are separate from trace facts.** This keeps execution history queryable and makes retries, recovery and replay observable.
2. **Trace storage is a Port.** Runtime code should only require `emit(event)`, allowing memory, database and telemetry adapters to be swapped.
3. **Internal timestamps are UTC-aware.** Cross-machine ordering must not depend on a local timezone.
4. **The first evaluation path is deterministic.** Faults and tools should be fakes with controlled outcomes before external services are introduced.

## Reliability evidence

Every later feature should answer three questions:

1. What failure or uncertainty does it handle?
2. What TraceEvents prove that it handled it?
3. Which metric changes when it is enabled compared with the baseline?

If a feature cannot answer those questions, it is infrastructure work without a reliability experiment yet.
