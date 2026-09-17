---
name: debug-distributed-systems
description: >-
  Use when an incident spans more than one service, when a request fails
  inconsistently, or when the user asks for "trace the request", "find
  the slow hop", or "correlate the logs". Applies when the system under
  investigation uses trace IDs, OpenTelemetry, or any cross-service
  correlation header. Do not use for single-process bugs (use a
  language-specific debugger), or for client-side rendering issues.
skill_type: specialist
domain_focus: observability
tags:
  - distributed
  - tracing
  - observability
  - debugging
  - otel
  - microservices
version: 1.0.0
version_notes: Initial reference covering trace IDs, span trees, and log correlation.
token_budget: 1600
---

## When to use

Use when a single user-visible failure touches multiple services and the
on-call engineer cannot reproduce it locally. The diagnostic discipline
is the same regardless of stack:

1. **Anchor on a trace ID.** Every request has one. Pull the slowest
   trace from the APM, not the most recent one — slowest traces
   concentrate the bug.
2. **Read the span tree top-down.** Identify the longest critical-path
   span first; that is the dominant contributor to latency.
3. **Correlate logs to the trace.** Use the trace ID as the join key.
   Filter logs to that trace before reading any individual log line.
4. **Form and test one hypothesis at a time.** "Service B is slow because
   connection pool exhausted" is testable; "something is weird" is not.
5. **Capture the timeline before patching.** Note wall-clock times,
   deploy IDs, and config changes so the post-incident write-up has
   evidence.

## Examples

For example, a trace tree where the user-facing latency is 4.2 s but
the server-side work only sums to 800 ms:

```text
api-gateway              4200ms
└─ auth-service             45ms
   └─ orders-service      4150ms  ← critical path
      ├─ db.query          780ms
      ├─ inventory.client  3300ms  ← suspicious
      │  └─ http.GET        3295ms
      └─ payments.client     60ms
```

The hypothesis to test: the inventory service is waiting on a connection
to a downstream dependency that itself timed out. Pulling the inventory
service's logs for that trace ID should show either a `connect timeout`
or a thread-pool wait.

A log filter that joins logs by trace ID (Datadog example):

```text
service:inventory @http.status_code:500 @trace_id:abc123
```

## Pitfalls to avoid

- Do not start reading logs without first anchoring on a trace; unfiltered
  logs drown the signal and tempt you to invent a story that fits the
  noise.
- Do not assume wall-clock order reflects causal order; a request can
  fan out and rejoin, and the span tree is the only faithful record.
- Do not trust a single trace in a flaky system; flaky bugs need
  statistical evidence. Pull 10–20 traces of the failing path before
  forming a hypothesis.
- Do not patch without first capturing the timeline; an unfixed bug is
  recoverable, an undocumented incident is not.
- Do not conflate "the trace shows X" with "X is the cause"; the span
  tree shows where time was spent, not why the time was spent. Read the
  logs and metrics for the *why*.