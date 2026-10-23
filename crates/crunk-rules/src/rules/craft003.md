<!-- mdtest: rule=CRAFT003 -->
# CRAFT003 one-moment

A scene has one focal moment, marked with `data-moment`.

## What it does

Flags, once, a scene with more than one element marked `data-moment` (at the second), and a scene of at least 30 elements with none (at its first element). A value of `false` does not mark. Short scenes need no moment, and a project with no scenes is quiet. Advisory.

## Why it matters

A scene that names several things to notice first, or none, has no hierarchy; the eye has nowhere to land.

## Remedy

Keep `data-moment` on the single element the user should see first, or turn CRAFT003 off under `[lint]`.

## Examples

### Two moments fire

```html expect=fire file=design/scenes/home.scene.html
<div data-id="a" data-moment></div>
<div data-id="b" data-moment></div>
```

### One moment is clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="a" data-moment></div>
<div data-id="b"></div>
```

### A short scene with none is clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="a"></div>
```
