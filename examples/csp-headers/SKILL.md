---
name: csp-headers
description: >-
  Use when designing or hardening a Content-Security-Policy header for
  an HTTP application. Applies when the user asks for "CSP", "Content
  Security Policy", "nonce-based CSP", "strict-dynamic", or "XSS
  hardening headers". Do not use for non-web platforms (native, mobile),
  for CORS configuration (use a CORS skill), or for setting CSP via a
  managed WAF without owning the header value.
skill_type: specialist
domain_focus: security
tags:
  - csp
  - content-security-policy
  - security
  - headers
  - http
  - xss
version: 1.0.0
version_notes: Gallery reference for nonce-based and strict-dynamic CSP policies.
token_budget: 1500
---

## When to use

Use when the application serves HTML over HTTP and you want to defend
against XSS by instructing the browser to refuse to load script, style,
or frame content from unauthorised sources. CSP is the second line of
defence after output encoding; it does not replace sanitisation.

The policy is a single HTTP response header whose value is a list of
*directives*. Each directive constrains one fetch target. The browser
applies the most restrictive directive that matches the fetch.

| Directive             | Restricts                          |
|-----------------------|------------------------------------|
| `default-src`         | everything not otherwise specified |
| `script-src`          | JavaScript sources                 |
| `style-src`           | Stylesheet sources                 |
| `img-src`             | Image sources                      |
| `connect-src`         | XHR, fetch, WebSocket, EventSource |
| `frame-src`           | `<iframe>` sources                 |
| `font-src`            | Font files                         |
| `object-src`          | `<object>`, `<embed>`, `<applet>` |
| `base-uri`            | Allowed values for `<base>`        |
| `form-action`         | Form submission targets            |
| `frame-ancestors`     | Who can frame this page            |

## Examples

A strict policy that allows only first-party scripts (no inline, no
eval, no third-party CDNs):

```http
Content-Security-Policy:
  default-src 'none';
  script-src 'self';
  style-src 'self';
  img-src 'self' data:;
  connect-src 'self';
  frame-ancestors 'none';
  base-uri 'none';
  form-action 'self';
```

A nonce-based policy for an app that must run inline scripts (typical
for SSR frameworks like Rails or Django):

```http
Content-Security-Policy:
  script-src 'nonce-{request-scoped-nonce}' 'strict-dynamic';
  object-src 'none';
  base-uri 'none';
```

The server generates a fresh base64 nonce per request, attaches it to
every `<script>` tag, and includes the same value in the CSP header.
`strict-dynamic` tells the browser to trust scripts loaded by the
nonce-bearing script, which lets you stop maintaining a hash list.

For example, rolling the policy out safely using `Content-Security-Policy-Report-Only`:

```http
Content-Security-Policy-Report-Only: default-src 'self'; report-uri /csp-report
```

The browser enforces nothing but sends violation reports to `/csp-report`.
After a week of clean reports, switch to the enforcing header.

## Pitfalls to avoid

- Do not allow `'unsafe-inline'` or `'unsafe-eval'` in `script-src`; both
  defeat the purpose of CSP. If you need inline scripts, switch to
  nonces or hashes.
- Do not omit `object-src`; legacy Flash / PDF plugins can re-introduce
  script execution that bypasses `script-src`.
- Do not set `frame-ancestors 'none'` until you are sure no legitimate
  partner frames your site; it replaces the deprecated `X-Frame-Options`
  header and is silently ignored by older browsers.
- Do not ship a CSP without `default-src`; missing directives fall back
  to `default-src`, so a sparse policy that omits `default-src` is
  effectively `default-src *`.
- Do not paste a CSP from a public generator without auditing every
  source; the generated value is often `*` and should never reach
  production.