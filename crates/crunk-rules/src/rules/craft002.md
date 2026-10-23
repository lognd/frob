<!-- mdtest: rule=CRAFT002 -->
# CRAFT002 component-states-complete

A component declares the full set of states a user can reach.

## What it does

Flags, once per component and at its `states` table, a component that lacks any of hover, active (or pressed), disabled, focus (or focus-visible), loading, error (or invalid) and empty. The message names what is missing. A project with no component files is quiet. Advisory.

## Why it matters

A state that is not designed is designed by accident at build time. Listing every state up front is how loading, error and empty screens get a design.

## Remedy

Add a `[[states]]` entry for each missing state, or turn CRAFT002 off under `[lint]` for a design of static components.

## Examples

### A component with only a hover state fires

```toml expect=fire file=design/components/button.component.toml
name = "button"

[[states]]
id = "hover"
```

### A component with every state is clean

```toml expect=clean file=design/components/button.component.toml
name = "button"

[[states]]
id = "hover"

[[states]]
id = "active"

[[states]]
id = "disabled"

[[states]]
id = "focus"

[[states]]
id = "loading"

[[states]]
id = "error"

[[states]]
id = "empty"
```
