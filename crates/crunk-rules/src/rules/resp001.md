<!-- mdtest: rule=RESP001 -->
# RESP001 breakpoint-without-scene

Every declared breakpoint is solved by some scene. Each block is one scene file under `design/scenes/` of a project whose `crunk.toml` declares `[breakpoints]` (`sm` 640, `md` 768, `lg` 1024); the case's `config` selects whether scenes for the other breakpoints exist.

## What it does

Fires once for each `[breakpoints]` width that no scene file is solved at (a scene whose viewport width equals the breakpoint). A project with no `[breakpoints]` or no scene files is not judged.

## Why it matters

A layout checked at one width says nothing about the others; a breakpoint no scene covers is a layout nobody has verified.

## Remedy

Add a `design/scenes/*.scene.json` whose viewport is the breakpoint's width, or waive the rule with a reason.

## Examples

### Only the `sm` breakpoint has a scene, so `md` and `lg` fire

```json expect=fire config=breakpoints file=design/scenes/home.scene.json
{
  "viewport": {
    "width": 640,
    "height": 300
  },
  "root": {
    "id": "root",
    "kind": "box",
    "style": {
      "width": 640,
      "height": 300
    },
    "children": [
      {
        "id": "a",
        "kind": "box",
        "style": {
          "width": 100,
          "height": 50
        }
      }
    ]
  }
}
```

### A scene at every declared breakpoint is clean

```json expect=clean config=breakpoints-scenes file=design/scenes/home.scene.json
{
  "viewport": {
    "width": 640,
    "height": 300
  },
  "root": {
    "id": "root",
    "kind": "box",
    "style": {
      "width": 640,
      "height": 300
    },
    "children": [
      {
        "id": "a",
        "kind": "box",
        "style": {
          "width": 100,
          "height": 50
        }
      }
    ]
  }
}
```
