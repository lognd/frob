//! The tier A fix of `FMT001`: run a formatter stage's unattended fix command over the files it flagged, inside the run's scope.

use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

use gob_rules::Finding;
use gob_text::FileInterner;

use crate::config::ToolStage;
use crate::error::CheckError;
use crate::report::{AppliedFix, SkippedFix};
use crate::tools::{ToolTrust, run_fix};

/// The rule id the formatter parser reports unformatted files under.
const FMT_RULE: &str = "FMT001";

/// What the formatter fixes did.
#[derive(Debug, Default)]
pub(crate) struct FmtFixRun {
    /// Files a formatter rewrote.
    pub applied: Vec<AppliedFix>,
    /// Flagged files left alone because the scope forbids editing them.
    pub skipped_scope: Vec<SkippedFix>,
}

#[allow(
    clippy::disallowed_methods,
    reason = "restoring an out-of-scope file compares and rewrites its exact on-disk bytes"
)]
// frob:ticket 01M4D94J5J2TZEXTB8GH36992B
/// Run each formatter stage's unattended fix over its in-scope `FMT001` files.
///
/// `blocked` maps the paths the scope forbids to their widen hint; those files are never passed to a
/// formatter, and any that a formatter touched anyway (a rustfmt child module) are restored byte for byte.
///
/// # Errors
///
/// [`CheckError::FixIo`] when a formatter is missing, untrusted, times out or exits non-zero; the
/// out-of-scope files are restored before the error is returned.
pub(crate) fn run_formatters(
    root: &Path,
    stages: &[ToolStage],
    findings: &[Finding],
    files: &FileInterner,
    blocked: &BTreeMap<String, String>,
    trust: Option<&dyn ToolTrust>,
) -> Result<FmtFixRun, CheckError> {
    let mut allowed: BTreeMap<&str, BTreeSet<String>> = BTreeMap::new();
    let mut held: BTreeSet<String> = BTreeSet::new();
    for finding in findings.iter().filter(|f| f.rule.as_str() == FMT_RULE) {
        let Some(path) = finding.span.and_then(|s| files.path(s.file)) else {
            continue;
        };
        if blocked.contains_key(path) {
            held.insert(path.to_owned());
            continue;
        }
        let Some(stage) = stages
            .iter()
            .find(|s| finding.message.starts_with(&format!("{}/", s.name)))
        else {
            tracing::warn!(
                path,
                "FMT001 fix skipped: no formatter stage owns the finding"
            );
            continue;
        };
        allowed
            .entry(stage.name.as_str())
            .or_default()
            .insert(path.to_owned());
    }
    let mut run = FmtFixRun::default();
    for path in &held {
        let widen = blocked.get(path).cloned().unwrap_or_default();
        tracing::info!(path, "FMT001 fix skipped: outside the run's scope");
        run.skipped_scope.push(SkippedFix {
            rule: FMT_RULE.to_owned(),
            file: path.clone(),
            widen,
        });
    }
    let snapshot: Vec<(&String, Vec<u8>)> = held
        .iter()
        .filter_map(|p| std::fs::read(root.join(p)).ok().map(|bytes| (p, bytes)))
        .collect();
    let mut failure = None;
    for stage in stages {
        let Some(paths) = allowed.get(stage.name.as_str()) else {
            continue;
        };
        let Some(mut args) = stage
            .def
            .as_deref()
            .and_then(crate::tool_def::lookup)
            .and_then(crate::tool_def::ToolDef::fix_args)
        else {
            tracing::warn!(stage = %stage.name, "FMT001 fix skipped: the stage has no unattended fix");
            continue;
        };
        args.extend(paths.iter().map(|p| format!("./{p}")));
        tracing::info!(stage = %stage.name, files = paths.len(), "running formatter fix");
        if let Err(why) = run_fix(root, stage, trust, &args) {
            failure = Some(format!("E-CHECK-FIX-IO: {why}"));
            break;
        }
        run.applied.extend(paths.iter().map(|p| AppliedFix {
            rule: FMT_RULE.to_owned(),
            file: p.clone(),
            title: format!("format with {}", stage.name),
        }));
    }
    for (path, original) in snapshot {
        if std::fs::read(root.join(path)).ok().as_deref() != Some(original.as_slice()) {
            tracing::warn!(path, "formatter touched an out-of-scope file; restoring it");
            if let Err(e) = std::fs::write(root.join(path), &original) {
                failure.get_or_insert(format!("E-CHECK-FIX-IO: restore {path}: {e}"));
            }
        }
    }
    match failure {
        Some(message) => Err(CheckError::FixIo(message)),
        None => Ok(run),
    }
}

