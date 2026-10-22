<!-- mdtest: rule=SCENE001 -->
# SCENE001: unsupported CSS property

## What it does

Flags a CSS declaration in a scene (a `<style>` body or an inline `style` attribute) whose property
is outside the scene dialect: the layout solver's subset (block, flex, grid, absolute positioning,
gap, padding, min/max sizes, aspect ratio) plus the paint properties the renderer implements.

## Why

A property the solver cannot honour would be silently approximated, and the scene would then lie
about the rendered layout. An unsupported property is a finding instead.

## Notes

- Custom properties (`--x`) are always allowed; tokens are referenced as `var(--space-4)`.
- Vendor prefixes (`-webkit-box`) are flagged: the unprefixed property is the dialect.
- Shorthands such as `background`, `font`, `transition` are flagged unless listed; use longhands.

## Fix

Replace the property with a supported one, or drop it.
