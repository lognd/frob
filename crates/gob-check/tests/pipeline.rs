//! The pipeline driven by a product that is not frob: proof that the extraction is neutral.

use std::path::Path;
use std::sync::Arc;

use gob_check::{
    CheckCtx, CheckError, CollectCx, Collected, FileCheck, Product, RepoGroup, RunOptions,
    ScopeView, SharedCtx, Snapshot, run,
};
use gob_diagnostics::ExitCode;
use gob_rules::{
    ExceptionCtx, Finding, RequiredReason, Resolved, Rule, RuleMeta, Severity, apply_exceptions,
};
use gob_text::{FileId, FileInterner, Span, TextRange, TextSize};

/// A line says BAD.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TOY001",
    slug = "toy-bad",
    family = "TOY",
    product = "toy",
    severity = Warn,
    tier = Universal,
    scope = File,
    fix = Manual,
    polarity = Pplus,
    version = 1
)]
struct Toy001;

/// A repo-wide measurement that must see subjects.
#[derive(Debug, Clone, Copy, Default, Rule)]
#[rule(
    id = "TOY002",
    slug = "toy-measured",
    family = "TOY",
    product = "toy",
    severity = Warn,
    tier = Universal,
    scope = Repo,
    fix = Manual,
    polarity = Pminus,
    must_measure = true,
    version = 1
)]
struct Toy002;

/// Reports every `*.txt` file that contains BAD.
struct BadCheck;

impl FileCheck<Toy> for BadCheck {
    fn rules(&self) -> Vec<&'static RuleMeta> {
        vec![Toy001.meta()]
    }

    fn applies(&self, _ctx: &SharedCtx<'_, Toy>, path: &str) -> bool {
        Path::new(path).extension().is_some_and(|e| e == "txt")
    }

    fn check(
        &self,
        _ctx: &CheckCtx<'_, Toy>,
        file: FileId,
        path: &str,
        text: &str,
    ) -> Vec<Finding> {
        let Some(at) = text.find("BAD") else {
            return Vec::new();
        };
        let start = TextSize::new(u32::try_from(at).expect("small"));
        let span = Span::new(file, TextRange::at(start, TextSize::new(3)));
        vec![Finding::new(
            Toy001.meta().rule_id().expect("valid"),
            Severity::Warn,
            Some(span),
            "says BAD",
            path,
        )]
    }
}

/// A product with no inputs; `subjects` is what its repo group claims to have examined.
struct Toy {
    subjects: usize,
    applicable: bool,
}

/// A fixed scope over `a.txt`.
struct ToyScope(std::collections::BTreeSet<String>);

impl ScopeView for ToyScope {
    fn label(&self) -> &'static str {
        "toy-scope"
    }

    fn files(&self) -> &std::collections::BTreeSet<String> {
        &self.0
    }
}

impl Product for Toy {
    type Shared = ();
    type Inputs = ();
    type Scope = ToyScope;

    fn resolve_scope(
        &self,
        _snap: &Snapshot<Self>,
        _table: &gob_check::CheckTable,
        _reference: &str,
    ) -> Result<ToyScope, CheckError> {
        Ok(ToyScope(["a.txt".to_owned()].into()))
    }

    fn name(&self) -> &'static str {
        "toy"
    }

    fn collect(&self, _cx: &mut CollectCx<'_>) -> Result<Collected<Self>, CheckError> {
        Ok(Collected {
            shared: (),
            inputs: (),
            findings: Vec::new(),
        })
    }

    fn file_checks(&self) -> Vec<Arc<dyn FileCheck<Self>>> {
        vec![Arc::new(BadCheck)]
    }

    fn repo_groups(&self) -> Vec<RepoGroup<Self>> {
        let n = self.subjects;
        vec![
            RepoGroup::new("repo:toy", vec![Toy002.meta()], |_: &Snapshot<Self>, _| {
                Vec::new()
            })
            .counting(move |_| vec![("TOY002", n)])
            .full_only(),
        ]
    }

    fn repo_digest(&self, _snap: &Snapshot<Self>) -> Vec<u8> {
        Vec::new()
    }

    fn resolve_exceptions(
        &self,
        _snap: &Snapshot<Self>,
        files: &FileInterner,
        raw: Vec<Finding>,
    ) -> Resolved {
        apply_exceptions(raw, &[], &ExceptionCtx { files })
    }

    fn applicable(&self, _snap: &Snapshot<Self>, _meta: &RuleMeta) -> bool {
        self.applicable
    }
}

fn tree() -> tempfile::TempDir {
    let dir = tempfile::tempdir().expect("tempdir");
    std::fs::write(dir.path().join("a.txt"), "fine\nBAD here\n").expect("write");
    std::fs::write(dir.path().join("b.txt"), "fine\n").expect("write");
    std::fs::write(dir.path().join("c.md"), "not a txt file\n").expect("write");
    dir
}

