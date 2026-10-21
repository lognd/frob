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
    malformed: Vec<(String, String)>,
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

    fn malformed_projects(&self, _shared: &()) -> Vec<gob_symbols::MalformedProject> {
        self.malformed
            .iter()
            .map(|(path, reason)| gob_symbols::MalformedProject {
                path: path.clone(),
                reason: reason.clone(),
            })
            .collect()
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
        malformed: Vec::new(),
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
        !dir.path().join(".toy").exists(),
        "the cache is per-user, so no state directory lands in the worktree"
    );
    let shared = gob_cache::shared_dir(dir.path(), ".toy").expect("per-user cache dir");
    assert!(shared.is_dir(), "state lives in the shared cache directory");

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
        malformed: Vec::new(),
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
        malformed: Vec::new(),
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
        malformed: Vec::new(),
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
        malformed: Vec::new(),
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
        malformed: Vec::new(),
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

// frob:ticket 01M5C2Q5V7NRJTW8Y3DX625YAT
// frob:tests crates/gob-check/src/trust_from.rs::findings
#[test]
fn trust_from_reports_a_pack_absent_from_the_lock_at_the_ref_as_untrusted_in_change() {
    let dir = tree();
    let repo = gob_git::Repo::init(dir.path()).expect("init");
    let path = gob_git::RelPath::new("toy.packs.lock").expect("path");
    let commit = gob_git::CommitOptions {
        cas_retries: 5,
        author: Some(("Test".into(), "test@example.com".into())),
    };
    let lock = "lock_version = 1\ndigest_scheme = 1\n";
    repo.commit_paths(
        "refs/heads/main",
        &[(path, Some(lock.as_bytes().to_vec()))],
        "base",
        &commit,
    )
    .expect("commit");
    let spec = |required| gob_check::TrustFromSpec {
        base_ref: "refs/heads/main".to_owned(),
        lock_path: "toy.packs.lock".to_owned(),
        packs: vec![gob_check::trust_from::LivePack {
            name: "newpack".to_owned(),
            tree: "blake3:abc".to_owned(),
            required,
        }],
    };
    let toy = Toy {
        subjects: 1,
        applicable: true,
        malformed: Vec::new(),
    };
    let opts = RunOptions {
        trust_from: Some(spec(true)),
        ..quiet()
    };
    let report = run(&toy, dir.path(), &opts).expect("run");
    let hit: Vec<_> = report
        .findings
        .iter()
        .filter(|f| f.severity == Severity::Unresolved)
        .filter_map(|f| f.required.as_ref().map(ToString::to_string))
        .collect();
    assert_eq!(hit, ["untrusted-in-change: newpack"]);
    let none = RunOptions {
        trust_from: None,
        ..opts
    };
    let clean = run(&toy, dir.path(), &none).expect("run");
    assert!(clean.findings.iter().all(|f| f.required.is_none()));
}

// frob:tests crates/gob-check/src/pipeline.rs::run
#[test]
fn malformed_projects_are_required_unresolved_read001_naming_each_file() {
    let dir = tree();
    let toy = Toy {
        subjects: 1,
        applicable: true,
        malformed: vec![
            ("src/B/B.csproj".to_owned(), "unclosed element".to_owned()),
            ("App.sln".to_owned(), "bad header".to_owned()),
            ("App.sln".to_owned(), "duplicate".to_owned()),
        ],
    };
    let report = run(&toy, dir.path(), &quiet()).expect("run");
    let read: Vec<&Finding> = report
        .findings
        .iter()
        .filter(|f| f.rule.to_string() == "READ001")
        .collect();
    assert_eq!(read.len(), 2, "one per file, duplicates folded: {read:?}");
    assert!(read[0].message.contains("App.sln") && read[0].message.contains("bad header"));
    assert!(read[1].message.contains("B.csproj") && read[1].message.contains("unclosed element"));
    assert!(read.iter().all(|f| f.severity == Severity::Unresolved));
    assert!(
        read.iter().all(|f| f.required.is_some()),
        "required Unresolved"
    );
    assert_eq!(
        report.fidelity.languages["project"]
            .unresolved
            .get("READ001"),
        Some(&2)
    );
}
