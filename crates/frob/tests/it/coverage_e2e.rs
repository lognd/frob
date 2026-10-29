//! Coverage across Rust, Python, JavaScript and C#: each language's report is read, merged, and held to its COV004 threshold.
// frob:ticket 01M5XD3T77PEHA0QDBXC7TFFN3

use std::fmt::Write as _;
use std::path::{Path, PathBuf};
use std::process::Output;
use std::sync::Arc;

use frob_evidence::Workspace;
use frob_evidence::coverage::csharp::CsharpCoverage;
use frob_evidence::coverage::js::VitestCoverage;
use frob_evidence::coverage::lcov::Lcov;
use frob_evidence::coverage::python::PythonCoverage;
use frob_evidence::coverage::rust::RustCoverage;
use frob_evidence::coverage::{
    CoveragePlan, CoverageProvider, PROVIDERS, language_report, merge_reports,
};
use gob_exec::Program;
use serde_json::Value;

use crate::common;

/// One lcov record: `lines` of which the first `hit` are executed.
fn record(sf: &str, lines: u32, hit: u32) -> String {
    let mut out = format!("TN:\nSF:{sf}\n");
    for n in 1..=lines {
        let _ = writeln!(out, "DA:{n},{}", u32::from(n <= hit));
    }
    let _ = write!(out, "LF:{lines}\nLH:{hit}\nend_of_record\n");
    out
}

/// A fixture repository with one tested file per language and a frob workspace over it.
struct Fixture {
    _tmp: tempfile::TempDir,
    root: PathBuf,
    ws: Workspace,
}

fn write(root: &Path, rel: &str, body: &str) {
    let path = root.join(rel);
    std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
    std::fs::write(path, body).expect("write");
}

impl Fixture {
    /// Rust (root crate), Python (`py/`), JavaScript (`js/`) and C# (`cs/`) sources and tests.
    fn new() -> Self {
        let tmp = tempfile::tempdir().expect("tempdir");
        let root = tmp.path().join("repo");
        std::fs::create_dir_all(&root).expect("mkdir");
        gob_git::Repo::init(&root).expect("git init");
        write(
            &root,
            "Cargo.toml",
            "[package]\nname = \"tiny\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(
            &root,
            "src/lib.rs",
            "pub fn f() {}\n#[cfg(test)]\nmod t {\n    #[test]\n    fn ok() {}\n}\n",
        );
        write(&root, "py/pkg/a.py", "def f():\n    return 1\n");
        write(
            &root,
            "py/tests/test_a.py",
            "def test_f():\n    assert True\n",
        );
        write(
            &root,
            "package.json",
            "{\"devDependencies\": {\"vitest\": \"1.0.0\"}}\n",
        );
        write(&root, "js/src/a.ts", "export const a = 1;\n");
        write(
            &root,
            "js/src/a.test.ts",
            "import { test } from 'vitest';\ntest('a', () => {});\n",
        );
        write(
            &root,
            "cs/Calc.csproj",
            "<Project><ItemGroup><PackageReference Include=\"coverlet.collector\" /></ItemGroup></Project>\n",
        );
        write(&root, "cs/Calc.cs", "class Calc { }\n");
        write(
            &root,
            "cs/CalcTests.cs",
            "using Xunit;\nclass CalcTests { [Fact] public void A() { } }\n",
        );
        let ws = Workspace::open(&root, Arc::new(gob_time::SystemClock)).expect("workspace");
        Self {
            _tmp: tmp,
            root,
            ws,
        }
    }

    /// Feed `raw` through `provider`'s own reader and the shared normaliser into `.frob/coverage/<lang>.info`.
    fn ingest(&self, provider: &dyn CoverageProvider, raw_name: &str, raw: &str) {
        tracing::info!(
            language = provider.language(),
            "ingesting seeded coverage report"
        );
        let report = self
            .root
            .join(".frob/raw")
            .join(provider.language())
            .join(raw_name);
        write(
            &self.root,
            &format!(".frob/raw/{}/{raw_name}", provider.language()),
            raw,
        );
        let plan = CoveragePlan {
            program: Program::Git,
            args: Vec::new(),
            cwd: self.root.clone(),
            env: Vec::new(),
            report,
        };
        let lcov = provider.to_lcov(&self.ws, &plan).expect("to_lcov");
        let normalised = Lcov::parse(&lcov, &self.root).render();
        let target = language_report(&self.root, provider.language());
        std::fs::create_dir_all(target.parent().expect("parent")).expect("mkdir");
        std::fs::write(target, normalised).expect("write info");
    }

