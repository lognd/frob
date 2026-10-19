<!-- mdtest: rule=LAYOUT002 -->
# LAYOUT002 siblings-overlap

Sibling scene nodes do not cover one another. Each block is one scene file under `design/scenes/`; siblings share a parent and their solved rectangles are compared pairwise.

## What it does

Fires for each pair of siblings whose rectangles intersect by more than half a pixel in both directions. Touching edges are not an overlap. A project with no scene files is not judged.

## Why it matters

Overlapping siblings hide text and targets behind one another; a negative margin or an absolute offset that works at one viewport collides at another.

## Remedy

Remove the negative margin or offset, give the siblings room, or waive the rule with a reason when the layering is intended.

## Examples

### A negative margin that pulls a sibling over its neighbour fires

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
        "id": "a",
        "kind": "box",
        "style": {
          "width": 100,
          "height": 50
        }
      },
      {
        "id": "b",
        "kind": "box",
        "style": {
          "width": 100,
          "height": 50,
          "margin": -20
        }
      }
    ]
  }
}
```

### Siblings laid side by side are clean

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
        "id": "a",
        "kind": "box",
        "style": {
          "width": 100,
          "height": 50
        }
      },
      {
        "id": "b",
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
