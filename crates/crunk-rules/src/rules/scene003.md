<!-- mdtest: rule=SCENE003 -->
# SCENE003 scene-tag-unknown

A scene uses only the HTML tags of the scene dialect, plus capitalised component tags.

## What it does

Fires for each element whose lowercase tag is outside the dialect's tag list (`<blink>`, `<my-widget>`). Capitalised tags are component instances and pass; content inside an `svg` is skipped.

## Why it matters

The layout solver and exporters only know the dialect's tags; anything else would be approximated or dropped.

## Remedy

Use a supported tag, or make it a component (`<MyWidget>`).

## Examples

### An unknown tag fires

```html expect=fire file=design/scenes/home.scene.html
<blink data-id="a"></blink>
```

### Known tags and components are clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="a"><Button data-id="b"></Button></div>
```
