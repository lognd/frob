//! The typed effect claim of `frob:effects` (neatness.md section 3); parsed only, never evaluated.

use std::fmt;

use gob_symbols::Symref;
use gob_text::{TextRange, TextSize};

use crate::args::{ArgError, ArgKind, FromArgs, Token};
use crate::scan::DirectiveRecord;

/// One effect atom: a resource access or a control-flow escape.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum EffectAtom {
    /// Reads the state named by the symref.
    Reads(Symref),
    /// Writes the state named by the symref.
    Writes(Symref),
    /// Reads the clock.
    Clock,
    /// Draws randomness.
    Rng,
    /// Reads the process environment.
    Env,
    /// Touches the filesystem (covers `fs.read` and `fs.write`).
    Fs,
    /// Touches the network.
    Net,
    /// Uses standard streams.
    Stdio,
    /// May exit the process.
    Exit,
    /// May panic.
    Panic,
    /// May diverge.
    Diverge,
}

impl EffectAtom {
    /// The bare-word atoms and their spellings.
    const WORDS: [(&'static str, Self); 7] = [
        ("clock", Self::Clock),
        ("rng", Self::Rng),
        ("env", Self::Env),
        ("fs", Self::Fs),
        ("net", Self::Net),
        ("stdio", Self::Stdio),
        ("exit", Self::Exit),
    ];

    /// True for the atoms `total` rules out (`panic`, `diverge`).
    pub const fn breaks_totality(&self) -> bool {
        matches!(self, Self::Panic | Self::Diverge)
    }
}

impl fmt::Display for EffectAtom {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Reads(s) => write!(f, "reads({s})"),
            Self::Writes(s) => write!(f, "writes({s})"),
            Self::Clock => f.write_str("clock"),
            Self::Rng => f.write_str("rng"),
            Self::Env => f.write_str("env"),
            Self::Fs => f.write_str("fs"),
            Self::Net => f.write_str("net"),
            Self::Stdio => f.write_str("stdio"),
            Self::Exit => f.write_str("exit"),
            Self::Panic => f.write_str("panic"),
            Self::Diverge => f.write_str("diverge"),
        }
    }
}

/// The base of an effect claim: a named level or an explicit atom list.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EffectBase {
    /// No effects at all (`none`, the `pure` alias).
    None,
    /// Honest: effects are exactly what the signature admits (`honest`).
    Honest,
    /// Arbitrary input and output (`io`).
    Io,
    /// Anything at all (`any`).
    Any,
    /// A sorted, de-duplicated, non-empty atom list.
    Atoms(Vec<EffectAtom>),
}

/// A parsed `frob:effects` set: a base and the optional `total` suffix.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EffectSet {
    /// The level or atom list.
    pub base: EffectBase,
    /// True when suffixed `total`: no panic and no divergence.
    pub total: bool,
}

impl EffectSet {
    /// The set `none`.
    pub const NONE: Self = Self {
        base: EffectBase::None,
        total: false,
    };
    /// The set `honest`.
    pub const HONEST: Self = Self {
        base: EffectBase::Honest,
        total: false,
    };
}

impl fmt::Display for EffectSet {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match &self.base {
            EffectBase::None => f.write_str("none")?,
            EffectBase::Honest => f.write_str("honest")?,
            EffectBase::Io => f.write_str("io")?,
            EffectBase::Any => f.write_str("any")?,
            EffectBase::Atoms(atoms) => {
                for (i, a) in atoms.iter().enumerate() {
                    if i > 0 {
                        f.write_str(" ")?;
                    }
                    write!(f, "{a}")?;
                }
            }
        }
        if self.total {
            f.write_str(" total")?;
        }
        Ok(())
    }
}

/// The error for the text of `token` between byte offsets `from..to` of its value.
fn invalid(
    name: &str,
    token: &Token,
    (from, to): (usize, usize),
    expected: &'static str,
) -> ArgError {
    // Quoted tokens have escapes, so offsets in the value are not offsets in the file.
    let range = if token.quoted {
        token.range
    } else {
        let base = token.range.start().to_usize();
        let at = |n: usize| TextSize::new(u32::try_from(base + n).unwrap_or(u32::MAX));
        TextRange::new(at(from), at(to))
    };
    ArgError::Invalid {
        name: name.to_owned(),
        value: token.value.get(from..to).unwrap_or(&token.value).to_owned(),
        expected,
        range,
    }
}

