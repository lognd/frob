<!-- mdtest: rule=CRAFT009 -->
# CRAFT009 real-content

A scene shows real content, not a stand-in.

## What it does

Flags an empty `data-copy` key, a content key whose text is blank or placeholder (lorem, ipsum, todo, tbd, placeholder, xxx), an `<img>` with no `alt` (or `data-copy-alt`) and an `<img>` with no `data-provenance`. Unknown keys stay with CONTENT003 and literal copy with CONTENT001. A project with no scenes is quiet. Advisory.

## Why it matters

Layouts judged on stand-in content look right and ship wrong. Provenance on every picture says a real one is coming from somewhere.

## Remedy

Write the copy, give the image alt text and a `data-provenance`, or turn CRAFT009 off under `[lint]`.

## Examples

### An image with no alt or provenance fires

```html expect=fire file=design/scenes/home.scene.html
<img data-id="hero" src="hero.png">
```

### An image with alt and provenance is clean

```html expect=clean file=design/scenes/home.scene.html
<img data-id="hero" src="hero.png" alt="A team at a desk" data-provenance="studio shoot, 2026">
```
