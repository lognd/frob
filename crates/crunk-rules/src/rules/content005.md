<!-- mdtest: rule=CONTENT005 -->
# CONTENT005 glossary-term-avoided

Content text uses the glossary's preferred term, not a variant it lists to avoid.

## What it does

Reads the `[[term]]` entries of `design/content/voice.toml` (`preferred` plus an `avoid` list) and fires once for each content key whose text uses an avoided variant as a whole word or phrase, ignoring case. A voice file with no glossary passes.

## Why it matters

A product that says "sign in" on one screen and "log in" on the next teaches its users that the two are different things.

## Remedy

Replace the variant with the preferred term, or remove the variant from the glossary if it is acceptable.

## Examples

### An avoided variant fires

```toml expect=fire file=design/content/en.toml config=content-voice-rules
locale = "en"

[[key]]
id = "home.cta"
text = "Log in to continue"
```

### The preferred term is clean

```toml expect=clean file=design/content/en.toml config=content-voice-rules
locale = "en"

[[key]]
id = "home.cta"
text = "Sign in to continue"
```
