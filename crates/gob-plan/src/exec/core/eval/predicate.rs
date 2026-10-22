//! The word and path predicates: `is`, `exists`, `has attr`, `under` and `in unit`.

// frob:ticket 01M4WGCDG1786P1D7BT26X4K6K
use gob_ir::{AttrValue, Truth};

use super::{
    Datum, Env, Eval, KindTest, Op, Operand, Scalar, StrId, VarId, Verdict, is_canonical_unit,
    unwrap_statement,
};

/// Words that test a string value (`l.target is relative`).
const STRING_WORDS: &[&str] = &["relative", "valid_glob", "integer"];
/// Words that read a boolean field of a node (`f is public`).
const FLAG_WORDS: &[&str] = &["public", "exported"];

/// Whether `is WORD` can be lowered on a variable (`on_field` false) or a field (`on_field`).
pub(crate) fn is_test_word(word: &str, on_field: bool) -> bool {
    if on_field {
        STRING_WORDS.contains(&word)
    } else {
        KindTest::from_word(word).is_some() || FLAG_WORDS.contains(&word)
    }
}

/// Whether the sibling just before `node` is a comment carrying the `frob:<name>` directive `key`.
// frob:ticket 01M539NQGFCK3VJGRBM3H6CT56
fn preceded_by_directive(term: &gob_ir::Term, node: gob_ir::NodeId, key: &str) -> bool {
    let Some(want) = key.strip_prefix("frob:") else {
        return false;
    };
    let Some(parent) = term.node(node).parent() else {
        return false;
    };
    let sibs = term.node(parent).children();
    let Some(i) = sibs.iter().position(|s| *s == node) else {
        return false;
    };
    let hit = i.checked_sub(1).is_some_and(|j| {
        matches!(term.node(sibs[j]).op(),
            gob_ir::Operator::Universal(gob_ir::Universal::Comment { text })
                if super::super::kind::directive_name(text) == Some(want))
    });
    tracing::trace!(key, hit, "has attr: directive comment before node");
    hit
}

/// Whether `s` is a relative reference: no URL scheme and not rooted.
fn is_relative(s: &str) -> bool {
    let scheme = s.split_once(':').is_some_and(|(head, _)| {
        !head.is_empty()
            && head.starts_with(|c: char| c.is_ascii_alphabetic())
            && head
                .chars()
                .all(|c| c.is_ascii_alphanumeric() || matches!(c, '+' | '-' | '.'))
    });
    !scheme && !s.starts_with('/') && !s.starts_with("//")
}

/// Whether `s` parses as a whole integer: an optional sign and digits, surrounding blanks ignored.
fn is_integer(s: &str) -> bool {
    let ok = s.trim().parse::<i64>().is_ok();
    tracing::trace!(value = %s, ok, "integer value predicate");
    ok
}

/// Whether `path` lies under `prefix`, segment by segment (`.`, `/` and `::` separate).
fn is_under(path: &str, prefix: &str) -> bool {
    let segs = |s: &str| -> Vec<String> {
        s.replace("::", "/")
            .split(['.', '/'])
            .filter(|p| !p.is_empty())
            .map(str::to_owned)
            .collect()
    };
    let (p, q) = (segs(path), segs(prefix));
    !q.is_empty() && p.starts_with(&q)
}

