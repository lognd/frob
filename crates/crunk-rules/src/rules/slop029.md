<!-- mdtest: rule=SLOP029 -->
# SLOP029 uniform-density

Four or more consecutive sections whose solved heights differ by less than 1.75x.

## What it does

Fires for a run of four or more sibling `section`s whose solved heights have a largest-to-smallest ratio under 1.75, so no band is an oversized moment.

## Why it matters

Every band carrying the same weight gives the page one speed; nothing is the hero and nothing is the pause.

## Remedy

Give one section real scale (a full-height hero, a large quote) and let others be compact.

## Examples

### Fires

```html expect=fire file=design/scenes/page.scene.html
<main data-id="page" style="width:600px">
  <section data-id="s1" style="height:300px"></section>
  <section data-id="s2" style="height:320px"></section>
  <section data-id="s3" style="height:300px"></section>
  <section data-id="s4" style="height:340px"></section>
</main>
```

### Clean

```html expect=clean file=design/scenes/page.scene.html
<main data-id="page" style="width:600px">
  <section data-id="s1" style="height:600px"></section>
  <section data-id="s2" style="height:200px"></section>
  <section data-id="s3" style="height:300px"></section>
  <section data-id="s4" style="height:240px"></section>
</main>
```
