//! Turning findings into `gob-fix` fixes.

use gob_fix::{Applicability, Edit, Fix};
use gob_rules::{Finding, FixKind};
use gob_text::FileInterner;

/// Fixes ready to plan, plus how many were refused before planning.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Collected {
    /// Machine-applicable fixes on stylesheet sites.
    pub fixes: Vec<Fix>,
    /// Fixes refused because an edit lands outside a stylesheet (for example a JSX style prop).
    pub skipped_non_stylesheet: usize,
}

/// Whether `path` is a stylesheet; only stylesheet sites are ever auto-fixed.
#[must_use]
pub fn is_stylesheet(path: &str) -> bool {
    matches!(
        path.rsplit_once('.').map(|(_, ext)| ext),
        Some("css" | "scss" | "sass" | "less" | "pcss")
    )
}

/// Collect the Deterministic, machine-applicable fixes of `findings` as `gob-fix` fixes.
#[must_use]
pub fn collect(findings: &[Finding], files: &FileInterner) -> Collected {
    let mut out = Collected::default();
    for finding in findings {
        let Some(fix) = &finding.fix else { continue };
        if fix.kind != FixKind::Deterministic
            || fix.applicability != Applicability::Machine
            || fix.edits.is_empty()
        {
            continue;
        }
        let edits: Option<Vec<Edit>> = fix
            .edits
            .iter()
            .map(|e| {
                files.path(e.file).map(|path| Edit {
                    path: path.to_owned(),
                    start: u32::from(e.range.start()) as usize,
                    end: u32::from(e.range.end()) as usize,
                    replacement: e.replacement.clone(),
                })
            })
            .collect();
        let Some(edits) = edits else {
            tracing::warn!(rule = %finding.rule, "fix has an unresolvable file; skipped");
            continue;
        };
        if !edits.iter().all(|e| is_stylesheet(&e.path)) {
            tracing::info!(rule = %finding.rule, "fix on a non-stylesheet site; never auto-fixed");
            out.skipped_non_stylesheet += 1;
            continue;
        }
        out.fixes.push(Fix {
            rule: finding.rule.to_string(),
            title: fix.title.clone(),
            applicability: fix.applicability,
            edits,
        });
    }
    out
}
