<!-- mdtest: rule=SLOP060 -->
# SLOP060 buzzword-density

## What it does

Scores the literal text of a JSX source against a buzzword lexicon (seamless, unlock, elevate, supercharge, world-class and similar). Three or more hits at three or more per 100 words, over at least 30 words, fires once per source; a single hit never fires. `[decisions] voice` silences it. Advisory.

The lexicon is a dated tell list (`SLOP060.toml`: term, added day, source). `crunk explain SLOP060` prints each entry's provenance; drop a replacement at `tells/SLOP060.toml` in the project to refresh it without a code change.

## Why it matters

Copy dense with buzzwords says nothing a competitor could not also say.

## Remedy

Say what the product does, or declare `voice` under `[decisions]`.

## Examples

### Dense buzzwords fire

```tsx expect=fire file=src/Page.tsx
export function Page() {
  return (
    <main>
      <p>Our seamless platform will unlock growth and elevate your team. A robust, comprehensive suite that helps every person work together on the things that matter most to them every day of the week.</p>
    </main>
  );
}
```

### One buzzword is clean

```tsx expect=clean file=src/Page.tsx
export function Page() {
  return (
    <main>
      <p>Our seamless platform helps every person work together on the things that matter most to them every day of the week, with plain words and no padding at all in this paragraph of copy.</p>
    </main>
  );
}
```

### A declared voice decision is clean

```tsx expect=clean file=src/Page.tsx config=decide-voice
export function Page() {
  return (
    <main>
      <p>Our seamless platform will unlock growth and elevate your team. A robust, comprehensive suite that helps every person work together on the things that matter most to them every day of the week.</p>
    </main>
  );
}
```
