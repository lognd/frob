//! TYPE002: a `font-family` stack that is not a prefix of any declared stack (port of
//! `crunk/rules/_typography.py` `type002`).
//!
//! The stack is compared case-insensitively and quote-stripped with every declared
//! `[typography.stacks]` entry (the single implicit stack of `families` when none is declared). A
//! declaration whose value holds a `var()` is conformant by construction, as in Python, even
//! when literals follow it. Not fixable: choosing a replacement stack is a design decision.

// frob:ticket 01M43ATBDWVSJBXP7TEQ6DBW3W

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};
use crate::typography::{effective_stacks, split_family_stack};

/// A `font-family` stack that is not a prefix of any declared stack.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "TYPE002",
    slug = "font-family-off-stack",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Type002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Type002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let stacks = effective_stacks(spec);
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            let families = sheet
                .declarations
                .iter()
                .filter(|d| d.prop == "font-family");
            for decl in families.filter(|d| d.var_refs.is_empty()) {
                let stack = split_family_stack(&decl.value);
                if stacks.values().any(|declared| declared.starts_with(&stack)) {
                    continue;
                }
                let names: Vec<&String> = stacks.keys().collect();
                tracing::debug!(%path, prop = %decl.prop, "TYPE002: undeclared font stack");
                out.fire_in(
                    &path,
                    decl.span.0,
                    format!("font-family stack {stack:?} is not a prefix of any declared stack {names:?}"),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Type002 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
