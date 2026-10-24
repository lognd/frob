//! `GRL016`: a rule file in the repository whose embedded examples fail or which does not compile.
//!
//! Runs the same engine as `frob rule test` (`gob_plan::verbs::test::test_file`) over every
//! `.grl` file the walk found, so a repository pack's rules never rot (`grl-spec.md` section 9).

// frob:ticket 01M3ZX7H37B9GKN45MPD6ZNBTY

use gob_check::Snapshot;
use gob_plan::verbs::test::{FileTest, test_file};
use gob_rules::{Finding, Rule, RuleId, Severity};
use gob_text::{FileInterner, Span, TextRange, TextSize};

use crate::product::Frob;

/// A repository rule file whose example expectation does not match, or which fails to compile.
///
/// For each `.grl` file in the repository the rule runs every embedded example and fires once
/// per example that fails (the finding names the rule, the example and the expected-versus-actual
/// diff) or cannot run. A file that does not compile fires once per compile error, because none
/// of its examples can run. Passing examples are counted as the rule's subjects and produce
/// nothing. The std pack is checked with the same engine once its compiled-in bytes exist.
///
/// ## Remedy
///
/// Run `frob rule test PATH` for the full diff, then fix the rule or the example.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "GRL016",
    slug = "rule-example-mismatch",
    family = "GRL",
    severity = Error,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    version = 1
)]
pub struct Grl016;

fn rule_id() -> RuleId {
    Grl016
        .meta()
        .rule_id()
        .unwrap_or_else(|e| unreachable!("derive validates the id: {e}"))
}

/// The `.grl` paths the walk found, in path order.
fn grl_paths(snap: &Snapshot<Frob>) -> Vec<&str> {
    snap.core
        .entries
        .iter()
        .map(|e| e.path.as_str())
        .filter(|p| {
            std::path::Path::new(p)
                .extension()
                .is_some_and(|x| x == "grl")
        })
        .collect()
}

/// Every rule file's test result; an unreadable file is skipped with a warning.
fn results(snap: &Snapshot<Frob>) -> Vec<FileTest> {
    // Examples with a model body need the grimble reader; installing it is idempotent.
    gob_plan::examples::install_model_reader(grimble_check::example_model::read_example_model);
    grl_paths(snap)
        .into_iter()
        .filter_map(|p| match snap.core.text(p) {
            Ok(src) => Some(test_file(p, &src)),
            Err(e) => {
                tracing::warn!(path = p, error = %e, "GRL016: rule file unreadable; skipped");
                None
            }
        })
        .collect()
}

/// The byte range of the 1-based `line` of `src` (the whole file start when `line` is 0).
fn line_range(src: &str, line: u32) -> TextRange {
    let Some(n) = (line as usize).checked_sub(1) else {
        return TextRange::empty(TextSize::new(0));
    };
    let mut start = 0usize;
    for (i, l) in src.split_inclusive('\n').enumerate() {
        if i == n {
            let len = u32::try_from(l.trim_end().len()).unwrap_or(0);
            let s = u32::try_from(start).unwrap_or(0);
            return TextRange::at(TextSize::new(s), TextSize::new(len));
        }
        start += l.len();
    }
    TextRange::empty(TextSize::new(0))
}

