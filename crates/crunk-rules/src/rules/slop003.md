<!-- mdtest: rule=SLOP003 -->
# SLOP003 gradient-abuse

## What it does

Flags the fourth gradient background in a project, and any gradient text (`background-clip: text`). `[decisions] gradients` silences it. Advisory.

## Why it matters

One gradient is a choice; a gradient on every surface is a style nobody argued for.

## Remedy

Keep one gradient where it carries meaning, or declare `gradients` under `[decisions]`.

## Examples

### Four gradient backgrounds fire

```css expect=fire file=styles/app.css
.a0 {
  background: linear-gradient(#111, #330);
}
.a1 {
  background: linear-gradient(#111, #331);
}
.a2 {
  background: linear-gradient(#111, #332);
}
.a3 {
  background: linear-gradient(#111, #333);
}
```

### Gradient text fires

```css expect=fire file=styles/app.css
.t {
  background-clip: text;
}
```

### One gradient is clean

```css expect=clean file=styles/app.css
.hero {
  background: linear-gradient(#111, #333);
}
```

### A declared gradients decision is clean

```css expect=clean file=styles/app.css config=decide-gradients
.a0 {
  background: linear-gradient(#111, #330);
}
.a1 {
  background: linear-gradient(#111, #331);
}
.a2 {
  background: linear-gradient(#111, #332);
}
.a3 {
  background: linear-gradient(#111, #333);
}
```