#[cfg(test)]
#[allow(
    clippy::disallowed_methods,
    reason = "the tests assert the exact on-disk bytes a formatter left behind"
)]
mod tests {
    use super::*;
    use crate::config::ToolParser;
    use gob_rules::{RuleId, Severity};
    use gob_text::{Span, TextRange, TextSize};

    /// A stage on the `ruff-format` def whose program is `sh`, so the def's `ruff@<version>` first
    /// argument names the fake formatter script in the work tree.
    fn stage() -> ToolStage {
        ToolStage {
            name: "ruff-format".to_owned(),
            def: Some("ruff-format".to_owned()),
            command: "sh".to_owned(),
            args: Vec::new(),
            timeout_secs: 30,
            fail_on_nonzero: true,
            parser: ToolParser::FormatterList,
            labels: Vec::new(),
            id_map: BTreeMap::new(),
            min_version: None,
            max_version: None,
            version_args: None,
            optional: false,
            inputs: Vec::new(),
            tier: crate::ToolTier::Ticket,
            unscoped_packages: Vec::new(),
            requires: Vec::new(),
        }
    }

    /// An `FMT001` finding for `path`, owned by the `ruff-format` stage.
    fn finding(files: &mut FileInterner, path: &str) -> Finding {
        let at = Span::new(
            files.intern(path),
            TextRange::new(TextSize::from(0), TextSize::from(0)),
        );
        Finding::new(
            FMT_RULE.parse::<RuleId>().expect("rule id"),
            Severity::Warn,
            Some(at),
            "ruff-format/FMT001: file is not formatted",
            path,
        )
    }

    /// A fake formatter run as `sh ruff@0.14.1 ...` from the work tree: it appends a marker to every
    /// `./path` argument and to `b.py` regardless, then exits `exit`.
    fn fake(dir: &Path, exit: i32) {
        std::fs::write(
            dir.join("ruff@0.14.1"),
            format!(
                "for a in \"$@\"; do case \"$a\" in ./*) echo formatted >> \"$a\";; esac; done\necho formatted >> b.py\nexit {exit}\n"
            ),
        )
        .expect("write");
    }

    // frob:ticket 01M4D94J5J2TZEXTB8GH36992B
    // frob:tests crates/gob-check/src/fmt_fix.rs::run_formatters
    #[test]
    fn formatter_fix_rewrites_only_in_scope_files() {
        if !gob_exec::require_sh("formatter_fix_rewrites_only_in_scope_files") {
            return;
        }
        let dir = tempfile::tempdir().expect("tmp");
        std::fs::write(dir.path().join("a.py"), "a\n").expect("a");
        std::fs::write(dir.path().join("b.py"), "b\n").expect("b");
        fake(dir.path(), 0);
        let mut files = FileInterner::default();
        let findings = vec![finding(&mut files, "a.py"), finding(&mut files, "b.py")];
        let blocked = BTreeMap::from([("b.py".to_owned(), "frob lease widen b.py".to_owned())]);
        let run =
            run_formatters(dir.path(), &[stage()], &findings, &files, &blocked, None).expect("fix");
        assert_eq!(
            std::fs::read_to_string(dir.path().join("a.py")).expect("a"),
            "a\nformatted\n"
        );
        assert_eq!(
            std::fs::read_to_string(dir.path().join("b.py")).expect("b"),
            "b\n",
            "the out-of-scope file is restored"
        );
        assert_eq!(run.applied.len(), 1);
        assert_eq!(run.applied[0].file, "a.py");
        assert_eq!(run.skipped_scope.len(), 1);
        assert_eq!(run.skipped_scope[0].file, "b.py");
        assert!(run.skipped_scope[0].widen.contains("widen"));
    }

    // frob:ticket 01M4D94J5J2TZEXTB8GH36992B
    // frob:tests crates/gob-check/src/fmt_fix.rs::run_formatters
    #[test]
    fn a_failing_formatter_is_a_fix_io_error_and_still_restores_scope() {
        if !gob_exec::require_sh("a_failing_formatter_is_a_fix_io_error_and_still_restores_scope") {
            return;
        }
        let dir = tempfile::tempdir().expect("tmp");
        std::fs::write(dir.path().join("a.py"), "a\n").expect("a");
        std::fs::write(dir.path().join("b.py"), "b\n").expect("b");
        fake(dir.path(), 3);
        let mut files = FileInterner::default();
        let findings = vec![finding(&mut files, "a.py"), finding(&mut files, "b.py")];
        let blocked = BTreeMap::from([("b.py".to_owned(), String::new())]);
        let err = run_formatters(dir.path(), &[stage()], &findings, &files, &blocked, None)
            .expect_err("fix failed");
        assert!(matches!(err, CheckError::FixIo(_)), "{err:?}");
        assert_eq!(
            std::fs::read_to_string(dir.path().join("b.py")).expect("b"),
            "b\n"
        );
    }
}
