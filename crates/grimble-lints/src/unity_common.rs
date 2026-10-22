//! Shared plumbing of the `UNITY3xx` Unity rules: the finding shape, preprocessor-aware tree
//! walking and the class loop, so each rule module only holds its own vocabulary.
//!
//! `#if` conditions are evaluated three-valued against the defines a rule knows. A symbol the rule
//! does not know (`UNITY_EDITOR`) is Unknown, so both branches are scanned rather than guessing.

// frob:ticket 01M4D94ZPDYBATXNCVY3XRQ6RM

use gob_languages::{Language, ParseLimits, ParseResult, ParsedTree, parse};
use gob_text::TextRange;
use tree_sitter::Node;

use crate::res::{Certainty, ScanError, text as node_text};
use crate::unity::named_children;

/// One Unity rule hit: the rule, where, how sure, and what to tell the author.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// The rule id (`UNITY301`).
    pub rule: &'static str,
    /// The offending expression, as byte offsets in the scanned text.
    pub range: TextRange,
    /// Whether the syntax alone decides it; an Unknown finding is Unresolved, never Warn.
    pub certainty: Certainty,
    /// The author-facing explanation.
    pub message: String,
}

/// A three-valued truth for a preprocessor condition.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum Tri {
    True,
    False,
    Unknown,
}

impl Tri {
    fn not(self) -> Self {
        match self {
            Self::True => Self::False,
            Self::False => Self::True,
            Self::Unknown => Self::Unknown,
        }
    }

    fn and(self, o: Self) -> Self {
        match (self, o) {
            (Self::False, _) | (_, Self::False) => Self::False,
            (Self::True, Self::True) => Self::True,
            _ => Self::Unknown,
        }
    }

    fn or(self, o: Self) -> Self {
        match (self, o) {
            (Self::True, _) | (_, Self::True) => Self::True,
            (Self::False, Self::False) => Self::False,
            _ => Self::Unknown,
        }
    }
}

/// Splits a condition into symbols and operators; `None` on anything else.
fn tokens(cond: &str) -> Option<Vec<String>> {
    let chars: Vec<char> = cond.chars().collect();
    let mut out = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        let next = chars.get(i + 1).copied();
        if c.is_whitespace() {
            i += 1;
        } else if matches!(
            (c, next),
            ('&', Some('&')) | ('|', Some('|')) | ('=', Some('='))
        ) || (c == '!' && next == Some('='))
        {
            out.push(chars[i..i + 2].iter().collect());
            i += 2;
        } else if matches!(c, '(' | ')' | '!') {
            out.push(c.to_string());
            i += 1;
        } else if c.is_alphanumeric() || c == '_' {
            let end = (i..chars.len())
                .find(|&j| !(chars[j].is_alphanumeric() || chars[j] == '_'))
                .unwrap_or(chars.len());
            out.push(chars[i..end].iter().collect());
            i = end;
        } else {
            return None;
        }
    }
    Some(out)
}

/// A recursive-descent evaluator over `||`, `&&`, `!`, parentheses and symbols.
struct Cond<'a> {
    toks: Vec<String>,
    pos: usize,
    defines: &'a [(&'a str, bool)],
}

impl Cond<'_> {
    fn peek(&self) -> Option<&str> {
        self.toks.get(self.pos).map(String::as_str)
    }

    fn or(&mut self) -> Option<Tri> {
        let mut v = self.and()?;
        while self.peek() == Some("||") {
            self.pos += 1;
            v = v.or(self.and()?);
        }
        Some(v)
    }

    fn and(&mut self) -> Option<Tri> {
        let mut v = self.unary()?;
        while self.peek() == Some("&&") {
            self.pos += 1;
            v = v.and(self.unary()?);
        }
        Some(v)
    }

    fn unary(&mut self) -> Option<Tri> {
        let tok = self.peek()?.to_owned();
        self.pos += 1;
        match tok.as_str() {
            "!" => Some(self.unary()?.not()),
            "(" => {
                let v = self.or()?;
                (self.peek() == Some(")")).then(|| self.pos += 1)?;
                Some(v)
            }
            "true" => Some(Tri::True),
            "false" => Some(Tri::False),
            t if t.chars().all(|c| c.is_alphanumeric() || c == '_') => {
                Some(self.defines.iter().find(|(name, _)| *name == t).map_or(
                    Tri::Unknown,
                    |(_, on)| if *on { Tri::True } else { Tri::False },
                ))
            }
            _ => None,
        }
    }
}

/// Evaluates a preprocessor condition; anything unparseable is Unknown.
pub(crate) fn eval_condition(cond: &str, defines: &[(&str, bool)]) -> Tri {
    let Some(toks) = tokens(cond) else {
        return Tri::Unknown;
    };
    let mut c = Cond {
        toks,
        pos: 0,
        defines,
    };
    match c.or() {
        Some(v) if c.pos == c.toks.len() => v,
        _ => Tri::Unknown,
    }
}

/// The nodes a (possibly preprocessor) child stands for: the live branches of `#if` chains.
fn expand<'t>(n: Node<'t>, src: &str, defines: &[(&str, bool)]) -> Vec<Node<'t>> {
    match n.kind() {
        "preproc_if" | "preproc_elif" => {
            let cond = n.child_by_field_name("condition");
            let alt = n.child_by_field_name("alternative");
            let tri = cond.map_or(Tri::Unknown, |c| eval_condition(node_text(c, src), defines));
            tracing::debug!(?tri, "preprocessor condition evaluated");
            let mut out = Vec::new();
            if tri != Tri::False {
                out.extend(named_children(n).into_iter().filter(|c| {
                    Some(c.id()) != cond.map(|x| x.id()) && Some(c.id()) != alt.map(|x| x.id())
                }));
            }
            if tri != Tri::True {
                out.extend(alt);
            }
            out.into_iter()
                .flat_map(|c| expand(c, src, defines))
                .collect()
        }
        "preproc_else" => named_children(n)
            .into_iter()
            .flat_map(|c| expand(c, src, defines))
            .collect(),
        _ => vec![n],
    }
}

/// The named children of `n` with every `#if` chain replaced by its live branches.
pub(crate) fn live_named<'t>(n: Node<'t>, src: &str, defines: &[(&str, bool)]) -> Vec<Node<'t>> {
    named_children(n)
        .into_iter()
        .flat_map(|c| expand(c, src, defines))
        .collect()
}

/// Parses `text` as C#; `Ok(None)` for another language.
fn parse_csharp(language: Language, text: &str) -> Result<Option<ParsedTree>, ScanError> {
    if language != Language::CSharp {
        return Ok(None);
    }
    match parse(language, text, &ParseLimits::default()) {
        ParseResult::Parsed(tree) => Ok(Some(tree)),
        ParseResult::Unresolved(u) => Err(ScanError::Parse(u.reason.to_string())),
    }
}

/// Calls `visit` on every live node of a C# file (none for another language), in tree order.
///
/// # Errors
///
/// [`ScanError::Parse`] when the file does not parse within the limits.
pub(crate) fn walk(
    language: Language,
    text: &str,
    defines: &[(&str, bool)],
    mut visit: impl FnMut(Node<'_>),
) -> Result<(), ScanError> {
    let Some(tree) = parse_csharp(language, text)? else {
        return Ok(());
    };
    let mut stack = vec![tree.root()];
    while let Some(n) = stack.pop() {
        visit(n);
        let mut kids = live_named(n, text, defines);
        kids.reverse();
        stack.extend(kids);
    }
    Ok(())
}
