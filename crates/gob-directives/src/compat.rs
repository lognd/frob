//! v1 compatibility: `note="..."` on `frob:todo` and `reason="..."` on
//! `frob:invariant` are read as the v2 trailing free text and offered a fix.

use gob_rules::{Finding, Fix, FixKind, RuleId, TextEdit};
use gob_text::{FileId, Span, TextRange};

use crate::args::{ArgList, Token};
use crate::rules::Dsl002;

/// `(namespace, verb, v1 key)` triples whose keyed text is now trailing words.
const V1_KEYS: &[(&str, &str, &str)] = &[("frob", "todo", "note"), ("frob", "invariant", "reason")];

/// A v1 key form found in a directive, with the v2 text that replaces it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct V1Key {
    /// Verb the key was written on.
    pub(crate) verb: String,
    /// The v1 key spelling.
    pub(crate) key: String,
    /// Source range from the key's first byte to the value's last byte.
    pub(crate) range: TextRange,
    /// The v2 spelling: the value's words.
    pub(crate) replacement: String,
}

/// Fold a v1 `key="text"` into trailing positional words; returns what it folded.
pub(crate) fn fold_v1_key(ns: &str, verb: &str, args: &mut ArgList) -> Option<V1Key> {
    let (_, _, key) = V1_KEYS.iter().find(|(n, v, _)| *n == ns && *v == verb)?;
    let at = args.keyed.iter().position(|k| k.key == *key)?;
    let found = args.keyed.remove(at);
    for word in found.value.value.split_whitespace() {
        args.positional.push(Token {
            value: word.to_owned(),
            range: found.value.range,
            quoted: false,
        });
    }
    tracing::debug!(verb, key, "v1 key form folded into trailing words");
    Some(V1Key {
        verb: verb.to_owned(),
        key: (*key).to_owned(),
        range: TextRange::new(found.key_range.start(), found.value.range.end()),
        replacement: found
            .value
            .value
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" "),
    })
}

/// The DSL002 finding (with a Deterministic fix) that rewrites `v1` to the v2 form.
pub(crate) fn v1_finding(v1: &V1Key, file: FileId, anchor: &str) -> Finding {
    let meta = &Dsl002::META;
    let id: RuleId = meta
        .id
        .parse()
        .unwrap_or_else(|e| unreachable!("derive validated rule id {}: {e}", meta.id));
    let message = format!(
        "`frob:{}` uses the v1 form `{}=\"...\"`; v2 writes the text after the arguments",
        v1.verb, v1.key
    );
    Finding::new(
        id,
        meta.severity,
        Some(Span::new(file, v1.range)),
        message,
        anchor,
    )
    .with_fix(Fix {
        kind: FixKind::Deterministic,
        title: format!("rewrite `{}=` to the v2 form", v1.key),
        edits: vec![TextEdit {
            file,
            range: v1.range,
            replacement: v1.replacement.clone(),
        }],
    })
}
