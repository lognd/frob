<!-- mdtest: rule=CONTENT007 -->
# CONTENT007 content-locale-gap

Every locale defines every content key that any locale defines.

## What it does

Groups the files in `design/content/*.toml` by their `locale` (files with none count as `default`) and fires once for each key that one locale defines and another lacks, anchored at the locale that lacks it. A project with a single locale passes.

## Why it matters

A key missing from a translation falls back to another language or to nothing, so one locale ships with holes the default locale never shows.

## Remedy

Add the key to the locale's content file with translated text.

## Examples

### A key one locale lacks fires

```toml expect=fire file=design/content/en.toml config=content-locale-gap
locale = "en"

[[key]]
id = "home.hero"
text = "Welcome back"

[[key]]
id = "home.cta"
text = "Get started"
```

### Locales that define the same keys are clean

```toml expect=clean file=design/content/en.toml
locale = "en"

[[key]]
id = "home.hero"
text = "Welcome back"
```
