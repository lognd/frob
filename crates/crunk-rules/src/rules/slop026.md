<!-- mdtest: rule=SLOP026 -->
# SLOP026 centred-long-text

Running text over three lines (or 160 characters, unsolved) with `text-align: center`.

## What it does

Fires for an element with its own text whose effective `text-align` (inherited) is `center` and whose solved text runs over three lines, or over 160 characters when the scene does not solve.

## Why it matters

Centred text has a ragged start on every line; past a few lines it is hard to read and is the template default.

## Remedy

Left-align the paragraph; keep centring for short headings and captions.

## Examples

### Fires

```html expect=fire file=design/scenes/page.scene.html
<section data-id="hero" style="text-align:center;width:300px">
  <p data-id="lead">Centred copy that goes on and on across many lines of a narrow column so that every line starts somewhere new and the eye has to hunt for it each time it wraps again.</p>
</section>
```

### Clean

```html expect=clean file=design/scenes/page.scene.html
<section data-id="hero" style="text-align:center;width:300px">
  <h1 data-id="title">Short title</h1>
  <p data-id="lead" style="text-align:left">Left aligned copy that goes on and on across many lines of a narrow column so that every line starts at the same place.</p>
</section>
```
