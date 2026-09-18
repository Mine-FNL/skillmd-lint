---
name: api-error-response-format
description: >-
  Use when designing or implementing an HTTP API's error response shape,
  when reviewing a PR that adds a new error path, or when a client SDK
  needs to consume errors. Triggers: "how should we return errors",
  "what's the JSON error schema", "this 500 leaked a stack trace", "the
  error structure is inconsistent". Do not use for logging-format
  questions, exception handling inside the service, or for non-HTTP
  protocols (gRPC, message queues).
skill_type: domain-expert
domain_focus: api-design
tags:
  - api
  - errors
  - http
  - rest
  - json
  - sdk
version: 1.0.0
version_notes: Gallery API-design skill. Locks a four-field error envelope and enumerates what goes in each slot.
token_budget: 1300
---

## When to use

Use at the start of any HTTP API design, when adding a new error path
to an existing endpoint, when reviewing an error-handling change, or
when authoring the client-side error parser.

Apply the four-field envelope below to every error response, including
auth failures, validation failures, downstream-dependency failures, and
internal errors. Consistency across the surface matters more than the
specifics of any single endpoint.

If you are inheriting an existing API with a different shape, this
skill gives you the target. Migrate endpoint by endpoint; do not mix
shapes inside a single endpoint.

## Examples

The canonical error envelope:

```json
{
  "error": {
    "code": "user_not_found",
    "message": "No user exists with the given ID.",
    "details": {
      "user_id": "u_12345",
      "trace_id": "01J7X9K2E5RQZT8M3P6VFYBNC0"
    },
    "retryable": false
  }
}
```

Four fields, no others:

- **code** — stable, machine-readable, snake_case. The client SDK
  switches on this. Never localised, never changed without a major
  version bump.
- **message** — human-readable, English. May be shown to the end user.
  Localisation is the client's job.
- **details** — structured context. Field names, IDs, trace IDs.
  Optional but always present as `{}` if empty.
- **retryable** — boolean. `true` for transient failures (503, 429,
  upstream timeout). `false` for permanent failures (400, 401, 404,
  422). The SDK uses this to decide whether to retry automatically.

For example, a 401 Unauthorized response:

```json
{
  "error": {
    "code": "auth_token_expired",
    "message": "The session token has expired.",
    "details": { "expired_at": "2024-09-18T03:14:15Z" },
    "retryable": false
  }
}
```

For example, a 503 Service Unavailable response:

```json
{
  "error": {
    "code": "upstream_timeout",
    "message": "The downstream service did not respond in time.",
    "details": {
      "upstream": "billing-api",
      "trace_id": "01J7X9K2E5RQZT8M3P6VFYBNC0"
    },
    "retryable": true
  }
}
```

## Pitfalls to avoid

- **Do not** leak stack traces, query text, or file paths in `message`.
  These are developer-facing diagnostics and they tell attackers where
  the seams are. Move them to logs.
- **Do not** change `code` values without a major version bump. Clients
  pin on this string; renaming it silently breaks every deployed SDK.
- **Do not** invent a new error envelope for a new endpoint. Use the
  same four fields every time, with `details` carrying the endpoint-
  specific context.
- **Do not** put the reason for a 4xx in the HTTP reason phrase alone.
  Reason phrases are not parsed by clients; only the body is. The body
  is the contract.
- **Do not** return 200 OK with an error body. It breaks every cache,
  every proxy, every monitoring rule that assumes status code semantics.
  Pick a 4xx or 5xx status that matches.
- **Do not** return a different shape for 5xx than for 4xx. Internal
  errors deserve the same structured envelope so the SDK can switch on
  `code` uniformly.
- **Do not** omit `retryable`. The default behavior on the client side
  is "do not retry", but that default is wrong for transient failures.
  Make the server say so explicitly.
- **Do not** include `details` from another tenant. Multi-tenant APIs
  must scrub the details object to only fields the caller is authorised
  to see.