fn quiet() -> RunOptions {
    RunOptions {
        skip_telemetry: true,
        skip_tools: true,
        ..RunOptions::default()
    }
}

// frob:tests crates/gob-check/src/pipeline.rs::run
#[test]
fn a_foreign_product_gets_findings_caches_and_subject_counts() {
    let dir = tree();
    let toy = Toy {
        subjects: 4,
        applicable: true,
    };
    let first = run(&toy, dir.path(), &quiet()).expect("first run");
    let rules: Vec<String> = first.findings.iter().map(|f| f.rule.to_string()).collect();
    assert_eq!(rules, ["TOY001"]);
    assert_eq!(
        first.subjects_examined.get("TOY001"),
        Some(&2),
        "two txt files examined"
    );
    assert_eq!(first.subjects_examined.get("TOY002"), Some(&4));
    assert!(first.stats.file_misses > 0);
    assert!(
        dir.path().join(".toy").is_dir(),
        "state lives under the product's own directory"
    );

    let second = run(&toy, dir.path(), &quiet()).expect("second run");
    assert_eq!(second.stats.file_misses, 0, "served from the cache");
    assert_eq!(second.findings, first.findings);
    assert_eq!(
        second.subjects_examined, first.subjects_examined,
        "counts survive cache hits"
    );
}

// frob:tests crates/gob-check/src/required.rs::zero_subjects
#[test]
fn a_must_measure_rule_with_zero_subjects_is_a_required_unresolved() {
    let dir = tree();
    let toy = Toy {
        subjects: 0,
        applicable: true,
    };
    let report = run(&toy, dir.path(), &quiet()).expect("run");
    let zero: Vec<&Finding> = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved)
        .collect();
    assert_eq!(zero.len(), 1);
    assert_eq!(zero[0].rule.as_str(), "TOY002");
    assert_eq!(
        zero[0].required,
        Some(RequiredReason::ZeroSubjects {
            rule: "TOY002".into()
        })
    );
    assert_eq!(report.required_unresolved(), 1);
    assert_eq!(
        report.exit_code(),
        ExitCode::Negative,
        "the gate fails on silence"
    );
}

#[test]
fn zero_subjects_pass_when_the_rule_is_not_applicable_or_was_filtered_out() {
    let dir = tree();
    let na = Toy {
        subjects: 0,
        applicable: false,
    };
    let report = run(&na, dir.path(), &quiet()).expect("run");
    assert!(
        report
            .findings
            .iter()
            .all(|f| f.severity != Severity::Unresolved),
        "not applicable means no finding"
    );
    let applicable = Toy {
        subjects: 0,
        applicable: true,
    };
    let only = RunOptions {
        only: vec!["TOY001".to_owned()],
        ..quiet()
    };
    let report = run(&applicable, dir.path(), &only).expect("run");
    assert!(
        report
            .findings
            .iter()
            .all(|f| f.severity != Severity::Unresolved),
        "a rule `--only` dropped is not measured"
    );
}

#[test]
fn only_accepts_this_products_rules_and_rejects_the_others() {
    let dir = tree();
    let toy = Toy {
        subjects: 1,
        applicable: true,
    };
    let ok = RunOptions {
        only: vec!["toy".to_owned()],
        ..quiet()
    };
    assert!(run(&toy, dir.path(), &ok).is_ok(), "family TOY is known");
    let foreign = RunOptions {
        only: vec!["TOOL001".to_owned()],
        ..quiet()
    };
    assert!(
        matches!(
            run(&toy, dir.path(), &foreign),
            Err(CheckError::UnknownFamily(_))
        ),
        "TOOL001 belongs to frob's namespace, not toy's"
    );
}

// frob:tests crates/gob-check/src/repo.rs::run_repo_rules
#[test]
fn a_scoped_run_skips_full_only_groups_with_a_reason_and_a_full_run_keeps_them() {
    let dir = tree();
    let toy = Toy {
        subjects: 4,
        applicable: true,
    };
    let scoped = RunOptions {
        scope: Some("anything".to_owned()),
        ..quiet()
    };
    let report = run(&toy, dir.path(), &scoped).expect("scoped run");
    assert_eq!(
        report.subjects_examined.get("TOY002"),
        None,
        "group skipped"
    );
    assert_eq!(
        report
            .fidelity
            .inapplicable
            .get("TOY002")
            .map(String::as_str),
        Some("repo-wide, runs in full check")
    );
    let full = run(&toy, dir.path(), &quiet()).expect("full run");
    assert_eq!(full.subjects_examined.get("TOY002"), Some(&4));
    assert!(full.fidelity.inapplicable.is_empty());
}
