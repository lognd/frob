<!-- mdtest: rule=SCENE004 -->
# SCENE004 scene-at-rule-unsupported

A scene stylesheet uses only `@media`.

## What it does

Fires for each at-rule other than `@media` in a scene's `<style>` bodies, including at-rules nested inside a `@media` block.

## Why it matters

`@font-face`, `@keyframes`, `@import` and the like are not implemented by the layout solver and renderer, so they would silently do nothing.

## Remedy

Drop the at-rule; fonts and motion come from tokens.

## Examples

### An unsupported at-rule fires

```html expect=fire file=design/scenes/home.scene.html
<style>@keyframes spin { from { opacity: 0 } to { opacity: 1 } }</style>
<div data-id="a"></div>
```

### A media query is clean

```html expect=clean file=design/scenes/home.scene.html
<style>@media (min-width: 768px) { .a { display: flex } }</style>
<div data-id="a"></div>
```
