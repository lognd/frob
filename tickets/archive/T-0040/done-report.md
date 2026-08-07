## Done report

frob mutate: AST-based Python mutation (comparison/arith/boolop swaps,
bool negation), runs the test command per mutant, reports survivors +
mutation score, restores source always. Weak tests -> survivors, strong
tests -> 100%. Delivers T-0011 (MUT gate + other langs = follow-on).
