<!-- mdtest: rule=SCENE001 -->
# SCENE001 scene-property-unsupported

A scene is styled only with the CSS subset the scene renderer and layout solver implement.

## What it does

Fires for each declaration in a scene document (a `<style>` body or an inline `style` attribute) whose property is outside the scene dialect. The finding names the property, the element (its `data-id`, else its tag) and the line. Custom properties (`--x`) are always allowed.

## Why it matters

A property the solver cannot honour would be silently approximated, and the scene would then lie about the rendered layout.

## Remedy

Replace the property with a supported one, or drop it. Use longhands rather than shorthands, and no vendor prefixes.

## Examples

### An unsupported property fires

```html expect=fire file=design/scenes/home.scene.html
<div data-id="hero" style="float: left"></div>
```

### Supported and custom properties are clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="hero" style="display: flex; --gap: 4px"></div>
```
