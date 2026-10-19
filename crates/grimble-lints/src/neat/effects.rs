//! The `effects(unit)` capability: ambient effects a Rust unit's calls perform.

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP

use std::collections::BTreeSet;

use gob_ir::Answer;

use super::unit::Unit;
use super::{Options, Verdict};

/// An ambient effect atom of the callee vocabulary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Atom {
    /// Reads the clock.
    Clock,
    /// Draws randomness.
    Rng,
    /// Reads the process environment.
    Env,
    /// Touches the file system.
    Fs,
    /// Touches the network.
    Net,
    /// Reads or writes the standard streams.
    Stdio,
    /// Ends the process.
    Exit,
}

impl Atom {
    /// The atom a `frob:effects` word names.
    pub fn from_word(word: &str) -> Option<Self> {
        Some(match word {
            "clock" => Self::Clock,
            "rng" => Self::Rng,
            "env" => Self::Env,
            "fs" => Self::Fs,
            "net" => Self::Net,
            "stdio" => Self::Stdio,
            "exit" => Self::Exit,
            _ => return None,
        })
    }

    /// The word spelling the atom.
    pub fn word(self) -> &'static str {
        match self {
            Self::Clock => "clock",
            Self::Rng => "rng",
            Self::Env => "env",
            Self::Fs => "fs",
            Self::Net => "net",
            Self::Stdio => "stdio",
            Self::Exit => "exit",
        }
    }
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

/// True when a call `path` names the vocabulary `key` (equal or a trailing-segment match).
fn matches(key: &str, path: &str) -> bool {
    path.contains("::") && (key == path || key.ends_with(&format!("::{path}")))
}

/// The verdict of an effects answer against a ceiling.
pub fn verdict(answer: &Answer<EffectSet>, ceiling: &Ceiling) -> Verdict {
    match (answer.lo(), answer.hi()) {
        (Some(lo), Some(hi)) => {
            if !lo.atoms.is_subset(ceiling) {
                Verdict::Contradicted
            } else if !hi.open && hi.atoms.is_subset(ceiling) {
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
