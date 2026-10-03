# gob-plan

Plan format, GRL compiler and executor (plugins.md section 10). This crate
currently holds only the GRL lexer (`grl::lex`, grl-spec.md section 3):
source text in, tokens with `gob-text` spans out, or a located `LexError`
written in the rule author's words. The lexer never panics on any input.

Later tickets add the parser, the relation catalog, the plan IR and the
executor here.
