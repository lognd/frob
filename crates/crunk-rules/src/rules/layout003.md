<!-- mdtest: rule=LAYOUT003 -->
# LAYOUT003 node-clipped-by-viewport

No scene node extends past the viewport edge. Each block is one scene file under `design/scenes/`; every node's rectangle, the root included, is compared with the viewport the scene is solved against.

## What it does

Fires for each solved node whose rectangle extends more than half a pixel beyond the viewport on any side. A project with no scene files is not judged.

## Why it matters

Content past the viewport edge is clipped or needs horizontal scrolling, which hides text and targets from the people who cannot scroll to them.

## Remedy

Wrap or shrink the content to the viewport, or waive the rule with a reason when the scrolling is intended.

## Examples

### A node wider than the viewport fires

```json expect=fire file=design/scenes/home.scene.json
{
  "viewport": {
    "width": 400,
    "height": 300
  },
  "root": {
    "id": "root",
    "kind": "box",
    "style": {
      "width": 400,
      "height": 300
    },
    "children": [
      {
        "id": "banner",
        "kind": "box",
        "style": {
          "width": 450,
          "height": 40,
          "shrink": 0
        }
      }
    ]
  }
}
```

### Nodes inside the viewport are clean

```json expect=clean file=design/scenes/home.scene.json
{
  "viewport": {
    "width": 400,
    "height": 300
  },
  "root": {
    "id": "root",
    "kind": "box",
    "style": {
      "width": 400,
      "height": 300
    },
    "children": [
      {
        "id": "banner",
        "kind": "box",
        "style": {
          "width": 350,
          "height": 40,
          "shrink": 0
        }
      }
    ]
  }
}
```
