# frob.render -- the unified CLI output layer

`frob.render` is the single place every command's human-facing stdout is
produced. It exists so that pretty, colored output on a human TTY and
deterministic, machine-stable plain output for pipes and agents come from one
implementation instead of ad-hoc `print` calls scattered across commands
(the T-0448 epic). A command runner builds a `Renderer` for its output stream
and prints through it; it never writes ANSI escapes or bare `print` itself.

`--json` is a separate structured channel and is unaffected by this layer;
`frob.render` governs only the human/plain text channel.

## Color resolution

Color is decided exactly once, when a `Renderer` is built for a stream
(`Renderer.for_stream`), by `resolve_color`. The decision honors, in
descending precedence:

1. an explicit `--no-color` flag, or `--color=never` -- force OFF.
2. `--color=always` -- force ON.
3. `NO_COLOR` (any non-empty value) and `FROB_NO_COLOR` -- force OFF (the
   community `NO_COLOR` convention; `FROB_NO_COLOR` is the frob-scoped
   equivalent).
4. `CLICOLOR_FORCE` (non-zero) -- force ON even when the stream is not a TTY.
5. `TERM=dumb` -- OFF.
6. otherwise: ON iff the stream `isatty()`.

Explicit off (`--no-color` / `--color=never` / `NO_COLOR`) always beats
`CLICOLOR_FORCE`. The resolution runs once per `Renderer`, never per call
site, so a command's output is internally consistent.

<!-- frob:invariant INV-020 -->

## Semantic palette

One colorblind-safe palette, shared by every command, with five semantic
names -- `good`, `warn`, `critical`, `muted`, `accent`. Colors carry meaning,
never decoration. `critical` is distinguished from `good` by weight (bold)
as well as hue, so red/green colorblindness does not collapse the two;
`accent` sits off the red/green axis (cyan). The palette reuses the SGR
codes from `frob.logging` rather than duplicating them. The accent is
distinct from the severity colors and is never used to signal severity.

## Element vocabulary

The standardized elements are namespaced off `Renderer.write` (a
`RenderWriter`), so a command calls `r.write.heading(...)`,
`r.write.kv(...)`, etc. rather than accumulating flat methods on `Renderer`
(the god-class split). Elements: `heading`, `subhead`, `kv`, `status`,
`count_summary`, `path`, `ticket_id`, `table`, `tree`, `count_deltas`, and
the severity shortcuts `good`, `warn`, `critical`, `muted`. `progress`
(T-0460) is the one TTY-only, ephemeral exception -- see its own section
below.

Every element has BOTH a colored-TTY rendering and a deterministic PLAIN
rendering. The plain rendering is the canonical, machine-stable form: no ANSI
escapes, no cursor control, no spinner residue -- so `frob ... | cat` and
agent capture are clean and greppable. Color only paints an element; it never
changes the plain structural shape.

Element contract -- total vs fallible:

| Element kind | Return | Notes |
|--------------|--------|-------|
| Structural writers (`heading`, `subhead`, `kv`, `count_summary`, `path`, `table`, `tree`, `count_deltas`, severity text) | total (`str` / `list[str]` / direct write) | cannot fail |
| Validated elements (`status`/`status_pill`, `ticket_id`/`ticket_id_label`) | typani `Result` | reject malformed input as `Err(RenderError)` rather than emitting a wrong glyph |

New elements must follow the same split: a fallible element returns a
`Result`; a total element returns a string (or, for multi-line elements
like `table`/`tree`, a `list[str]` of lines). `RenderError` is the fallible
error type.

### `table`

`r.write.table(headers, rows)` renders a fixed-column table: a header row
(painted `accent`), a `-`-rule separator (painted `muted`), then one line
per data row. Column widths are the max width across the header and every
row's cell in that column, so color and plain mode share the exact same
column layout -- color only paints the header/rule, never the data cells,
and never changes a width.

### `tree`

