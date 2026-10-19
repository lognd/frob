// The dispatcher after review: a plain guarded call; the rule owns the scope logic.
fn expression(expr: &Expr, checker: &mut Checker) {
    match expr {
        Expr::Name(id) => {
            if checker.is_rule_enabled(Rule::BuiltinVariableShadowing) {
                builtin_variable_shadowing(checker, id);
            }
        }
        _ => {}
    }
}
