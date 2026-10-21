# GRL examples: model inputs, node, cell and owned by

Status: current
Owner: grimble
Decisions: D80
Audience: rule author

How a GRL example supplies a design model and how the executor answers
the model-backed parts of a rule (grl-spec.md section 6). Rules that
`need model` are checked against the `model` input of each example.

## The model input

An example may carry `model """..."""`, the text of a grmb model. The
runner reads it through the installed model reader
(`gob_plan::examples::install_model_reader`; the grimble binary installs
`grimble_check::example_model::read_example_model`). Two side tables come
from it:

- `model.nodes`: one row per node (name, kind, path).
- `model.selectors`: one row per `owns` selector (node, selector), with
  the surrounding quotes removed.

An example with no `model` input that runs a rule using `node`, `cell` or
`owned by` is refused with a run error. It is never silently clean. A
model that does not parse is a model error.

## node and owned by

`find n: node` ranges over `model.nodes` in model order. `u owned by n`
holds when the file of `u` matches one of the `owns` globs of `n`. A
glob that cannot be compiled is refused with a bad-pattern error rather
than treated as matching nothing. A model with no `owns` selectors owns
nothing, so every file is unowned.

## cell

`find c: cell` ranges over `engine.cells`, which the runner computes for
the example file when the rule mentions `cell`. One row exists per (owner
node, atom) pair where the file calls a name in the atom's callee
vocabulary for the example language. Columns:

| column   | meaning                                                      |
|----------|--------------------------------------------------------------|
| node     | the owning node                                              |
| atom     | the capability atom observed                                 |
| observed | always true for computed rows                                |
| granted  | the node has an unscoped `may` covering the atom             |
| excused  | the node has an `excuses` clause covering the atom           |
| line     | the first line where the atom is used                        |

A grant covers its own atom and every dotted descendant, so `may net`
covers `net.listen`. A file that no node owns yields no cells. A finding
on a cell reports the line column.

## Limits

- Only unscoped `may` clauses count as grants; `may ... at "glob"` and
  grant arguments are ignored.
- Observed atoms come from callee names only, with no data-flow.
