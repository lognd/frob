# gob-plan

Plan format, GRL compiler and executor (plugins.md section 10). This crate
currently holds only the GRL lexer (`grl::lex`, grl-spec.md section 3):
source text in, tokens with `gob-text` spans out, or a located `LexError`
written in the rule author's words. The lexer never panics on any input.

Later tickets add the parser, the relation catalog, the plan IR and the
executor here.

The printer (`grl::print`, grl-spec.md section 11) writes a syntax tree back as the one
canonical layout; `tests/print_stability.rs` proves `print(print(x)) = print(x)` and
`parse(print(t)) = t` over every fixture, the spec rules and a generated family of trees.
