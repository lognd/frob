<!-- mdtest: rule=SCENE005 -->
# SCENE005 scene-document-unloadable

Every scene document under `design/scenes` loads, and each scene name is used once.

## What it does

Fires for a `.scene.html` file (any case, nested directories included) that cannot be read, is over the size cap, is not UTF-8, has no elements or cannot be parsed, and for a second file whose name (without `.scene.html`) repeats an earlier one.

## Why it matters

A scene that does not load is skipped by every other SCENE, GX and CONTENT rule, so it would pass them unchecked.

## Remedy

Fix or remove the file: save it as UTF-8, put an element in it, keep it under the size cap, and give each scene a unique name.

## Examples

### A scene with no elements fires

```html expect=fire file=design/scenes/home.scene.html
<!-- nothing here yet -->
```

### A well-formed scene is clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="a"></div>
```
