<!-- mdtest: rule=CONTENT006 -->
# CONTENT006 tone-banned-word

Content text avoids the words and phrases the voice file bans.

## What it does

Reads the `banned` list of `design/content/voice.toml` and fires once for each content key whose text uses a banned word or phrase as a whole word, ignoring case. A voice file with no `banned` list passes.

## Why it matters

The tone file is the only place the project writes down how it does not sound; unless copy is held to it, it is a wish rather than a rule.

## Remedy

Say what the product does in plain words, or remove the word from `banned` if the voice now allows it.

## Examples

### A banned word fires

```toml expect=fire file=design/content/en.toml config=content-voice-rules
locale = "en"

[[key]]
id = "home.hero"
text = "A seamless way to work"
```

### Plain copy is clean

```toml expect=clean file=design/content/en.toml config=content-voice-rules
locale = "en"

[[key]]
id = "home.hero"
text = "A quick way to work"
```
