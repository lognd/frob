<!-- mdtest: rule=CRAFT008 -->
# CRAFT008 semantic-roles-complete

A project whose `crunk.toml` is the default preset declares only a `body` role, so the fire case
is the preset itself; the clean case adds the danger, warning and success roles.

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

### The default preset has no state roles and fires

```css expect=fire file=styles/app.css
.card {
  color: #111111;
}
```

### Danger, warning and success roles are clean

```css expect=clean file=styles/app.css config=roles-semantic
.card {
  color: #111111;
}
```
