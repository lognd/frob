//! COLOR002: a `var(--x)` reference shaped like a token name that nothing defines (port of
//! `crunk/rules/_color.py` `color002`).
//!
//! A reference is defined by the spec's token export or by a custom property of any ingested
//! sheet (Python knew only the export). The definition set is only complete when every source was
//! indexed ([`crate::color::defs::unindexed_sources`]); a reference nothing defines is then a
//! finding, and otherwise the rule is Unresolved, never clean (polarity P-: absence is only
//! certified when the whole space was searched). Names, not colour values, are judged, so the mode
//! loop of the colour rules does not apply here until tokens differ per mode.

// frob:ticket 01M43ATB4X0B56W8T0G8MQFYVM

use crunk_spec::naming::token_namespaces;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::color::defs::{defined_names, unindexed_sources};
use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};

/// A token-shaped `var()` reference to a custom property nothing defines.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "COLOR002",
    slug = "undefined-token-reference",
    severity = Error,
    polarity = Pminus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Color002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Color002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        let defined = match defined_names(spec, styles) {
            Ok(defined) => defined,
            Err(err) => {
                tracing::warn!(%err, "COLOR002: the token export set cannot be built");
                out.unresolved(format!("the token export set cannot be built: {err}"));
                return;
            }
        };
        let unindexed = unindexed_sources(spec, styles);
        let namespaces = token_namespaces(&spec.tokens);
        let mut undecided: Vec<String> = Vec::new();
        for sheet in &styles.sheets {
            let path = site_path(spec, &sheet.path);
            let refs = sheet.declarations.iter().flat_map(|d| &d.var_refs);
            for var in refs {
                if !namespaces
                    .iter()
                    .any(|ns| var.name.starts_with(ns.as_str()))
                    || defined.contains(&var.name)
                {
                    continue;
                }
                if unindexed.is_empty() {
                    tracing::debug!(%path, name = %var.name, "COLOR002: undefined reference");
                    out.fire_in(
                        &path,
                        var.span.0,
                        format!("var({}) references an undefined token", var.name),
                    );
                } else {
                    undecided.push(format!("var({}) in {path}", var.name));
                }
            }
        }
        if !undecided.is_empty() {
            tracing::info!(
                count = undecided.len(),
                "COLOR002: references cannot be decided"
            );
            out.unresolved(format!(
                "{} token reference(s) match no known definition but the definition set is incomplete ({}); first: {}",
                undecided.len(),
                unindexed.join("; "),
                undecided[0],
            ));
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Color002 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
