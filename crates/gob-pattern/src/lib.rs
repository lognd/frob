//! The declarative rule engine over U terms (rules.md section 3, level 2).
//!
//! Decision of the `Doc`-over-U spike: U terms are matched by an in-house structural matcher,
//! not by implementing ast-grep's `Doc` trait. The U level needs `role`, `callee` and the
//! per-language vocabularies, which the tree-sitter oriented trait cannot express, and an
//! in-house matcher keeps the combinators identical for every language. Grammar-level
//! `pattern` rules (level 1) live in [`grammar`]: the pattern is parsed with the language's own
//! tree-sitter grammar, `$X` / `$$$ARGS` are metavariables, and a `fix` template rewrites the match.
//!
//! A rule file is TOML (`rules/*.grl.toml`); a rule with `language = "*"` runs on terms of
//! every language and fires on each node the `rule` table matches.

// frob:ticket 01M3Z714QT3QXEAJAK9JDDEB70
// frob:ticket 01M4PPRHCTN3TZ0TJF8NRQ4KHD

pub mod grammar;

use std::ops::Range;

use gob_ir::{Answer, Node, NodeId, Operator, Term, Universal, registry};
use grammar::{Edit, GrammarError, Pattern};
use serde::Deserialize;

/// Why a rule file could not be compiled.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum PatternError {
    /// The TOML did not parse or has an unknown key.
    #[error("rule file is malformed: {0}")]
    Malformed(String),
    /// The rule id is not of the form `GPOLnnn`.
    #[error("rule id `{0}` must look like GPOL001")]
    BadId(String),
    /// A grammar-level pattern or fix did not compile.
    #[error("pattern rule: {0}")]
    Grammar(#[from] GrammarError),
    /// A `pattern` rule must name one concrete language, not `*`.
    #[error("a `pattern` rule needs a concrete `language`, not `*`")]
    PatternNeedsLanguage,
    /// A `fix` was given on a rule whose top table has no `pattern`.
    #[error("`fix` needs the rule table to set `pattern`")]
    FixWithoutPattern,
    /// A combinator table is empty or a rule table sets nothing.
    #[error("a rule table must set at least one key")]
    EmptyRule,
}

/// One node test plus combinators; every key that is set must hold.
#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct Rule {
    /// Grammar-level pattern with `$X` / `$$$ARGS` metavariables; matched by [`RuleFile::find_source`].
    pub pattern: Option<String>,
    /// The operator kind (`apply` kind, `bind` kind, `unit` kind, ...).
    pub kind: Option<String>,
    /// The role: a unit's role or the `role` attribute of any node.
    pub role: Option<String>,
    /// The head of an `apply`: a spelled name or a callee vocabulary class.
    pub callee: Option<String>,
    /// All of these rules hold at the node.
    #[serde(default)]
    pub all: Vec<Rule>,
    /// At least one of these rules holds at the node.
    #[serde(default)]
    pub any: Vec<Rule>,
    /// The rule does not hold at the node.
    pub not: Option<Box<Rule>>,
    /// Some ancestor satisfies the rule.
    pub inside: Option<Box<Rule>>,
    /// Some descendant satisfies the rule.
    pub has: Option<Box<Rule>>,
}

/// A compiled rule file.
#[derive(Debug, Clone, Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
pub struct RuleFile {
    /// Rule id, `GPOLnnn`.
    pub id: String,
    /// Optional slug alias.
    pub alias: Option<String>,
    /// A language tag or `*` for every language.
    pub language: String,
    /// Severity spelled in lowercase.
    pub severity: String,
    /// The message shown on a finding.
    pub message: String,
    /// The matching rule.
    pub rule: Rule,
    /// Fix template over the pattern's metavariables; needs `rule.pattern`.
    pub fix: Option<String>,
}

/// One firing of a grammar-level rule over source text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Finding {
    /// Byte range of the matched node.
    pub range: Range<usize>,
    /// The rule message.
    pub message: String,
    /// The rewrite, when the rule has a `fix`.
    pub edit: Option<Edit>,
}

impl RuleFile {
    /// Parse and validate a `*.grl.toml` document.
    ///
    /// # Errors
    ///
    /// [`PatternError`] when the TOML is malformed, the id is not `GPOLnnn`, a rule uses a
    /// grammar-level `pattern`, or a rule table sets nothing.
    pub fn parse(text: &str) -> Result<Self, PatternError> {
        let file: Self =
            toml::from_str(text).map_err(|e| PatternError::Malformed(e.message().to_owned()))?;
        let digits = file.id.strip_prefix("GPOL").unwrap_or("");
        if digits.len() < 3 || !digits.bytes().all(|b| b.is_ascii_digit()) {
            return Err(PatternError::BadId(file.id));
        }
        file.rule.validate()?;
        if file.rule.pattern.is_some() {
            file.compile_pattern()?;
        } else if file.fix.is_some() {
            return Err(PatternError::FixWithoutPattern);
        }
        Ok(file)
    }

    /// Compile the top-level pattern for the rule's language, if there is one.
    fn compile_pattern(&self) -> Result<Option<Pattern>, PatternError> {
        let Some(text) = self.rule.pattern.as_deref() else {
            return Ok(None);
        };
        if self.language == "*" {
            return Err(PatternError::PatternNeedsLanguage);
        }
        Ok(Some(Pattern::compile(&self.language, text)?))
    }

