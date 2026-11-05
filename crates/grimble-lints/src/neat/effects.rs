//! The `effects(unit)` capability: ambient effects a Rust unit's calls perform.

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP

use std::collections::BTreeSet;

use gob_ir::Answer;

use super::unit::Unit;
use super::{Options, Verdict};

/// A registry atom (`clock`, `fs.read`, ...): the canonical name `gob_ir::registry` knows it by.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct Atom(&'static str);

impl Atom {
    /// The registry atom a `frob:effects` word names (an alias resolves), or `None`.
    pub fn from_word(word: &str) -> Option<Self> {
        let atom = gob_ir::registry::canonical(word).map(Self);
        tracing::trace!(word, found = atom.is_some(), "effects word looked up");
        atom
    }

    /// The canonical registry name of the atom.
    pub fn word(self) -> &'static str {
        self.0
    }

    /// Whether a ceiling allows this atom: it names the atom or an atom it nests under.
    pub fn within(self, ceiling: &Ceiling) -> bool {
        ceiling
            .iter()
            .any(|c| c.0 == self.0 || self.0.strip_prefix(c.0).is_some_and(|r| r.starts_with('.')))
    }
}

/// The default callee vocabulary: every Rust ambient-source name of the registry with its atom.
pub fn registry_vocabulary() -> Vec<(String, Atom)> {
    let mut out = Vec::new();
    for class in gob_ir::registry::AMBIENT_CLASSES {
        for (atom, name) in gob_ir::registry::callee_names("rust", class) {
            if name.starts_with('.') || name.contains('.') || name.ends_with('*') {
                continue; // receiver-typed or wildcard forms are the binder's, not a path match
            }
            out.push((name.to_owned(), Atom(atom)));
        }
    }
    tracing::debug!(
        entries = out.len(),
        "neat vocabulary derived from the registry"
    );
    out
}

/// The atoms a claim allows.
pub type Ceiling = BTreeSet<Atom>;

/// A set of atoms; `open` marks a set that unresolved callees may extend.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct EffectSet {
    /// The atoms.
    pub atoms: BTreeSet<Atom>,
    /// True when the set is an upper bound with unknown additions.
    pub open: bool,
}

/// The effects of `unit`: Exact when every callee resolved, else Bounds with an open `hi`.
pub fn effects(
    unit: &Unit<'_>,
    all: &[Unit<'_>],
    src: &str,
    options: &Options,
) -> Answer<EffectSet> {
    let mut atoms = BTreeSet::new();
    let mut open = false;
    let mut seen = BTreeSet::new();
    collect(unit, all, src, options, &mut seen, &mut atoms, &mut open);
    if open {
        Answer::Bounds {
            lo: EffectSet {
                atoms: atoms.clone(),
                open: false,
            },
            hi: EffectSet { atoms, open: true },
        }
    } else {
        Answer::Exact(EffectSet { atoms, open: false })
    }
}

fn collect(
    unit: &Unit<'_>,
    all: &[Unit<'_>],
    src: &str,
    options: &Options,
    seen: &mut BTreeSet<String>,
    atoms: &mut BTreeSet<Atom>,
    open: &mut bool,
) {
    if !seen.insert(unit.name.clone()) {
        return;
    }
    let Some(body) = unit.node.child_by_field_name("body") else {
        return;
    };
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if n.kind() == "call_expression"
            && let Some(f) = n.child_by_field_name("function")
        {
            resolve(
                &src[f.byte_range()],
                f.kind(),
                all,
                src,
                options,
                seen,
                atoms,
                open,
            );
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
}

#[allow(clippy::too_many_arguments)] // one recursion state, split would only rename it
fn resolve(
    callee: &str,
    kind: &str,
    all: &[Unit<'_>],
    src: &str,
    options: &Options,
    seen: &mut BTreeSet<String>,
    atoms: &mut BTreeSet<Atom>,
    open: &mut bool,
) {
    let path: String = callee.split_whitespace().collect();
    if let Some((_, atom)) = options
        .vocabulary
        .iter()
        .find(|(key, _)| matches(key, &path))
    {
        atoms.insert(*atom);
        return;
    }
    let last = path.rsplit("::").next().unwrap_or(&path);
    if last.chars().next().is_some_and(char::is_uppercase) {
        return; // a tuple struct or variant constructor
    }
    if kind == "identifier"
        && let Some(local) = all.iter().find(|u| u.name == path)
    {
        collect(local, all, src, options, seen, atoms, open);
        return;
    }
    *open = true;
}

/// The ambient calls the unit's own body makes (not its callees'), as call node and atom.
pub fn direct_hits<'t>(
    unit: &Unit<'t>,
    src: &str,
    options: &Options,
) -> Vec<(tree_sitter::Node<'t>, Atom)> {
    let Some(body) = unit.node.child_by_field_name("body") else {
        return Vec::new();
    };
    let mut out = Vec::new();
    let mut stack = vec![body];
    while let Some(n) = stack.pop() {
        if n.kind() == "call_expression"
            && let Some(f) = n.child_by_field_name("function")
        {
            let path: String = src[f.byte_range()].split_whitespace().collect();
            if let Some((_, atom)) = options.vocabulary.iter().find(|(k, _)| matches(k, &path)) {
                out.push((n, *atom));
            }
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    out.sort_by_key(|(n, _)| n.start_byte());
    out
}

/// True when a call `path` names the vocabulary `key`: the registry rule (equal or behind extra
/// leading segments), or a configured longer `key` that ends in the call's own path.
fn matches(key: &str, path: &str) -> bool {
    path.contains("::")
        && (gob_ir::registry::callee_matches(key, path) || key.ends_with(&format!("::{path}")))
}

/// The verdict of an effects answer against a ceiling.
pub fn verdict(answer: &Answer<EffectSet>, ceiling: &Ceiling) -> Verdict {
    match (answer.lo(), answer.hi()) {
        (Some(lo), Some(hi)) => {
            if !lo.atoms.iter().all(|a| a.within(ceiling)) {
                Verdict::Contradicted
            } else if !hi.open && hi.atoms.iter().all(|a| a.within(ceiling)) {
                Verdict::Verified
            } else {
                Verdict::Unverified
            }
        }
        _ => Verdict::Unverified,
    }
}

/// The certain atoms of an answer, for messages.
pub fn describe(answer: &Answer<EffectSet>) -> String {
    answer
        .lo()
        .map(|s| {
            s.atoms
                .iter()
                .map(|a| a.word())
                .collect::<Vec<_>>()
                .join(" ")
        })
        .unwrap_or_default()
}
