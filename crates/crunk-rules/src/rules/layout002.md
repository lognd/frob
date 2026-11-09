<!-- mdtest: rule=LAYOUT002 -->
# LAYOUT002 siblings-overlap

Sibling scene nodes do not cover one another. Each block is one scene document (`design/scenes/*.scene.html`) solved with the crunk-layout solver; siblings share a parent and their solved rectangles are compared pairwise.

## What it does

Fires for each pair of siblings whose rectangles intersect by more than half a pixel in both directions. Touching edges are not an overlap. A project with no scene files is not judged.

## Why it matters

Overlapping siblings hide text and targets behind one another; a negative margin or an absolute offset that works at one viewport collides at another.

## Remedy

Remove the negative margin or offset, give the siblings room, or waive the rule with a reason when the layering is intended.

## Examples

### A negative margin that pulls a sibling over its neighbour fires

```html expect=fire file=design/scenes/home.scene.html
<div data-id="root" style="width:400px;height:300px">
<div data-id="a" style="width:100px;height:50px"></div>
<div data-id="b" style="width:100px;height:50px;margin:-20px"></div>
</div>
```

### Siblings laid side by side are clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="root" style="width:400px;height:300px">
<div data-id="a" style="width:100px;height:50px"></div>
<div data-id="b" style="width:100px;height:50px"></div>
</div>
```
