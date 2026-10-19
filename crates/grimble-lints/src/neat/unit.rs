//! Units (Rust functions) and the `frob:` claims written above them.

// frob:ticket 01M3Z7151078ZAM6AM1GFWC6QP

use std::collections::BTreeSet;

use tree_sitter::Node;

use super::effects::{Atom, Ceiling};

/// A claim directive on a unit.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Claim {
    /// `frob:honest`, `frob:pure` or `frob:core`: no ambient effect.
    Honest(String),
    /// `frob:effects a b`: only these atoms.
    Atoms(BTreeSet<Atom>),
    /// `frob:shell`, `frob:trusted`: permitted to be dishonest.
    Exempt,
    /// `frob:dispatcher`: a dispatch site on purpose.
    Dispatcher,
}

/// One function and its claims.
#[derive(Debug, Clone)]
pub struct Unit<'t> {
    /// The `function_item` node.
    pub node: Node<'t>,
    /// The function name.
    pub name: String,
    /// The claims above it.
    pub claims: Vec<Claim>,
}

impl Unit<'_> {
    /// 1-based line of the unit.
    pub fn line(&self) -> usize {
        self.node.start_position().row + 1
    }

    /// The effect ceiling the claims declare, or `None` when there is none to check.
    pub fn ceiling(&self) -> Option<Ceiling> {
        if self.is_shell() {
            return None;
        }
        let mut found: Option<BTreeSet<Atom>> = None;
        for c in &self.claims {
            match c {
                Claim::Honest(_) => found = Some(BTreeSet::new()),
                Claim::Atoms(a) => found = Some(a.clone()),
                Claim::Exempt | Claim::Dispatcher => {}
            }
        }
        found
    }

    /// True when the unit may be dishonest and is exempt from the rules.
    pub fn is_shell(&self) -> bool {
        self.claims.contains(&Claim::Exempt)
    }

    /// True when the unit declares itself a dispatcher.
    pub fn is_marked_dispatcher(&self) -> bool {
        self.claims.contains(&Claim::Dispatcher)
    }

    /// The claim as written, for messages.
    pub fn claim_text(&self) -> String {
        self.claims
            .iter()
            .find_map(|c| match c {
                Claim::Honest(w) => Some(format!("`frob:{w}`")),
                Claim::Atoms(_) => Some("a `frob:effects` set".to_owned()),
                _ => None,
            })
            .unwrap_or_default()
    }

    /// The names of the unit's parameters.
    pub fn params(&self, src: &str) -> Vec<String> {
        let Some(list) = self.node.child_by_field_name("parameters") else {
            return Vec::new();
        };
        let mut cur = list.walk();
        list.children(&mut cur)
            .filter(|p| p.kind() == "parameter")
            .filter_map(|p| p.child_by_field_name("pattern"))
            .map(|p| src[p.byte_range()].trim_start_matches("mut ").to_owned())
            .collect()
    }
}

/// Every function of the file, with its claims.
pub fn units<'t>(root: Node<'t>, src: &str) -> Vec<Unit<'t>> {
    let mut out = Vec::new();
    let mut stack = vec![root];
    while let Some(n) = stack.pop() {
        if n.kind() == "function_item"
            && let Some(name) = n.child_by_field_name("name")
        {
            out.push(Unit {
                node: n,
                name: src[name.byte_range()].to_owned(),
                claims: claims_above(n, src),
            });
        }
        let mut cur = n.walk();
        stack.extend(n.children(&mut cur));
    }
    out.sort_by_key(|u| u.node.start_byte());
    out
}

fn claims_above(node: Node<'_>, src: &str) -> Vec<Claim> {
    let mut claims = Vec::new();
    let mut prev = node.prev_sibling();
    while let Some(p) = prev.filter(|p| {
        matches!(
            p.kind(),
            "attribute_item" | "line_comment" | "block_comment"
        )
    }) {
        if p.kind() != "attribute_item" {
            claims.extend(parse_claim(&src[p.byte_range()]));
        }
        prev = p.prev_sibling();
    }
    claims
}

/// The claim a comment spells, if it is a `frob:` claim directive.
fn parse_claim(comment: &str) -> Option<Claim> {
    let body = comment
        .trim_start_matches('/')
        .trim_start_matches('*')
        .trim_start_matches('!')
        .trim();
    let rest = body.strip_prefix("frob:")?;
    let mut words = rest.split_whitespace();
    let verb = words.next()?.trim_end_matches("*/");
    match verb {
        "honest" | "pure" | "core" => Some(Claim::Honest(verb.to_owned())),
        "shell" | "trusted" => Some(Claim::Exempt),
        "dispatcher" => Some(Claim::Dispatcher),
        "effects" => {
            let mut atoms = BTreeSet::new();
            for w in words {
                match w {
                    "none" | "honest" | "total" => {}
                    w => {
                        atoms.insert(Atom::from_word(w)?);
                    }
                }
            }
            Some(Claim::Atoms(atoms))
        }
        _ => None,
    }
}