/// Parse `reads(X)` or `writes(Y)` when `value` has that shape.
fn parse_access(name: &str, token: &Token) -> Option<Result<EffectAtom, ArgError>> {
    let value = token.value.as_str();
    let (open, ctor): (&str, fn(Symref) -> EffectAtom) = if value.starts_with("reads(") {
        ("reads(", EffectAtom::Reads)
    } else if value.starts_with("writes(") {
        ("writes(", EffectAtom::Writes)
    } else {
        return None;
    };
    let Some(inner) = value
        .strip_prefix(open)
        .and_then(|rest| rest.strip_suffix(')'))
    else {
        return Some(Err(invalid(
            name,
            token,
            (0, value.len()),
            "a closed `reads(SYMREF)` or `writes(SYMREF)`",
        )));
    };
    let bounds = (open.len(), value.len() - 1);
    Some(match Symref::parse(inner) {
        Ok(s) if !inner.is_empty() => Ok(ctor(s)),
        _ => Err(invalid(
            name,
            token,
            bounds,
            "a symref such as `src/a.rs::name` inside the parentheses",
        )),
    })
}

/// Parse one non-`total` token that is not a level keyword.
fn parse_atom(name: &str, token: &Token) -> Result<EffectAtom, ArgError> {
    if let Some(r) = parse_access(name, token) {
        return r;
    }
    match token.value.as_str() {
        "panic" => return Ok(EffectAtom::Panic),
        "diverge" => return Ok(EffectAtom::Diverge),
        v => {
            if let Some((_, a)) = EffectAtom::WORDS.iter().find(|(w, _)| *w == v) {
                return Ok(a.clone());
            }
        }
    }
    Err(invalid(
        name,
        token,
        (0, token.value.len()),
        "an effect atom (reads(X), writes(Y), clock, rng, env, fs, net, stdio, exit, panic, diverge) or `none`, `honest`, `io`, `any`, `total`",
    ))
}

/// The level keyword a token spells, if any.
fn level(word: &str) -> Option<EffectBase> {
    Some(match word {
        "none" => EffectBase::None,
        "honest" => EffectBase::Honest,
        "io" => EffectBase::Io,
        "any" => EffectBase::Any,
        _ => return None,
    })
}

impl FromArgs for EffectSet {
    const KIND: ArgKind = ArgKind::Str;

    fn from_tokens(name: &str, tokens: &[Token]) -> Result<Self, ArgError> {
        let (total, body) = match tokens.split_last() {
            Some((last, body)) if last.value == "total" => (true, body),
            _ => (false, tokens),
        };
        if body.is_empty() {
            return match tokens.first() {
                Some(t) => Err(invalid(
                    name,
                    t,
                    (0, t.value.len()),
                    "an effect set before `total`",
                )),
                None => Err(ArgError::Missing {
                    name: name.to_owned(),
                }),
            };
        }
        if let Some(lvl) = level(&body[0].value) {
            return match body.get(1) {
                Some(extra) => Err(invalid(
                    name,
                    extra,
                    (0, extra.value.len()),
                    "nothing after a level keyword (`none`, `honest`, `io`, `any`) except `total`",
                )),
                None => Ok(Self { base: lvl, total }),
            };
        }
        let mut atoms = Vec::with_capacity(body.len());
        for token in body {
            if level(&token.value).is_some() {
                return Err(invalid(
                    name,
                    token,
                    (0, token.value.len()),
                    "an atom: a level keyword cannot join an atom list",
                ));
            }
            let atom = parse_atom(name, token)?;
            if total && atom.breaks_totality() {
                return Err(invalid(
                    name,
                    token,
                    (0, token.value.len()),
                    "no `panic` or `diverge` in a `total` set",
                ));
            }
            atoms.push(atom);
        }
        atoms.sort();
        atoms.dedup();
        Ok(Self {
            base: EffectBase::Atoms(atoms),
            total,
        })
    }
}

/// Which alias spelled an effects claim, when not `frob:effects` itself.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EffectAlias {
    /// `frob:pure`, meaning `frob:effects none`.
    Pure,
    /// `frob:honest`, meaning `frob:effects honest`.
    Honest,
}

/// An effect claim read from `frob:effects`, `frob:pure` or `frob:honest`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EffectsClaim {
    /// The claimed set (`none` for `pure`, `honest` for `honest`).
    pub set: EffectSet,
    /// The alias the author wrote, or `None` for the full `frob:effects` form.
    pub alias: Option<EffectAlias>,
}

