//! The z-index layer model LAYER001 judges against: the declared `[layers]` values and the
//! reading of a `z-index` value as an integer literal.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use crunk_spec::DesignSpec;

/// The declared z-index values of `[layers]`, in declaration order; empty when none are declared.
pub fn declared_values(spec: &DesignSpec) -> Vec<i64> {
    spec.layers.values().copied().collect()
}

/// The integer a `z-index` value spells, or `None` for anything else (`auto`, `var(...)`,
/// `calc(...)`, a keyword): only a bare integer literal can be off the declared layers.
pub fn z_index_literal(value: &str) -> Option<i64> {
    let text = value.trim();
    let digits = text.strip_prefix(['+', '-']).unwrap_or(text);
    if digits.is_empty() || !digits.bytes().all(|b| b.is_ascii_digit()) {
        return None;
    }
    text.parse().ok()
}

#[cfg(test)]
mod tests {
    use super::z_index_literal;

    // frob:tests crates/crunk-rules/src/layers/mod.rs::z_index_literal
    #[test]
    fn only_bare_integers_are_literals() {
        assert_eq!(z_index_literal("99"), Some(99));
        assert_eq!(z_index_literal(" -1 "), Some(-1));
        assert_eq!(z_index_literal("+5"), Some(5));
        for other in ["auto", "var(--layer-toast)", "1.5", "", "-", "calc(1 + 2)"] {
            assert_eq!(z_index_literal(other), None, "{other}");
        }
    }
}
