<!-- mdtest: rule=STATE005 -->
# STATE005 state-diff-low

Two states of one screen differ visibly on every platform. Each block is one source file in a project whose `crunk.toml` is the default preset plus the platforms `desk` and `phone` and one screen `home` with `default` and `hover` states; the case's `config` selects the ledger.

## What it does

Reads the pairwise pixel difference the render ledger records for two states of a screen on a platform. A pair under the minimum (10000 parts per million, one percent of pixels) is a finding naming the screen, both states and the platform. A ledger that cannot be read is reported as unresolved instead of a clean pass.

## Why it matters

Two states that render near-identically give the user no feedback and make the extra state dead weight; the state exists in the spec but not on screen.

## Remedy

Give the states a visible difference (color, shape, text), or merge them if they are the same state.

## Examples

### Two near-identical renders fire

```css expect=fire config=render-alike file=styles/app.css
.a {
  margin: 0;
}
```

### Distinct renders are clean

```css expect=clean config=render-distinct file=styles/app.css
.a {
  margin: 0;
}
```
