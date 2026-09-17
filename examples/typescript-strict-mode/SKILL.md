---
name: typescript-strict-mode
description: >-
  Use when migrating a JavaScript codebase to TypeScript with strict mode,
  or when tightening `tsconfig.json` after a migration has plateaued.
  Applies when the user asks for "enable strict", "noImplicitAny",
  "strict null checks", or "fix the type errors". Do not use for adding
  TypeScript to a brand-new project with no existing JS (start with
  `tsc --init` and a permissive config), and not for non-TypeScript
  typed languages.
skill_type: domain-expert
domain_focus: language-migration
tags:
  - typescript
  - javascript
  - migration
  - type-safety
  - tsconfig
version: 1.0.0
version_notes: Gallery reference for the staged `allowJs` → `strict` rollout.
token_budget: 1800
---

## When to use

Use when the user has an existing JavaScript project and wants to land
TypeScript without freezing feature work. The proven pattern is to add
TypeScript as a parallel type-checker first (`allowJs: true`,
`noEmit: true`), then progressively enable the strict flags one cohort
at a time. Each flag surfaces a different category of latent bug, so
flipping them all at once produces an unmergeable diff.

The flags to enable, in the order the TypeScript team itself recommends:

1. `noImplicitAny` — implicit `any` is the most common escape hatch in
   hand-written JS and the biggest source of late-discovered bugs.
2. `strictNullChecks` — forces every reference to be narrowed before use;
   this is the single biggest reduction in runtime `TypeError`s.
3. `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`
5. `alwaysStrict` — emits `"use strict"` in the output and tightens
   parser semantics.
6. `noImplicitThis`, `useUnknownInCatchVariables`

## Examples

For example, a minimal `tsconfig.json` that type-checks a JS tree without
emitting anything:

```json
{
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "noEmit": true,
    "target": "ES2022",
    "module": "ESNext",
    "strict": false
  },
  "include": ["src/**/*"]
}
```

Then, after the first cohort of `noImplicitAny` errors has been fixed,
tighten the config and pin the new flag in CI:

```json
{
  "compilerOptions": { "strict": true, "noImplicitAny": true }
}
```

A before / after snippet showing the most frequent migration fix:

```ts
// before — `user` is implicit any
function greet(user) {
  return "hello " + user.name.toUpperCase();
}

// after — explicit shape
interface User { name: string }
function greet(user: User): string {
  return `hello ${user.name.toUpperCase()}`;
}
```

## Pitfalls to avoid

- Do not enable `strict: true` on day one; the resulting diff is too large
  to review and will block the migration PR for days.
- Do not lean on `@ts-nocheck` or `@ts-ignore` to "make it pass"; those
  accumulate and become permanent dead weight. Use `@ts-expect-error`
  with a comment explaining the unfixed error instead.
- Do not pin `strictNullChecks` while leaving `noImplicitAny` off; the
  two flags reinforce each other, and turning them on in isolation
  produces inconsistent error reports.
- Do not skip the `skipLibCheck: true` flag if you depend on npm packages
  with imperfect typings — otherwise their errors block your own build.
- Do not forget to update `tsc --build` references and `paths` aliases;
  the strict checker enforces alias consistency where the loose checker
  silently coerces.