    /// Seed every language: Rust 3/4, Python 4/5, JavaScript 1/2 and C# 9/10 lines hit, plus dependency and build-output junk.
    fn seed_all(&self) {
        let abs = |rel: &str| gob_path::Shown::of(&self.root.join(rel)).to_string();
        self.ingest(
            &RustCoverage,
            "lcov.info",
            &record(&abs("src/lib.rs"), 4, 3),
        );
        self.ingest(&PythonCoverage, "lcov.info", &record("py/pkg/a.py", 5, 4));
        let js = record("js/src/a.ts", 2, 1) + &record("js/node_modules/dep/index.js", 10, 0);
        self.ingest(&VitestCoverage, "lcov.info", &js);
        let cs = record(&abs("cs/Calc.cs"), 10, 9) + &record(&abs("cs/obj/Debug/gen.cs"), 10, 0);
        self.ingest(&CsharpCoverage, "coverage.info", &cs);
        merge_reports(&self.root, "lcov.info").expect("merge");
    }

    /// `frob.toml` with the fresh-repo rules off and one threshold per language scope.
    fn configure(&self, thresholds: &[(&str, f64)]) {
        let mut text = String::from("[coverage]\nrequire_reports = true\n\n");
        for (scope, line) in thresholds {
            let _ = write!(
                text,
                "[[coverage.threshold]]\nscope = \"{scope}\"\nline = {line}\n\n"
            );
        }
        write(&self.root, "frob.toml", &text);
        common::turn_off_fresh_repo_rules(&self.root);
    }

    /// `frob check --json` in the fixture, returning only the COV004 findings.
    fn cov004(&self) -> Vec<Value> {
        let out: Output = common::frob_command()
            .current_dir(&self.root)
            .env_remove("FROB_LOG")
            .args(["check", "--json"])
            .output()
            .expect("run frob");
        let env: Value = serde_json::from_slice(&out.stdout)
            .unwrap_or_else(|e| panic!("not JSON ({e}): {}", String::from_utf8_lossy(&out.stdout)));
        env["data"]["findings"]
            .as_array()
            .expect("data.findings array")
            .iter()
            .filter(|f| f["rule"] == "COV004")
            .cloned()
            .collect()
    }
}

const MET: &[(&str, f64)] = &[
    ("src/**", 75.0),
    ("py/**", 80.0),
    ("js/src/**", 50.0),
    ("cs/Calc.cs", 90.0),
];

// frob:tests PROVIDERS
#[test]
fn every_language_has_a_provider_that_sees_its_tests() {
    let fx = Fixture::new();
    let seen: Vec<&str> = PROVIDERS
        .iter()
        .filter(|p| p.has_tests(&fx.root))
        .map(|p| p.language())
        .collect();
    for lang in ["rust", "python", "javascript", "csharp"] {
        assert!(seen.contains(&lang), "{lang} not detected: {seen:?}");
    }
}

// frob:tests merge_reports
// frob:tests cov004
#[test]
fn thresholds_met_in_every_language_are_clean() {
    let fx = Fixture::new();
    fx.seed_all();
    fx.configure(MET);
    let merged = std::fs::read_to_string(fx.root.join("lcov.info")).expect("merged");
    assert!(!merged.contains("node_modules"), "{merged}");
    assert!(!merged.contains("/obj/"), "{merged}");
    assert!(
        merged.contains("SF:src/lib.rs"),
        "paths are repo-relative: {merged}"
    );
    let found = fx.cov004();
    assert!(found.is_empty(), "{found:?}");
}

// frob:tests cov004
#[test]
fn each_language_is_reported_against_its_own_threshold() {
    let fx = Fixture::new();
    fx.seed_all();
    // Measured: rust 75, python 80, javascript 50, csharp 90; ask for one point more of each.
    fx.configure(&[
        ("src/**", 76.0),
        ("py/**", 81.0),
        ("js/src/**", 51.0),
        ("cs/Calc.cs", 91.0),
    ]);
    let found = fx.cov004();
    assert_eq!(found.len(), 4, "{found:?}");
    for (scope, measured, required) in [
        ("src/**", "75.00%", "76.00%"),
        ("py/**", "80.00%", "81.00%"),
        ("js/src/**", "50.00%", "51.00%"),
        ("cs/Calc.cs", "90.00%", "91.00%"),
    ] {
        let hit = found
            .iter()
            .filter_map(|f| f["message"].as_str())
            .find(|m| m.contains(&format!("`{scope}`")))
            .unwrap_or_else(|| panic!("no finding for {scope}: {found:?}"));
        assert!(hit.contains("line coverage"), "{hit}");
        assert!(hit.contains(measured), "{hit}");
        assert!(hit.contains(required), "{hit}");
    }
}

// frob:tests cov004
#[test]
fn a_language_with_tests_but_no_report_is_flagged() {
    let fx = Fixture::new();
    fx.seed_all();
    std::fs::remove_file(language_report(&fx.root, "python")).expect("remove python report");
    fx.configure(MET);
    let found = fx.cov004();
    let messages: Vec<&str> = found.iter().filter_map(|f| f["message"].as_str()).collect();
    assert!(
        messages.iter().any(|m| m.contains("python")
            && (m.contains("no coverage report") || m.contains("coverage not run"))),
        "{messages:?}"
    );
}