/// The `GRL016` findings for every rule file in the snapshot.
pub(crate) fn findings(snap: &Snapshot<Frob>, files: &mut FileInterner) -> Vec<Finding> {
    let mut out = Vec::new();
    for ft in results(snap) {
        let src = snap.core.text(&ft.path).unwrap_or_default();
        let id = files.intern(&ft.path);
        for d in ft.diagnostics.iter().filter(|d| d.severity == "error") {
            let msg = format!(
                "{}:{}: rule file does not compile, so no example ran: {} {}",
                ft.path, d.line, d.code, d.message
            );
            let span = Span::new(id, line_range(&src, d.line));
            out.push(Finding::new(
                rule_id(),
                Severity::Error,
                Some(span),
                msg,
                &ft.path,
            ));
        }
        for e in ft.examples.iter().filter(|e| e.status != "ok") {
            let name = e
                .name
                .as_deref()
                .map_or_else(String::new, |n| format!(" \"{n}\""));
            let mut msg = format!(
                "{}: rule {} example{name} (expect {}) {}: {}",
                ft.path,
                e.rule,
                e.expect,
                if e.status == "fail" {
                    "does not match"
                } else {
                    "could not run"
                },
                e.detail
            );
            if !e.diff.is_empty() {
                msg.push('\n');
                msg.push_str(&e.diff);
            }
            let span = Span::new(id, TextRange::empty(TextSize::new(0)));
            let anchor = format!("{}:{}{name}", ft.path, e.rule);
            tracing::debug!(path = %ft.path, rule = %e.rule, "GRL016: example failed");
            out.push(Finding::new(
                rule_id(),
                Severity::Error,
                Some(span),
                msg,
                &anchor,
            ));
        }
    }
    out
}

/// The number of examples run across the repository's rule files (the rule's subjects).
pub(crate) fn example_count(snap: &Snapshot<Frob>) -> usize {
    let n: usize = results(snap).iter().map(|f| f.examples.len()).sum();
    tracing::debug!(examples = n, "GRL016: examples counted");
    n
}

#[cfg(test)]
#[allow(
    clippy::disallowed_methods,
    reason = "tests write fixtures with std::fs, not a walked snapshot"
)]
mod tests {
    use crate::{CheckOptions, run};

    const RULE: &str = r#"rule NOPE001 "danger-call" {
  lang rust
  severity warn
  find c: call where c.callee == "danger"
  report c "danger on line {c.line}"
  example fire rust """
    fn b() {
        danger(); //~ warn
    }
  """
  example clean rust """
    fn b() {
        safe();
    }
  """
  explain """
    Danger bites.

    ## Remedy
    Call something safe.
  """
}
"#;

    fn repo(rule: &str) -> tempfile::TempDir {
        let d = tempfile::tempdir().expect("tempdir");
        std::fs::create_dir_all(d.path().join("rules")).expect("mkdir");
        std::fs::write(d.path().join("rules/nope.grl"), rule).expect("write");
        d
    }

    fn report(root: &std::path::Path) -> gob_check::CheckReport {
        let opts = CheckOptions {
            skip_telemetry: true,
            skip_tools: true,
            ..CheckOptions::default()
        };
        run(root, &opts).expect("check runs")
    }

    fn grl(r: &gob_check::CheckReport) -> Vec<&gob_rules::Finding> {
        r.findings
            .iter()
            .filter(|f| f.rule.as_str() == "GRL016")
            .collect()
    }

    // frob:tests crates/frob-check/src/grl.rs::findings
    #[test]
    fn a_failing_example_is_a_grl016_finding_naming_the_rule_and_example() {
        let broken = RULE.replacen("danger(); //~ warn", "danger();", 1);
        let d = repo(&broken);
        let r = report(d.path());
        let found = grl(&r);
        assert_eq!(found.len(), 1, "{:?}", r.findings);
        assert!(found[0].message.contains("NOPE001"), "{}", found[0].message);
        assert!(found[0].message.contains("fire"), "{}", found[0].message);
    }

    // frob:tests crates/frob-check/src/grl.rs::example_count
    #[test]
    fn passing_examples_emit_nothing_and_are_counted() {
        let d = repo(RULE);
        let r = report(d.path());
        assert!(grl(&r).is_empty(), "{:?}", r.findings);
        assert_eq!(r.subjects_examined.get("GRL016"), Some(&2));
    }

    // frob:tests crates/frob-check/src/grl.rs::findings
    #[test]
    fn a_rule_file_that_does_not_compile_is_a_grl016_finding() {
        let d = repo("rule {");
        let r = report(d.path());
        let found = grl(&r);
        assert!(!found.is_empty());
        assert!(found[0].message.contains("does not compile"));
    }
}
