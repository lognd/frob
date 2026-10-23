<!-- mdtest: rule=CRAFT013 -->
# CRAFT013 voice-file-present

A scene that references a copy key needs the project's voice file; the clean case adds
`design/content/voice.toml` (the `content-voice` config).

## What it does

Flags, once, a project where a scene document references a copy key (`data-copy` or
`data-copy-<attribute>` with a non-empty key) and `design/content/voice.toml` does not exist. The
finding sits at the first scene that references a key and names SLOP060. A voice file holding only
blank lines and `#` comments is a placeholder: it fires once at that file. A voice file with
content is present, whether or not it is well formed. Scenes with no copy key never fire it, and
neither does a project with no scenes. Warn.

## Why it matters

SLOP060 measures buzzword density against the allow and deny list of the tone file. With no voice
file there is nothing to judge against, and deleting the file passes SLOP060 vacuously. This
presence rule pairs with it so the missing voice is reported.

## Remedy

Write `design/content/voice.toml` with the product's voice, tone by situation and banned or
preferred terms, or turn CRAFT013 off under `[lint]` for a design without scene copy.

## Examples

### A referenced copy key with no voice file fires

```html expect=fire file=design/scenes/home.scene.html
<h1 data-id="hero" data-copy="home.hero">Welcome back</h1>
```

### The same scene with a voice file is clean

```html expect=clean file=design/scenes/home.scene.html config=content-voice
<h1 data-id="hero" data-copy="home.hero">Welcome back</h1>
```

### A scene with no copy key is clean

```html expect=clean file=design/scenes/home.scene.html
<div data-id="hero"></div>
```
