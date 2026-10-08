<!-- mdtest: rule=WAIVE001 -->
# WAIVE001 waiver-without-reason

A `crunk:waive RULE reason="..."` comment silences one rule at one declaration. Without the reason
the waiver is not granted: the finding it names stays, and this rule reports the comment itself.

## What it does

Flags a `crunk:waive` comment that has no `reason`, or a blank one. WAIVE001 cannot be waived.

## Why it matters

A silent waiver is an undocumented exception. The reason is what a reviewer reads when deciding
whether the waiver can go.

## Remedy

Add `reason="why this declaration is exempt"` to the comment, or delete the waiver and fix the
declaration.

## Examples

### A waiver with no reason fires

```css expect=fire file=styles/app.css
.card {
  padding: 13px; /* crunk:waive SPACE001 */
}
```

### A blank reason fires

```css expect=fire file=styles/app.css
.card {
  /* crunk:waive SPACE001 reason="" */
  padding: 13px;
}
```

### A waiver with a reason is clean

```css expect=clean file=styles/app.css
.card {
  padding: 13px; /* crunk:waive SPACE001 reason="legacy embed" */
}
```

### A comment that only mentions the directive is clean

```css expect=clean file=styles/app.css
/* see the crunk:waive docs */
.card {
  padding: 8px;
}
```
