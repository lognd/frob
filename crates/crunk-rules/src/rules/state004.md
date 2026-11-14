<!-- mdtest: rule=STATE004 -->
# STATE004 render-missing

Every screen state has a render-ledger entry for each platform it applies to. Each block is one source file in a project whose `crunk.toml` is the default preset plus the platforms `desk` and `phone` and one screen `home` with a `default` state; the case's `config` selects the ledger.

## What it does

For every `(screen, state, platform)` cell the spec declares (a state's or screen's `applies_to` narrows the platforms), checks that the render ledger gathered from the gallery manifest holds a render. Each cell without one is a finding naming the screen, state and platform. A ledger that cannot be read is reported as unresolved instead of a clean pass.

## Why it matters

A state nobody has rendered on a platform has never been seen there, so layout, contrast and approval checks on it prove nothing.

## Remedy

Run the gallery render for the missing cell, or narrow the screen's or state's `applies_to` if the platform does not apply.

## Examples

### A cell with no render fires

```css expect=fire config=render-missing file=styles/app.css
.a {
  margin: 0;
}
```

### Every cell rendered is clean

```css expect=clean config=render-complete file=styles/app.css
.a {
  margin: 0;
}
```
