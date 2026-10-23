<!-- mdtest: rule=CRAFT011 -->
# CRAFT011 optical-alignment

An icon beside a label is centred on it.

## What it does

Flags a scene container laid out with flex (an inline `display:flex` or a `flex` class) that holds an icon (`svg`, `img`, `data-icon` or an icon class) beside a label, and sets no `align-items` (or `items-*` class). Containers whose layout is not visible in the markup are quiet. Advisory.

## Why it matters

Left on the baseline, an icon sits a few pixels off the optical centre of its label.

## Remedy

Add `align-items: center` or an `items-center` class, or turn CRAFT011 off under `[lint]`.

## Examples

### An unaligned icon and label fire

```html expect=fire file=design/scenes/home.scene.html
<div data-id="row" style="display:flex"><svg data-id="icon"></svg><span data-id="label">Save</span></div>
```

### An aligned row is clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="row" style="display:flex;align-items:center"><svg data-id="icon"></svg><span data-id="label">Save</span></div>
```
