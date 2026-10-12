# gob-plan

Plan format, GRL compiler and executor (plugins.md section 10). The crate
holds the GRL lexer (`grl::lex`, grl-spec.md section 3), parser and printer,
the relation catalog, the plan IR with its codec and validator, and the
executor (`exec`, with its relation modules). The lexer takes source text and
returns tokens with `gob-text` spans, or a located `LexError` written in the
rule author's words; it never panics on any input.

The printer (`grl::print`, grl-spec.md section 11) writes a syntax tree back as the one
canonical layout; `tests/print_stability.rs` proves `print(print(x)) = print(x)` and
`parse(print(t)) = t` over every fixture, the spec rules and a generated family of trees.
