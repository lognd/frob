<!-- mdtest: rule=CRAFT008 -->
# CRAFT008 semantic-roles-complete

The default preset declares danger, warning and success roles beside `body`, so a fresh init is
clean and is the clean case; the fire case drops the three state roles to leave only `body`.

## What it does

Flags, once per missing role and at `crunk.toml`, a `[palette.roles]` table with no danger, no
warning or no success role. A role is matched by name, ignoring ASCII case, and a conventional
alias counts for it: `error` or `destructive` for danger, `caution` for warning, `positive` for
success. Advisory.

## Why it matters

CONTRAST001 measures the role pairs that exist. A palette that never declares a state role passes
it vacuously, so a danger, warning or success colour that fails its contrast floor is never seen.
This presence rule pairs with it so the missing role is reported.

## Remedy

Declare the role under `[palette.roles]` as a `[foreground, background]` pair of palette names, or
turn CRAFT008 off under `[lint]` for a design with no state colours.

## Examples

### A palette with only a body role fires

```css expect=fire file=styles/app.css config=roles-body-only
.card {
  color: #111111;
}
```

### The default preset declares danger, warning and success roles and is clean

```css expect=clean file=styles/app.css
.card {
  color: #111111;
}
```
