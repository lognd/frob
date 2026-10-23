<!-- mdtest: rule=CRAFT005 -->
# CRAFT005 press-feedback

A pressed control answers the press; the clean case adds an `:active` rule.

## What it does

Flags, once and at the first stylesheet that styles something, a project whose styling never defines `:active` (a non-empty rule on the pseudo-class, an `@apply active:` variant or a Tailwind `active:` utility). Comments, strings and look-alike words such as `.is-active` do not count. A project with no styling is quiet. Advisory.

## Why it matters

A control that does not move when pressed feels dead, and on touch there is no hover to stand in for it.

## Remedy

Add an `:active` rule (a scale, a shade or an offset) to the interactive elements, or turn CRAFT005 off under `[lint]`.

## Examples

### A UI that never styles the pressed state fires

```css expect=fire file=styles/app.css
.btn {
  color: #111111;
}
.btn.is-active {
  color: #222222;
}
```

### An `:active` rule is clean

```css expect=clean file=styles/app.css
.btn {
  color: #111111;
}
.btn:active {
  transform: scale(0.97);
}
```
