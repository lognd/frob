// The dispatcher before review (ruff PR 29076): the class-scope reasoning lives in the arm.
fn expression(expr: &Expr, checker: &mut Checker) {
    match expr {
        Expr::Name(id) => {
            let scope = checker.semantic.current_scope();
            let is_class_attribute = scope.kind.is_class()
                && scope.get(id).is_none_or(|b| matches!(checker.semantic.binding(b).kind, Assignment));
            if !is_class_attribute {
                if checker.is_rule_enabled(Rule::BuiltinVariableShadowing) {
                    builtin_variable_shadowing(checker, id);
                }
            }
        }
        _ => {}
    }
}