    /// Fire a grammar-level rule over `source`: each match, with its rewrite when `fix` is set.
    ///
    /// A rule without `pattern` yields nothing here; run [`RuleFile::find`] on a term instead.
    ///
    /// # Errors
    ///
    /// [`PatternError::Grammar`] when the source does not parse or the fix names an unbound
    /// metavariable.
    pub fn find_source(&self, source: &str) -> Result<Vec<Finding>, PatternError> {
        let Some(pattern) = self.compile_pattern()? else {
            return Ok(Vec::new());
        };
        let mut out = Vec::new();
        for m in pattern.find(source)? {
            let edit = match &self.fix {
                Some(t) => Some(Edit {
                    range: m.range.clone(),
                    text: grammar::render(t, &m.bindings)?,
                }),
                None => None,
            };
            tracing::debug!(rule = %self.id, start = m.range.start, "pattern rule fired");
            out.push(Finding {
                range: m.range,
                message: self.message.clone(),
                edit,
            });
        }
        Ok(out)
    }

    /// Every node of `term` the rule fires on, in arena order; empty when the language differs.
    pub fn find(&self, term: &Term) -> Vec<NodeId> {
        term.ids()
            .filter(|&n| {
                (self.language == "*" || term.node(n).lang() == self.language)
                    && self.rule.matches(term, n)
            })
            .collect()
    }
}

impl Rule {
    fn validate(&self) -> Result<(), PatternError> {
        let nested = self.all.iter().chain(&self.any);
        let boxed = [&self.not, &self.inside, &self.has].into_iter().flatten();
        let leaf = self.pattern.is_some()
            || self.kind.is_some()
            || self.role.is_some()
            || self.callee.is_some();
        if !leaf && nested.clone().next().is_none() && boxed.clone().next().is_none() {
            return Err(PatternError::EmptyRule);
        }
        for r in nested.chain(boxed.map(|r| &**r)) {
            r.validate()?;
        }
        Ok(())
    }

    /// Whether the rule holds at node `at`.
    pub fn matches(&self, term: &Term, at: NodeId) -> bool {
        let node = term.node(at);
        // A grammar-level pattern has no meaning on a U term; it never holds here.
        self.pattern.is_none()
            && self
                .kind
                .as_deref()
                .is_none_or(|k| kind_of(node) == Some(k))
            && self
                .role
                .as_deref()
                .is_none_or(|r| role_of(node) == Some(r))
            && self
                .callee
                .as_deref()
                .is_none_or(|c| callee_is(term, node, c))
            && self.all.iter().all(|r| r.matches(term, at))
            && (self.any.is_empty() || self.any.iter().any(|r| r.matches(term, at)))
            && self.not.as_ref().is_none_or(|r| !r.matches(term, at))
            && self.inside.as_ref().is_none_or(|r| {
                std::iter::successors(node.parent(), |&p| term.node(p).parent())
                    .any(|p| r.matches(term, p))
            })
            && self
                .has
                .as_ref()
                .is_none_or(|r| descendants(term, at).any(|d| r.matches(term, d)))
    }
}

fn descendants(term: &Term, at: NodeId) -> impl Iterator<Item = NodeId> + '_ {
    let mut stack: Vec<NodeId> = term.node(at).children().to_vec();
    std::iter::from_fn(move || {
        let n = stack.pop()?;
        stack.extend(term.node(n).children());
        Some(n)
    })
}

fn kind_of(node: &Node) -> Option<&str> {
    match node.op() {
        Operator::Universal(u) => match u {
            Universal::Unit { kind, .. }
            | Universal::Anon { kind }
            | Universal::Apply { kind }
            | Universal::Bind { kind, .. }
            | Universal::Lit { kind, .. }
            | Universal::Region { kind }
            | Universal::Phase { kind }
            | Universal::Hole { kind } => Some(kind),
            Universal::Group { .. } => Some("group"),
            Universal::Ref { .. } => Some("ref"),
            Universal::Attr { .. } => Some("attr"),
            Universal::Comment { .. } => Some("comment"),
            Universal::Opaque { .. } => Some("opaque"),
        },
        Operator::Adapter(_) => None,
    }
}

fn role_of(node: &Node) -> Option<&str> {
    match node.op() {
        Operator::Universal(Universal::Unit { role, .. }) => Some(role),
        _ => node.attrs().get_str("role"),
    }
}

/// The head (child 0) of an `apply` is a `ref` spelled `want`, or in the vocabulary class
/// `want` of the node's language.
fn callee_is(term: &Term, node: &Node, want: &str) -> bool {
    if !matches!(node.op(), Operator::Universal(Universal::Apply { .. })) {
        return false;
    }
    let Some(&head) = node.children().first() else {
        return false;
    };
    let Operator::Universal(Universal::Ref { name }) = term.node(head).op() else {
        return false;
    };
    name == want
        || matches!(registry::callee_vocab(node.lang(), want),
            Answer::Exact(set) if set.contains(name.as_str()))
}
