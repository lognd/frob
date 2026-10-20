//! Validation of plugin fixes against the primary span and the subject set (security.md 2.10).

// frob:ticket 01M3ZX7ZXZJ37A38BA4AVT0QRG

use std::collections::BTreeSet;

use gob_diagnostics::TextOrigin;
use gob_rules::{Fix, FixDrop, FixKind, PluginFix, TextEdit, cap_applicability};
use gob_text::{FileId, FileInterner, Span};
use gob_trust::effects::is_control_path;

/// What the host knows about one plugin call when it validates a fix.
pub struct FixContext<'a> {
    /// The finding's primary span.
    pub primary: Span,
    /// File handles the plugin was given in this call.
    pub subject_set: &'a BTreeSet<FileId>,
    /// Interned paths, to recognise the control plane.
    pub files: &'a FileInterner,
    /// The pack name, for the fix origin.
    pub pack: &'a str,
    /// Whether the pack holds the `fix.machine` effect.
    pub holds_fix_machine: bool,
}

/// A fix that passed validation, with the origin it carries.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidatedFix {
    /// The host fix, applicability already capped.
    pub fix: Fix,
    /// Who authored it (`pack:NAME`).
    pub origin: TextOrigin,
}

/// Validate `fix`: either every edit is allowed or the whole fix is dropped with the reasons.
///
/// # Errors
///
/// Every [`FixDrop`] reason found, when any edit is refused.
pub fn validate_plugin_fix(
    fix: &PluginFix,
    ctx: &FixContext<'_>,
) -> Result<ValidatedFix, Vec<FixDrop>> {
    let mut drops = Vec::new();
    if fix.edits.is_empty() {
        drops.push(FixDrop::NoEdits);
    }
    for e in &fix.edits {
        if let Some(path) = ctx.files.path(e.file).filter(|p| is_control_path(p)) {
            drops.push(FixDrop::ControlPlane(path.to_owned()));
        } else if !ctx.subject_set.contains(&e.file) {
            drops.push(FixDrop::NotInSubjectSet(e.file));
        } else if e.file != ctx.primary.file || !ctx.primary.range.contains_range(e.range) {
            drops.push(FixDrop::OutsidePrimarySpan(e.file));
        }
    }
    if !drops.is_empty() {
        for d in &drops {
            tracing::warn!(pack = ctx.pack, reason = %d, "plugin fix dropped");
        }
        return Err(drops);
    }
    let applicability = cap_applicability(fix.applicability, ctx.holds_fix_machine);
    if applicability != fix.applicability {
        tracing::info!(pack = ctx.pack, "plugin fix capped to maybe-incorrect");
    }
    Ok(ValidatedFix {
        fix: Fix {
            kind: FixKind::Deterministic,
            applicability,
            title: fix.title.clone(),
            edits: fix
                .edits
                .iter()
                .map(|e| TextEdit {
                    file: e.file,
                    range: e.range,
                    replacement: e.replacement.clone(),
                })
                .collect(),
        },
        origin: TextOrigin::Pack(ctx.pack.to_owned()),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::{Applicability, PluginEdit};
    use gob_text::{TextRange, TextSize};

    fn range(a: u32, b: u32) -> TextRange {
        TextRange::new(TextSize::from(a), TextSize::from(b))
    }

    struct Fixture {
        files: FileInterner,
        src: FileId,
        toml: FileId,
        subject: BTreeSet<FileId>,
    }

    fn fixture() -> Fixture {
        let mut files = FileInterner::default();
        let src = files.intern("src/a.py");
        let toml = files.intern("frob.toml");
        Fixture {
            files,
            src,
            toml,
            subject: BTreeSet::from([src, toml]),
        }
    }

    fn fix_of(file: FileId, r: TextRange, app: Applicability) -> PluginFix {
        PluginFix {
            applicability: app,
            title: "t".into(),
            edits: vec![PluginEdit {
                file,
                range: r,
                replacement: "x".into(),
            }],
        }
    }

    fn ctx(f: &Fixture, machine: bool) -> FixContext<'_> {
        FixContext {
            primary: Span::new(f.src, range(10, 20)),
            subject_set: &f.subject,
            files: &f.files,
            pack: "py-safety",
            holds_fix_machine: machine,
        }
    }

    #[test]
    // frob:tests validate_plugin_fix
    fn edit_outside_primary_span_is_dropped_and_reported() {
        let f = fixture();
        let bad = fix_of(f.src, range(5, 12), Applicability::MaybeIncorrect);
        let err = validate_plugin_fix(&bad, &ctx(&f, false)).unwrap_err();
        assert_eq!(err, vec![FixDrop::OutsidePrimarySpan(f.src)]);
        let ok = fix_of(f.src, range(12, 18), Applicability::MaybeIncorrect);
        assert!(validate_plugin_fix(&ok, &ctx(&f, false)).is_ok());
    }

    #[test]
    // frob:tests validate_plugin_fix
    fn control_plane_fix_is_refused_even_with_fix_machine() {
        let f = fixture();
        let bad = fix_of(f.toml, range(0, 1), Applicability::Machine);
        let err = validate_plugin_fix(&bad, &ctx(&f, true)).unwrap_err();
        assert_eq!(err, vec![FixDrop::ControlPlane("frob.toml".into())]);
    }

    #[test]
    // frob:tests validate_plugin_fix
    fn machine_is_capped_without_fix_machine_and_origin_is_the_pack() {
        let f = fixture();
        let fix = fix_of(f.src, range(12, 18), Applicability::Machine);
        let v = validate_plugin_fix(&fix, &ctx(&f, false)).unwrap();
        assert_eq!(v.fix.applicability, Applicability::MaybeIncorrect);
        assert_eq!(v.origin, TextOrigin::Pack("py-safety".into()));
        let v = validate_plugin_fix(&fix, &ctx(&f, true)).unwrap();
        assert_eq!(v.fix.applicability, Applicability::Machine);
    }

    #[test]
    // frob:tests validate_plugin_fix
    fn file_outside_subject_set_is_dropped() {
        let mut f = fixture();
        let other = f.files.intern("src/b.py");
        let bad = fix_of(other, range(12, 18), Applicability::MaybeIncorrect);
        let err = validate_plugin_fix(&bad, &ctx(&f, false)).unwrap_err();
        assert_eq!(err, vec![FixDrop::NotInSubjectSet(other)]);
    }
}
