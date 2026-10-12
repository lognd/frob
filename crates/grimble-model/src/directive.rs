//! Directives inside .grmb comments (grmb-spec 2.3 and 8).
//!
//! The shared `gob-directives` scanner is tied to tree-sitter languages (its comment
//! discovery is private and keyed by `gob_languages::Language`), so this module reads
//! the comment lines of the hand-written lexer with the same line rule (a directive is a
//! comment line whose text starts with `<namespace>:<verb>`) and validates verbs against
//! the shared registry plus the verbs grmb-spec 8.2 adds.

// frob:ticket 01M3Z713VGKF4Z0JJ3263XJMC3
// frob:ticket 01M4GK42XB93XT5TFDQDRQ36JC

use gob_directives::{all_directives, is_full_ulid, is_v1_alias, looks_like_ticket_ref};

use crate::lex::{Comment, CommentKind};
use crate::span::Span;

/// Namespaces whose directives bind to .grmb entities.
pub const NAMESPACES: [&str; 2] = ["frob", "grimble"];

/// The `frob:` verbs a .grmb file accepts beyond the registered ones (grmb-spec 8.2).
const FROB_EXTRA: [&str; 12] = [
    "decision",
    "deprecated",
    "until",
    "effects",
    "pure",
    "honest",
    "core",
    "shell",
    "hook",
    "dispatcher",
    "idempotent",
    "tests",
];

/// Verbs that are code-side only and are MDL013 in a .grmb comment.
const MDL013_VERBS: [(&str, &str); 9] = [
    ("grimble", "accept"),
    ("grimble", "defer"),
    ("grimble", "hotfix"),
    ("grimble", "node"),
    ("grimble", "channel"),
    ("grimble", "boundary"),
    ("grimble", "effect"),
    ("frob", "accept"),
    ("frob", "defer"),
];