impl Eval<'_> {
    /// Dispatches the five word and path predicate ops.
    pub(super) fn predicate_op(&self, op: &Op, env: &Env) -> Verdict {
        match op {
            Op::Is { subject, test } => self.is_op(subject, *test, env),
            Op::Exists { subject } => self.exists_op(subject, env),
            Op::HasAttr { var, attr } => self.has_attr_op(*var, *attr, env),
            Op::Under { subject, prefix } => self.under_op(subject, prefix, env),
            Op::MatchGlobOperand { subject, pattern } => {
                self.glob_operand_op(subject, pattern, env)
            }
            Op::InVocab { var, classes } => self.in_vocab_op(*var, classes, env),
            Op::InUnit { sub, unit } => self.in_unit_op(*sub, *unit, env),
            _ => unreachable!("not a predicate op"),
        }
    }

    /// `subject is test`: kind membership, a boolean field, or a string predicate.
    pub(super) fn is_op(&self, subject: &Operand, test: StrId, env: &Env) -> Verdict {
        let word = self.string(test);
        match *subject {
            Operand::Var(v) => {
                let node = Self::node(env, v);
                if let Some(k) = KindTest::from_word(word) {
                    let target = if k.looks_through_statement() {
                        unwrap_statement(self.rd.model, node)
                    } else {
                        node
                    };
                    return Verdict::certain(k.member(self.rd.model, target) == Some(Truth::Yes));
                }
                match self.rd.field(node, word) {
                    Datum::Known(Scalar::Bool(b)) => Verdict::certain(b),
                    Datum::Absent => Verdict::no(),
                    _ => Verdict::unknown(self.describe(subject, env)),
                }
            }
            _ => match self.datum(subject, env) {
                Datum::Known(Scalar::Str(s)) => Verdict::certain(match word {
                    "relative" => is_relative(&s),
                    "integer" => is_integer(&s),
                    _ => globset::Glob::new(&s).is_ok(),
                }),
                Datum::Absent | Datum::Known(_) | Datum::Node(_) => Verdict::no(),
                Datum::OneOf(_) | Datum::Unknown => Verdict::unknown(self.describe(subject, env)),
            },
        }
    }

    /// `exists subject`: the operand has a value.
    pub(super) fn exists_op(&self, subject: &Operand, env: &Env) -> Verdict {
        match self.datum(subject, env) {
            Datum::Absent => Verdict::no(),
            Datum::Unknown => Verdict::unknown(self.describe(subject, env)),
            _ => Verdict::yes(),
        }
    }

    /// `var has attr "k"`: the node carries the attribute, or the adapter may omit it.
    pub(super) fn has_attr_op(&self, var: VarId, attr: StrId, env: &Env) -> Verdict {
        let term = self.rd.model.term();
        let key = self.string(attr);
        if term.node(Self::node(env, var)).attrs().get(key).is_some() {
            return Verdict::yes();
        }
        if preceded_by_directive(term, Self::node(env, var), key) {
            return Verdict::yes();
        }
        match term
            .node(term.root())
            .attrs()
            .get(gob_ir::reserved::ATTRS_PROVIDED)
        {
            Some(AttrValue::Bool(false)) => Verdict::unknown(super::Doubt::Dynamic {
                node: Some(Self::node(env, var)),
                field: key.to_owned(),
            }),
            _ => Verdict::no(),
        }
    }

    /// The string a path operand stands for: a field value, or a node's name.
    fn path_text(&self, o: &Operand, env: &Env) -> Datum {
        match self.datum(o, env) {
            Datum::Node(n) => self.rd.field(n, "name"),
            d => d,
        }
    }

    /// `subject under prefix`: segment-wise prefix test.
    pub(super) fn under_op(&self, subject: &Operand, prefix: &Operand, env: &Env) -> Verdict {
        match (self.path_text(subject, env), self.path_text(prefix, env)) {
            (Datum::Known(Scalar::Str(a)), Datum::Known(Scalar::Str(b))) => {
                Verdict::certain(is_under(&a, &b))
            }
            (Datum::Unknown | Datum::OneOf(_), _) => Verdict::unknown(self.describe(subject, env)),
            (_, Datum::Unknown | Datum::OneOf(_)) => Verdict::unknown(self.describe(prefix, env)),
            _ => Verdict::no(),
        }
    }

    /// `subject matches pattern` where the glob is read from an operand at run time; an
    /// unreadable or invalid glob is unknown, never a mismatch.
    pub(super) fn glob_operand_op(
        &self,
        subject: &Operand,
        pattern: &Operand,
        env: &Env,
    ) -> Verdict {
        match (self.datum(subject, env), self.datum(pattern, env)) {
            (Datum::Known(Scalar::Str(s)), Datum::Known(Scalar::Str(g))) => {
                match globset::Glob::new(&g) {
                    Ok(glob) => Verdict::certain(glob.compile_matcher().is_match(&s)),
                    Err(e) => {
                        tracing::debug!(glob = %g, error = %e, "invalid glob operand is unknown");
                        Verdict::unknown(self.describe(pattern, env))
                    }
                }
            }
            (Datum::Unknown | Datum::OneOf(_), _) => Verdict::unknown(self.describe(subject, env)),
            (_, Datum::Unknown | Datum::OneOf(_)) => Verdict::unknown(self.describe(pattern, env)),
            _ => Verdict::no(),
        }
    }

    /// `var in knob.V`: the node's name is registered in its language's vocabulary classes.
    pub(super) fn in_vocab_op(&self, var: VarId, classes: &[StrId], env: &Env) -> Verdict {
        let node = Self::node(env, var);
        let Datum::Known(Scalar::Str(name)) = self.rd.field(node, "name") else {
            return Verdict::unknown(super::Doubt::Dynamic {
                node: Some(node),
                field: "name".to_owned(),
            });
        };
        let lang = self.rd.model.term().node(node).lang();
        let hit = classes.iter().any(|&c| {
            matches!(
                gob_ir::registry::callee_vocab(lang, self.string(c)),
                gob_ir::Answer::Exact(set) if set.contains(name.as_str())
            )
        });
        tracing::trace!(%name, lang, hit, "vocabulary membership");
        Verdict::certain(hit)
    }

    /// `sub in unit unit`: `unit` is the nearest enclosing canonical unit of `sub`.
    pub(super) fn in_unit_op(&self, sub: VarId, unit: VarId, env: &Env) -> Verdict {
        let model = self.rd.model;
        let (sub, unit) = (Self::node(env, sub), Self::node(env, unit));
        let nearest = model
            .term()
            .ancestors(sub)
            .into_iter()
            .find(|&p| is_canonical_unit(model, p));
        Verdict::certain(nearest == Some(unit))
    }
}

#[cfg(test)]
mod tests {
    use super::{is_relative, is_under};

    // frob:tests crates/gob-plan/src/exec/core/eval/predicate.rs::is_under
    #[test]
    fn under_is_segment_wise() {
        assert!(is_under("a.b", "a"));
        assert!(is_under("a/b/c", "a/b"));
        assert!(is_under("std::io::Read", "std"));
        assert!(is_under("a", "a"));
        assert!(!is_under("ab", "a"));
        assert!(!is_under("requests", "requests_mock"));
        assert!(!is_under("a", ""));
    }

    // frob:tests crates/gob-plan/src/exec/core/eval/predicate.rs::is_relative
    #[test]
    fn relative_has_no_scheme_or_root() {
        assert!(is_relative("docs/a.md"));
        assert!(is_relative("../a.md#x"));
        assert!(!is_relative("https://x.org"));
        assert!(!is_relative("mailto:a@b"));
        assert!(!is_relative("/abs"));
    }
}