`r.write.tree(entries)` renders a hierarchical listing from `(depth,
label)` pairs. Each line is `"  " * depth` of indent plus a `- ` marker;
depth-0 labels are painted `accent`. Deliberately no box-drawing
connectors (`|--`, `` `-- ``) -- those need sibling lookahead to place
correctly, and a lookahead-dependent shape is exactly the kind of thing
that could silently differ between callers. Plain indent+marker is
deterministic from the `(depth, label)` sequence alone.

### `count_deltas`

`r.write.count_deltas(deltas)` renders a `key: old -> new (+n/-n)` rollup
line from a `{key: (before, after)}` mapping -- the `frob check --delta`
before/after use case. This element assumes fewer is the improving
direction (a violation-count convention): a non-positive delta paints
`good`, a positive delta paints `critical`, unchanged paints `muted`. A
caller with a metric where "more" is the improving direction should not
reach for this element as-is.

### `progress` (T-0419 contract, TTY-only)

`r.write.progress(label)` returns a `Progress`, meant to be used as a
context manager around a unit of long-running work:

```python
with r.write.progress("running gates") as p:
    for i, stage in enumerate(stages):
        p.update(stage.name, i, len(stages))
        run(stage)
```

`Progress.update(label, current, total)` redraws one in-place line
(`label [#####-----] NN%`) via a carriage return -- no new line is ever
appended per update. `Progress.clear()` (also called automatically on
`__exit__`, success or exception) erases that line entirely, leaving no
residue, per the T-0419 "clears on completion" contract. On a non-TTY
stream (piped, redirected, CI) both methods are unconditional no-ops: no
carriage return, no ANSI, nothing reaches the captured output at all --
this is the one element in the vocabulary that is TTY-only by design
rather than "same shape, only the paint differs." `Renderer.is_tty` is
resolved once per `Renderer` (independent of the color decision, since
`--no-color` on a real TTY must still gate `progress` on) and threaded
into every `Progress` the writer builds.

## Renderer

Build a `Renderer` once for the output stream via `Renderer.for_stream`
(which runs color resolution), then call `r.write.<element>(...)`. `Renderer`
deliberately delegates the element vocabulary to `RenderWriter` (`r.write`)
so the facade stays small and every future element lands on `RenderWriter`,
not as another method on `Renderer`.

### Invariant: frob.render is the sole stdout path for command runners

INV-RENDER-SOLE-STDOUT (enforcement: T-0459; strata proof: T-0459's
capability may-analysis over the `terminal`/stdout-write effect): a command
runner produces human-facing stdout ONLY through a `Renderer` -- no bare
`print`, `click.echo`, or `sys.stdout.write` anywhere outside
`frob.render`. This is a normative exclusivity claim, so it is not left as
prose: it is a declared invariant, enforced two ways once T-0459 lands --
(1) a `frob check` gate that fails on any bare stdout write outside
`frob.render`, and (2) strata: the stdout-write capability is modeled so
that command-runner nodes may NOT hold it directly (only `frob.render` may),
making "only frob.render writes stdout" a proven effect, not an assertion.
Until T-0459 lands this invariant is the TARGET contract, tracked there, not
yet proven -- do not read it as already-enforced.

## Exemplar: frob doctor

`frob doctor` is one of the two foundation exemplars migrated to the layer.
Its native-extension report is printed through `Renderer` (headings +
`kv` rows + `status` pills), with `--json` emitting the unchanged
`DoctorReport`. Intentional behavior change during migration: the old
remediation line printed the literal word `None` when there was no
remediation (`f"remediation: {report.remediation}"`); the migrated line uses
`r.write.kv("  remediation", report.remediation or "")`, so an empty
remediation prints an empty value, not `None`. This is a deliberate fix,
disclosed here and in the T-0448 Done report.

## Exemplar: frob map

`frob map` is the second migrated exemplar. Its directory-tree summary prints
through `Renderer` in the human channel while its `--json` branch is
untouched. The golden tests assert that `frob map`'s color-forced and
plain-forced outputs share the same ANSI-stripped shape -- proving color only
paints and never restructures the plain form. T-1238 regrouped `frob map`
under `frob explore map` too (`explore_runner.run` dispatches straight into
this same `map_runner.run`) -- the `Renderer` wiring described here is
unaffected either way.