/// A directive found on a comment line.
#[derive(Clone, PartialEq, Eq, Debug)]
pub struct DirectiveHit {
    /// Index of the comment it was found in.
    pub comment: usize,
    /// Namespace (`frob`).
    pub namespace: String,
    /// Verb (`doc`).
    pub verb: String,
    /// The raw argument text, trimmed.
    pub args: String,
    /// The span of the directive text.
    pub span: Span,
    /// A problem with it, as `(rule id, message)`; the directive is still bound.
    pub problem: Option<(&'static str, String)>,
}

impl DirectiveHit {
    /// `namespace:verb`.
    pub fn qualified(&self) -> String {
        format!("{}:{}", self.namespace, self.verb)
    }
}

/// The text lines of a comment with their byte offsets (prefix markers stripped).
fn lines(c: &Comment) -> Vec<(usize, &str)> {
    let mut out = Vec::new();
    match c.kind {
        CommentKind::Doc => {}
        CommentKind::Line => {
            let body = c.text.trim_start_matches('/');
            let off = c.span.start + (c.text.len() - body.len());
            out.push((off, body));
        }
        CommentKind::Block => {
            let inner = c
                .text
                .strip_prefix("/*")
                .and_then(|t| t.strip_suffix("*/").or(Some(t)))
                .unwrap_or(&c.text);
            let mut pos = 2;
            for line in inner.split('\n') {
                let lead = line.len() - line.trim_start().len();
                let mut t = &line[lead..];
                let mut skip = lead;
                if let Some(rest) = t.strip_prefix('*') {
                    skip += 1;
                    t = rest;
                }
                out.push((c.span.start + pos + skip, t));
                pos += line.len() + 1;
            }
        }
    }
    out
}

fn is_word(s: &str, dash: bool) -> bool {
    !s.is_empty()
        && s.bytes().all(|b| {
            b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'_' || (dash && b == b'-')
        })
}

fn known_verb(ns: &str, verb: &str) -> bool {
    match ns {
        "frob" => {
            FROB_EXTRA.contains(&verb)
                || all_directives().any(|m| m.namespace == "frob" && m.verb == verb)
        }
        "grimble" => verb == "binds",
        _ => false,
    }
}

fn check_args(ns: &str, verb: &str, args: &str) -> Option<(&'static str, String)> {
    let first = args.split_whitespace().next();
    match (ns, verb) {
        ("frob", "ticket" | "todo") => match first {
            None => Some(("PARSE001", format!("`{ns}:{verb}` needs a ticket id"))),
            // frob:ticket 01M4GK42XB93XT5TFDQDRQ36JC
            Some(t) if is_full_ulid(t) || is_v1_alias(t) => None,
            Some(t) if looks_like_ticket_ref(t) => Some((
                "DSL002",
                format!(
                    "`{ns}:{verb}` carries abbreviated ticket id `{t}`; only full ULIDs persist"
                ),
            )),
            Some(t) => Some((
                "PARSE001",
                format!("`{ns}:{verb}`: `{t}` is not a ticket id"),
            )),
        },
        ("frob", "doc" | "tests") | ("grimble", "binds") if first.is_none() => {
            Some(("PARSE001", format!("`{ns}:{verb}` needs an argument")))
        }
        _ => None,
    }
}

/// Finds the directives of every non-doc comment of a file.
pub fn scan(comments: &[Comment]) -> Vec<DirectiveHit> {
    let mut out = Vec::new();
    for (ci, c) in comments.iter().enumerate() {
        for (off, text) in lines(c) {
            let t = text.trim();
            let lead = text.len() - text.trim_start().len();
            let Some(colon) = t.find(':') else {
                continue;
            };
            let ns = &t[..colon];
            if !is_word(ns, false) || !NAMESPACES.contains(&ns) {
                continue;
            }
            let after = &t[colon + 1..];
            let vlen = after.find(char::is_whitespace).unwrap_or(after.len());
            let verb = &after[..vlen];
            let args = after[vlen..].trim().to_owned();
            let start = off + lead;
            let span = Span::new(start, start + t.len());
            let problem = if verb.is_empty() {
                Some(("PARSE001", format!("`{ns}:` is missing a verb")))
            } else if !is_word(verb, true) {
                Some((
                    "PARSE001",
                    format!(
                        "malformed verb `{verb}`; expected lowercase letters, digits, `_` and `-`"
                    ),
                ))
            } else if MDL013_VERBS.contains(&(ns, verb)) {
                Some((
                    "MDL013",
                    format!(
                        "`{ns}:{verb}` is not accepted in a .grmb comment; use the clause form (grmb-spec 7 and 8.2)"
                    ),
                ))
            } else if !known_verb(ns, verb) {
                Some(("DSL001", format!("unknown directive `{ns}:{verb}`")))
            } else {
                check_args(ns, verb, &args)
            };
            tracing::trace!(ns, verb, ?problem, "grmb directive");
            out.push(DirectiveHit {
                comment: ci,
                namespace: ns.to_owned(),
                verb: verb.to_owned(),
                args,
                span,
                problem,
            });
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lex::lex;

    #[test]
    fn finds_line_and_block_directives() {
        let l = lex(
            "// frob:doc docs/x.md#a\n/* hello\n * grimble:binds a.rs::f\n */\n// prose frob:doc x\n",
        );
        let hits = scan(&l.comments);
        assert_eq!(hits.len(), 2);
        assert_eq!(hits[0].qualified(), "frob:doc");
        assert_eq!(hits[1].qualified(), "grimble:binds");
        assert_eq!(hits[1].args, "a.rs::f");
        assert!(hits.iter().all(|h| h.problem.is_none()));
    }

    #[test]
    fn code_side_verbs_are_mdl013() {
        let l = lex("// grimble:accept SYS004 because=\"x\"\n// frob:nope\n// frob:\n");
        let hits = scan(&l.comments);
        assert_eq!(hits[0].problem.as_ref().map(|p| p.0), Some("MDL013"));
        assert_eq!(hits[1].problem.as_ref().map(|p| p.0), Some("DSL001"));
        assert_eq!(hits[2].problem.as_ref().map(|p| p.0), Some("PARSE001"));
    }

    #[test]
    fn v1_ticket_aliases_are_accepted_but_abbreviations_are_not() {
        let l = lex(
            "// frob:ticket T-0042\n// frob:todo T-0042 later\n// frob:ticket ~3TXB8SR\n// frob:ticket T-\n",
        );
        let hits = scan(&l.comments);
        assert_eq!(hits.len(), 4);
        assert!(hits[0].problem.is_none(), "{:?}", hits[0].problem);
        assert!(hits[1].problem.is_none(), "{:?}", hits[1].problem);
        assert_eq!(hits[2].problem.as_ref().map(|p| p.0), Some("DSL002"));
        assert!(hits[3].problem.is_some());
    }
}
