<!-- mdtest: rule=RESP001 -->
# RESP001 root-wider-than-breakpoint

A scene root fits every declared breakpoint. Each block is one scene document (`design/scenes/*.scene.html`) of a project whose `crunk.toml` declares `[breakpoints]` (`sm` 640, `md` 768, `lg` 1024); the scene is solved with the crunk-layout solver (T1) at each of those widths.

## What it does

Solves each scene at every `[breakpoints]` width and fires for each solve whose root extends more than half a pixel past the viewport's right edge. A project with no `[breakpoints]` or no scene files is not judged.

## Why it matters

A layout checked at one width says nothing about the others; a root that is wider than a narrow viewport scrolls sideways or clips on exactly the devices that breakpoint names.

## Remedy

Let the root follow the viewport (a percentage width, `max-width`, or wrapping content), or waive the rule with a reason.

## Examples

### A fixed 700px root is wider than the `sm` breakpoint and fires

```html expect=fire config=breakpoints file=design/scenes/home.scene.html
<div data-id="root" style="width:700px;height:300px">
<div data-id="a" style="width:100px;height:50px"></div>
</div>
```

### A root that follows the viewport is clean at every breakpoint

```html expect=clean config=breakpoints file=design/scenes/home.scene.html
<div data-id="root" style="width:100%;height:300px">
<div data-id="a" style="width:100px;height:50px"></div>
</div>
```
