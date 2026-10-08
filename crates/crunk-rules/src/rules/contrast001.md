<!-- mdtest: rule=CONTRAST001 -->
# CONTRAST001 role-contrast-below-floor

Every `[scales]
spacing = [0, 4]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[palette.roles]` pair must meet its contrast floor. Each block is the `crunk.toml` of a
project.

## What it does

Measures the WCAG 2.2 contrast ratio of each declared role pair (foreground over background) in
every declared mode and flags a pair below its own floor: 4.5 by default, lower for a role that
declares the large-text or icon exception. The ratio is the gate; APCA is advisory and opt-in.

## Why it matters

A pair that fails the floor is unreadable for low-vision users and fails WCAG 2.2 AA, however
good it looks on the designer's monitor.

## Remedy

Move the foreground or background in `[palette]` until the ratio clears the floor, or declare the
role's floor explicitly when it is large text or an icon (3.0).

## Examples

### A role below the default floor fires

```toml expect=fire file=crunk.toml
[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#777777"
paper = "#ffffff"

[scales]
spacing = [0, 4]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[palette.roles]
body = ["ink", "paper"]
```

### A role that clears the floor is clean

```toml expect=clean file=crunk.toml
[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#1a1a1a"
paper = "#fafaf7"

[scales]
spacing = [0, 4]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[palette.roles]
body = ["ink", "paper"]
```

### A role with its own lower floor is judged against that floor

```toml expect=clean file=crunk.toml
[project]
css_root = "styles"
tokens_file = "tokens.css"
root_font_size = 16

[palette]
ink = "#777777"
paper = "#ffffff"

[scales]
spacing = [0, 4]
font_sizes = [16]
radii = [0]

[typography]
families = ["Inter"]
weights = [400]

[org]
buckets = ["base"]

[palette.roles]
heading = { pair = ["ink", "paper"], floor = 3.0 }
```
