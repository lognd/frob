//! The generated languages page `docs/reference/languages.md`: every adapter extension with its
//! fidelity and capability-matrix cells (docs/design/shared/code-model.md section 3, docs/design/shared/code-model.md section 13.5).

// frob:ticket 01M47QKW1R6KY7K1H6N4M1BX5H

use std::fmt::Write as _;

use gob_caps::{Lang, gap_ticket};

use crate::registry::fidelity_report;

/// Renders the languages page body (no generated marker; `cargo dev gen languages` adds it): an extension table, then one capability table per adapter.
pub fn languages_page() -> String {
    let report = fidelity_report();
    let mut out = String::from(
        "# Languages\n\nCells: `Implemented` (with its precision), `NotApplicable` (the language has no such concept) or `Gap` (not provided yet; the answer is Unknown; `Gap (~ID)` names the ticket that fills it).\n",
    );
    out.push_str("\n## Extensions\n\n| Extension | Language | Fidelity |\n|---|---|---|\n");
    let mut by_ext: Vec<(&str, &str, String)> = report
        .iter()
        .flat_map(|r| {
            r.extensions
                .iter()
                .map(move |e| (*e, r.language, r.fidelity.to_string()))
        })
        .collect();
    by_ext.sort();
    for (ext, lang, fid) in &by_ext {
        writeln!(out, "| `.{ext}` | {lang} | {fid} |").ok();
    }
    for r in &report {
        write!(out, "\n## {}\n\nFidelity {}", r.language, r.fidelity).ok();
        if !r.extensions.is_empty() {
            let exts: Vec<String> = r.extensions.iter().map(|e| format!("`.{e}`")).collect();
            write!(out, "; extensions {}", exts.join(", ")).ok();
        }
        out.push_str(".\n\n| Capability | Cell | Precision |\n|---|---|---|\n");
        for (c, p) in &r.capabilities {
            let ticket = Lang::from_tag(r.language).and_then(|l| gap_ticket(l, *c));
            writeln!(
                out,
                "| {} | {} | {} |",
                c.name(),
                p.cell_with_ticket(ticket),
                p.label()
            )
            .ok();
        }
    }
    tracing::debug!(
        adapters = report.len(),
        extensions = by_ext.len(),
        "languages page rendered"
    );
    out
}