/// The effect claim a record carries, or `None` for any other directive.
///
/// # Errors
///
/// The [`ArgError`] when a `frob:effects` record's set does not parse (the
/// scanner already reports it as PARSE001, so scanned records parse).
pub fn effects_claim(record: &DirectiveRecord) -> Option<Result<EffectsClaim, ArgError>> {
    use crate::Directive;
    use crate::frob::{Effects, Honest, Pure};
    if record.namespace != Effects::NAMESPACE {
        return None;
    }
    let claim = match record.verb.as_str() {
        Effects::VERB => Effects::parse_args(&record.args).map(|e| EffectsClaim {
            set: e.set,
            alias: None,
        }),
        Pure::VERB => Pure::parse_args(&record.args).map(|_| EffectsClaim {
            set: EffectSet::NONE,
            alias: Some(EffectAlias::Pure),
        }),
        Honest::VERB => Honest::parse_args(&record.args).map(|_| EffectsClaim {
            set: EffectSet::HONEST,
            alias: Some(EffectAlias::Honest),
        }),
        _ => return None,
    };
    Some(claim)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn toks(text: &str) -> Vec<Token> {
        let mut at = 0usize;
        let size = |n: usize| TextSize::new(u32::try_from(n).unwrap());
        text.split_whitespace()
            .map(|w| {
                let start = text[at..].find(w).unwrap() + at;
                at = start + w.len();
                Token {
                    value: w.to_owned(),
                    range: TextRange::new(size(start), size(at)),
                    quoted: false,
                }
            })
            .collect()
    }

    fn parse(text: &str) -> Result<EffectSet, ArgError> {
        EffectSet::from_tokens("set", &toks(text))
    }

    #[test]
    fn levels_parse_alone_and_with_total() {
        assert_eq!(parse("none").unwrap(), EffectSet::NONE);
        assert_eq!(parse("honest").unwrap(), EffectSet::HONEST);
        assert_eq!(parse("io").unwrap().base, EffectBase::Io);
        assert_eq!(parse("any").unwrap().base, EffectBase::Any);
        let t = parse("io total").unwrap();
        assert!(t.total && t.base == EffectBase::Io);
    }

    #[test]
    fn atom_lists_combine_sort_and_dedupe() {
        let s = parse("net clock net writes(b.rs::B) reads(a.rs::A) total").unwrap();
        assert!(s.total);
        let EffectBase::Atoms(a) = &s.base else {
            panic!("atoms expected")
        };
        assert_eq!(a.len(), 4);
        assert_eq!(
            s.to_string(),
            "reads(a.rs::A) writes(b.rs::B) clock net total"
        );
    }

    #[test]
    fn panic_and_diverge_parse_without_total() {
        let s = parse("panic diverge exit").unwrap();
        assert!(!s.total);
    }

    #[test]
    fn display_round_trips() {
        for text in [
            "none",
            "io total",
            "reads(a.rs::A) fs",
            "clock rng env total",
        ] {
            assert_eq!(parse(text).unwrap().to_string(), text);
        }
    }

    #[test]
    fn errors_name_the_offending_token() {
        for (text, bad) in [
            ("clock teleport", "teleport"),
            ("none clock", "clock"),
            ("clock io", "io"),
            ("panic total", "panic"),
            ("reads(a.rs::A", "reads(a.rs::A"),
            ("reads()", ""),
            ("total", "total"),
        ] {
            let Err(ArgError::Invalid { value, .. }) = parse(text) else {
                panic!("{text} should be invalid");
            };
            assert_eq!(value, bad, "{text}");
        }
        assert!(matches!(parse(""), Err(ArgError::Missing { .. })));
    }

    #[test]
    fn symref_errors_point_inside_the_parentheses() {
        let Err(ArgError::Invalid { range, .. }) = parse("reads(a b)") else {
            unreachable!()
        };
        // "reads(a b)" is two tokens; the first is unclosed and points at itself.
        assert_eq!(range.start().to_usize(), 0);
        let Err(ArgError::Invalid { range, value, .. }) = parse("writes()") else {
            unreachable!()
        };
        assert_eq!((range.start().to_usize(), range.end().to_usize()), (7, 7));
        assert!(value.is_empty());
    }
}
