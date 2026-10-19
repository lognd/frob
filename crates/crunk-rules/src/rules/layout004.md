<!-- mdtest: rule=LAYOUT004 -->
# LAYOUT004 content-outside-safe-area

Text and interactive targets stay inside the safe area. Each block is one scene file under `design/scenes/`; the scene's `safe_area` is the inset from every viewport edge (notches, rounded corners, home indicators) that content must respect.

## What it does

For a scene with a positive `safe_area`, fires for each text run or `interactive` node whose rectangle extends into the inset. A scene without `safe_area` is not judged. A project with no scene files is not judged.

## Why it matters

Content under a notch or a home indicator is hidden or cannot be tapped.

## Remedy

Pad the content in by the safe-area inset, or waive the rule with a reason.

## Examples

### Text at the very edge of a scene with a 20 px safe area fires

```json expect=fire file=design/scenes/home.scene.json
{
  "viewport": {
    "width": 400,
    "height": 300
  },
  "safe_area": 20,
  "root": {
    "id": "root",
    "kind": "box",
    "style": {
      "width": 400,
      "height": 300
    },
    "children": [
      {
        "id": "title",
        "kind": "text",
        "text": {
          "content": "Hello",
          "font_size": 16
        }
      }
    ]
  }
}
```

### The same text padded inside the safe area is clean

```json expect=clean file=design/scenes/home.scene.json
{
  "viewport": {
    "width": 400,
    "height": 300
  },
  "safe_area": 20,
  "root": {
    "id": "root",
    "kind": "box",
    "style": {
      "width": 400,
      "height": 300,
      "padding": 20
    },
    "children": [
      {
        "id": "title",
        "kind": "text",
        "text": {
          "content": "Hello",
          "font_size": 16
        }
      }
    ]
  }
}
```
