# Crunk solver and scene stylesheets

Status: current
Owner: crunk

Decision for audit2 H2: the solver REJECTS a scene whose `<style>` body holds rules or an
`@media` block, instead of honoring them.

Why: the solver maps inline `style` attributes only. Applying stylesheets needs selector
matching (class, id, type, compound), cascade and specificity, inheritance across rules and
`@media` evaluation against the solve width. That is a larger feature than the bounded fix.
Before this change the solver dropped the rules silently, so `crunk render`, `crunk snapshot`,
LAYOUT001/002 and RESP001 judged the unstyled layout and a snapshot baseline recorded it as truth.

Behavior: `solve_scene_html` returns `SolveError::StylesheetNotApplied` (message starts with
`STYLESHEET:`) naming the `<style>` line. Callers (`crunk render`, `crunk snapshot`) surface the
error text, so the author is told to move the declarations to inline `style` attributes. An
empty `<style>` is accepted. Honoring stylesheets stays follow-up work; lifting the refusal
means deleting the check in `style_or_refuse`.
