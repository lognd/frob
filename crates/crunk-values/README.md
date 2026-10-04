# crunk-values

Pure, panic-free CSS value math for the crunk design-system checker.

- `Color::parse`: hex, `rgb()`/`rgba()`, `hsl()`/`hsla()` and CSS named colors into
  0-1 sRGB channels plus alpha.
- `Color::distance`: redmean-weighted sRGB distance.
- `Color::contrast_ratio`: WCAG 2.x relative-luminance contrast ratio.
- `Length::parse`: px, rem, zero, percent, auto, calc and other units, with a
  root font size for rem.

Every function is pure (no I/O, no globals) and returns a typed error instead
of panicking, so the API can back built-in functions in other tools. Behaviour
is a port of the Python crunk `crunk.values` package and is pinned to it by
reference vectors in `tests/`.

OKLab and OKLCH are out of scope.
