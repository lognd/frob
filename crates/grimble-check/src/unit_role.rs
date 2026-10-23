//! Unit roles declared in code: `grimble:core` and `grimble:shell` comments (cohesion.md 4).
//!
//! The scanner binds each directive to the symbol it sits on; this module maps that symbol to
//! the function unit of the folded term. A directive on anything but a function or method, or
//! one bound to the whole file, declares nothing. Both roles on one unit conflict and resolve
//! to the stricter `core` claim, so a conflict never excuses a decision with effects.

// frob:ticket 01M5HJ078MGFERVXX3DSJT111F

use std::collections::HashMap;
use std::sync::OnceLock;

use gob_directives::{Binding, DirectiveRecord, ScanConfig, Scanner};
use gob_ir::{NodeId, Operator, Universal};
use gob_languages::Language;
use gob_symbols::{Folded, SymbolKind};
use tracing::{debug, warn};

use crate::coh002::UnitRole;

/// The `grimble`-namespace scanner, built once.
fn scanner() -> &'static Scanner {
    static SCANNER: OnceLock<Scanner> = OnceLock::new();
    SCANNER.get_or_init(|| {
        Scanner::new(&ScanConfig {
            namespaces: vec!["grimble".to_owned()],
            product: "grimble".to_owned(),
        })
    })
}

/// The byte range of a node, if it has a span.
fn span_of(folded: &Folded, node: NodeId) -> Option<(u32, u32)> {
    folded
        .term
        .node(node)
        .location()
        .span()
        .map(|sp| (u32::from(sp.range.start()), u32::from(sp.range.end())))
}

/// The outermost function unit inside the byte range `(start, end)`, if any.
fn function_in(folded: &Folded, (start, end): (u32, u32)) -> Option<NodeId> {
    folded
        .term
        .ids()
        .filter(|&i| {
            matches!(folded.term.node(i).op(),
                Operator::Universal(Universal::Unit { kind, .. }) if kind == "function")
        })
        .filter_map(|i| span_of(folded, i).map(|r| (i, r)))
        .filter(|&(_, (s, e))| s >= start && e <= end)
        .min_by_key(|&(_, (s, e))| (s, std::cmp::Reverse(e)))
        .map(|(i, _)| i)
}

/// The function unit a role directive is declared on, or `None` when it is not on a function.
fn unit_of(folded: &Folded, record: &DirectiveRecord) -> Option<NodeId> {
    let Binding::Symbol(symref) = &record.bound else {
        debug!(verb = %record.verb, "role directive bound to the file declares no unit role");
        return None;
    };
    let symbol = folded.file.symbols.iter().find(|s| &s.symref == symref)?;
    if !matches!(symbol.kind, SymbolKind::Function | SymbolKind::Method) {
        debug!(%symref, kind = ?symbol.kind, "role directive on a non-function declares no unit role");
        return None;
    }
    function_in(
        folded,
        (u32::from(symbol.span.start()), u32::from(symbol.span.end())),
    )
}

/// The role each function unit declares through `grimble:core` / `grimble:shell` comments in
/// `text`; units without a directive are absent. The shell claim is unverified here
/// (`verified: false`) because the effects rules run elsewhere.
pub fn declared_roles(
    folded: &Folded,
    language: Language,
    text: &str,
) -> HashMap<NodeId, UnitRole> {
    let scan = scanner().scan(language, text, &folded.file);
    for finding in &scan.findings {
        debug!(message = %finding.message, "role directive scan finding");
    }
    let mut roles: HashMap<NodeId, UnitRole> = HashMap::new();
    for record in scan
        .directives
        .iter()
        .filter(|r| r.namespace == "grimble" && matches!(r.verb.as_str(), "core" | "shell"))
    {
        let Some(unit) = unit_of(folded, record) else {
            continue;
        };
        let claimed = if record.verb == "core" {
            UnitRole::Core
        } else {
            UnitRole::Shell { verified: false }
        };
        match roles.insert(unit, claimed) {
            Some(prev) if prev != claimed => {
                warn!(unit = ?unit, "grimble:core and grimble:shell on one unit conflict; core wins");
                roles.insert(unit, UnitRole::Core);
            }
            _ => debug!(unit = ?unit, role = ?claimed, "unit role read from directive"),
        }
    }
    roles
}

/// The role to judge a unit by: the directive's claim when present, else `supplied` unchanged.
pub fn resolve_role(declared: Option<UnitRole>, supplied: UnitRole) -> UnitRole {
    declared.unwrap_or(supplied)
}
