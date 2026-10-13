<!-- mdtest: rule=HUMAN002 -->
# HUMAN002 human-review-rejected

A reviewed screen is not under a standing rejection. Each block is one source file in a project
whose `crunk.toml` is the default preset plus one reviewed screen `home`.

## What it does

When the `[[review]]` entry of a screen state has the current digest and the verdict `rejected`,
the rule fires, naming the screen, the reviewer and their note. A rejection of an older digest is
a stale review (HUMAN001), not a rejection. It is Advisory in `crunk check` and Error at the
release gate.

## Why it matters

A recorded "no" must keep blocking a release until someone changes the screen or approves it.

## Remedy

Fix what the note asks for (any change to the screen's inputs makes the review stale), then
`crunk ack` the new state with `--verdict approved`.

## Examples

### A current rejection fires

```css expect=fire config=review-rejected file=styles/app.css
.a {
  margin: 0;
}
```

### A current approval is clean

```css expect=clean config=review-current file=styles/app.css
.a {
  margin: 0;
}
```
