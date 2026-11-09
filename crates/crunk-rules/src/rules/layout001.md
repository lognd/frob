<!-- mdtest: rule=LAYOUT001 -->
# LAYOUT001 child-overflows-parent

A scene node stays inside its parent's rectangle. Each block is one scene document (`design/scenes/*.scene.html`) of a default-preset project; the scene is solved with the crunk-layout solver (T1) and every node's absolute rectangle is compared with its parent's.

## What it does

Fires for each solved node whose rectangle extends more than half a pixel beyond its parent's on any side. The root has no parent and is judged by LAYOUT003 against the viewport. A project with no scene files is not judged.

## Why it matters

Content that spills out of its container is cut off, covers its neighbours or forces scrolling, and the layout that looked right at one size breaks at another.

## Remedy

Size the child to fit (shrink, wrap or scroll it), enlarge the parent, or waive the rule with a reason when the overflow is intended.

## Examples

### A child wider than its parent fires

```html expect=fire file=design/scenes/home.scene.html
<div data-id="root" style="width:400px;height:300px">
<div data-id="panel" style="width:200px;height:100px">
<div data-id="wide" style="width:300px;height:40px;flex-shrink:0"></div>
</div>
</div>
```

### A child inside its parent is clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="root" style="width:400px;height:300px">
<div data-id="panel" style="width:200px;height:100px">
<div data-id="wide" style="width:150px;height:40px;flex-shrink:0"></div>
</div>
</div>
```
