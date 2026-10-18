//! Running the selected tests: `cargo nextest run -p <pkg> -E '<filter>'`, `pytest <node id>...`, `vitest run` or `jest` per member and `dotnet test` per project through gob-exec.

use std::collections::{BTreeMap, BTreeSet};
use std::path::{Path, PathBuf};
use std::time::Duration;

use frob_evidence::provider::{
    Capture, DotnetRun, JsRun, NODE_PROGRAM, UnityMode, UnityRun, UnityTestRun, run_dotnet,
    run_js_tests, run_nextest, run_pytest, run_unity, unity_assembly_name, unity_project_dir,
};
use frob_evidence::record::Provider;
use gob_exec::Runner;
use gob_walk::{WalkConfig, walk};

// frob:ticket 01M4CTTRCCJMVJDYVEJZWTT8J3
use crate::catalog::Packages;
use crate::error::Result;
use crate::node::{JsMembers, is_runner_test_file};
use crate::select::{CsharpOwner, CsharpOwners, Framework, TestTarget};

/// How to run: where, how long, and whether to run everything.
#[derive(Debug, Clone)]
pub struct RunOptions {
    /// The work tree root the runners run in.
    pub root: PathBuf,
    /// Wall-clock limit for one runner process.
    pub timeout: Duration,
    /// `--profile` for nextest; empty passes none.
    pub profile: String,
    /// `[evidence] allowed_tools`: pytest runs only when it is listed.
    pub allowed_tools: Vec<String>,
    /// Run the whole workspace instead of the selection.
    pub all: bool,
    /// The program vitest and jest need (`node`); a missing one refuses the run.
    pub node: String,
    // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
    /// `[evidence.dotnet] path`: the `dotnet` executable; empty finds it on `PATH`.
    pub dotnet_path: String,
    // frob:ticket 01M4FDPNXX3X842GBA3FP0SDK3
    /// `[tests] python`: the interpreter that runs pytest; empty prefers the repository's `.venv`.
    pub python: String,
    // frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
    /// `[evidence.unity] editor`: the Unity editor executable; empty finds the Hub install of the project's version.
    pub unity_editor: String,
}

impl RunOptions {
    /// Options for the work tree at `root` with the default node program ([`NODE_PROGRAM`]).
    pub fn new(
        root: PathBuf,
        timeout: Duration,
        profile: String,
        allowed_tools: Vec<String>,
        all: bool,
    ) -> Self {
        Self {
            root,
            timeout,
            profile,
            allowed_tools,
            all,
            node: NODE_PROGRAM.to_owned(),
            dotnet_path: String::new(),
            python: String::new(),
            unity_editor: String::new(),
        }
    }
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// What one runner produced.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameworkRun {
    /// The runner.
    pub framework: Framework,
    /// The arguments that were used (after `cargo nextest run`, `pytest`, or `vitest` and `jest`: test files relative to the member).
    pub args: Vec<String>,
    /// The directory vitest or jest ran in, or the Cargo workspace directory nextest ran in, relative to the work tree (empty at the root and for the other runners).
    pub member: String,
    /// Verdict, executed test names and the redacted transcript.
    pub capture: Capture,
}

impl FrameworkRun {
    // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
    /// The evidence reference of this run: its arguments, with vitest and jest files made repo-relative (the member alone when it ran whole).
    pub fn reference(&self) -> String {
        if !matches!(self.framework, Framework::Vitest | Framework::Jest) || self.member.is_empty()
        {
            return join_args(&self.args);
        }
        if self.args.is_empty() {
            return self.member.clone();
        }
        let files: Vec<String> = self
            .args
            .iter()
            .map(|a| format!("{}/{a}", self.member))
            .collect();
        join_args(&files)
    }
    /// The evidence provider that records this run.
    pub const fn provider(&self) -> Provider {
        match self.framework {
            Framework::Nextest => Provider::Nextest,
            Framework::Pytest => Provider::Pytest,
            // frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
            Framework::Vitest => Provider::Vitest,
            Framework::Jest => Provider::Jest,
            // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
            Framework::Dotnet => Provider::Dotnet,
            // frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
            Framework::Unity => Provider::Unity,
        }
    }
}

/// What a run produced: one entry per runner that ran.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct RunReport {
    /// The runs, nextest first.
    pub runs: Vec<FrameworkRun>,
}

impl RunReport {
    /// True when every run passed (and at least one ran).
    pub fn passed(&self) -> bool {
        !self.runs.is_empty() && self.runs.iter().all(|r| r.capture.passed)
    }

    /// Executed test names of every run.
    pub fn executed(&self) -> Vec<String> {
        self.runs
            .iter()
            .flat_map(|r| r.capture.tests.iter().cloned())
            .collect()
    }

    /// Failed test names of every run.
    pub fn failed(&self) -> Vec<String> {
        self.runs
            .iter()
            .flat_map(|r| r.capture.failed_tests.iter().cloned())
            .collect()
    }

    /// The exit code of the first run that did not pass, else of the first run.
    pub fn exit_code(&self) -> Option<i32> {
        self.runs
            .iter()
            .find(|r| !r.capture.passed)
            .or_else(|| self.runs.first())
            .and_then(|r| r.capture.exit_code)
    }
}

/// The filter arguments for the nextest tests of `selected`: `-p` per package plus one `-E` filterset (none when it has no nextest test).
///
/// The filterset pairs each package with its own tests, so equal test names in
/// different packages do not drag each other in:
/// `(package(=a) & (test(=x) | test(=y))) | (package(=b) & test(=z))`.
pub fn nextest_args(selected: &[TestTarget]) -> Vec<String> {
    let mut by_pkg: BTreeMap<&str, Vec<&str>> = BTreeMap::new();
    for t in selected
        .iter()
        .filter(|t| t.framework == Framework::Nextest)
    {
        by_pkg.entry(&t.package).or_default().push(&t.test_path);
    }
    if by_pkg.is_empty() {
        return Vec::new();
    }
    let mut args = Vec::new();
    for pkg in by_pkg.keys() {
        args.extend(["-p".to_owned(), (*pkg).to_owned()]);
    }
    let expr = by_pkg
        .iter()
        .map(|(pkg, tests)| {
            let any = tests
                .iter()
                .map(|t| format!("test(={t})"))
                .collect::<Vec<_>>()
                .join(" | ");
            format!("(package(={pkg}) & ({any}))")
        })
        .collect::<Vec<_>>()
        .join(" | ");
    args.extend(["-E".to_owned(), expr]);
    args
}

// frob:ticket 01M4CTTRCCJMVJDYVEJZWTT8J3
/// The nextest runs for `selected`: the work-tree-relative directory of each owning Cargo workspace (empty at the root) with its [`nextest_args`].
pub fn nextest_groups(root: &Path, selected: &[TestTarget]) -> Vec<(String, Vec<String>)> {
    let mut packages = Packages::new(root);
    let mut by_dir: BTreeMap<String, Vec<TestTarget>> = BTreeMap::new();
    for t in selected
        .iter()
        .filter(|t| t.framework == Framework::Nextest)
    {
        let file = t.symref.split("::").next().unwrap_or_default();
        let dir = packages
            .cargo_root(file)
            .map(|d| d.to_string_lossy().replace('\\', "/"))
            .unwrap_or_default();
        by_dir.entry(dir).or_default().push(t.clone());
    }
    let mut groups = Vec::new();
    for (dir, targets) in by_dir {
        let chunks = chunk_targets(&targets, MAX_FILTER_BYTES);
        if chunks.len() > 1 {
            tracing::info!(
                dir,
                targets = targets.len(),
                chunks = chunks.len(),
                "nextest filter split to keep argv bounded"
            );
        }
        groups.extend(chunks.into_iter().map(|c| (dir.clone(), nextest_args(&c))));
    }
    groups
}

// frob:ticket 01M4X64ATCQ55PKCTX0HEVH0W5
/// Byte budget of one nextest invocation's filter arguments (under Linux's 128 KiB single-argument limit, so the `-E` expression never trips E2BIG).
pub const MAX_FILTER_BYTES: usize = 64 * 1024;

// frob:ticket 01M4X64ATCQ55PKCTX0HEVH0W5
/// Split `targets` into consecutive chunks whose [`nextest_args`] each stay within `budget` bytes (a single oversized target gets its own chunk).
pub fn chunk_targets(targets: &[TestTarget], budget: usize) -> Vec<Vec<TestTarget>> {
    let mut chunks: Vec<Vec<TestTarget>> = Vec::new();
    let mut size = 0usize;
    for t in targets {
        // Upper bound of what the target adds: `-p pkg`, `test(=path) | ` and the package clause.
        let cost = 2 * t.package.len() + t.test_path.len() + 48;
        match chunks.last_mut() {
            Some(cur) if size + cost <= budget => {
                cur.push(t.clone());
                size += cost;
            }
            _ => {
                chunks.push(vec![t.clone()]);
                size = cost;
            }
        }
    }
    chunks
}

// frob:ticket 01M4CTTRCCJMVJDYVEJZWTT8J3
/// Why a failed report failed: the exit code and the last lines of the first failing runner's stderr (empty when everything passed).
pub fn failure_cause(report: &RunReport) -> String {
    const TAIL_LINES: usize = 15;
    const TAIL_CHARS: usize = 1500;
    let Some(run) = report.runs.iter().find(|r| !r.capture.passed) else {
        return String::new();
    };
    let exit = run.capture.exit_code.map_or_else(
        || "no exit code (signal or timeout)".to_owned(),
        |c| format!("exit code {c}"),
    );
    let lines: Vec<&str> = run.capture.transcript.lines().collect();
    let mut tail = lines[lines.len().saturating_sub(TAIL_LINES)..].join("\n");
    if tail.len() > TAIL_CHARS {
        let mut cut = tail.len() - TAIL_CHARS;
        while !tail.is_char_boundary(cut) {
            cut += 1;
        }
        tail = tail[cut..].to_owned();
    }
    let place = if run.member.is_empty() {
        String::new()
    } else {
        format!(" in {}", run.member)
    };
    format!(
        "{:?} runner{place} failed with {exit}; stderr tail:\n{}",
        run.framework,
        tail.trim_end()
    )
}

/// Quote `args` so [`frob_evidence::provider::split_args`] reads them back unchanged.
pub fn join_args(args: &[String]) -> String {
    args.iter()
        .map(|a| {
            if a.is_empty() || a.contains(char::is_whitespace) || a.contains(['\'', '"']) {
                format!("'{a}'")
            } else {
                a.clone()
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// The pytest arguments for `selected`: the node ids of its Python tests, in order.
pub fn pytest_args(selected: &[TestTarget]) -> Vec<String> {
    selected
        .iter()
        .filter(|t| t.framework == Framework::Pytest)
        .map(|t| t.test_path.clone())
        .collect()
}

// frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
/// True when the work tree at `root` holds a Python test file (so `--all` must run pytest).
fn has_python_tests(root: &Path) -> bool {
    match walk(root, &WalkConfig::default()) {
        Ok(walked) => walked
            .files
            .iter()
            .any(|f| gob_symbols::is_python_test_file(&f.path)),
        Err(e) => {
            tracing::warn!(error = %e, "could not walk for Python tests; pytest skipped under --all");
            false
        }
    }
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// One vitest or jest invocation: the runner, the member it runs in and the test files (empty runs the whole member).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct JsGroup {
    /// Which runner.
    pub framework: Framework,
    /// Member directory relative to the work tree (empty at the root).
    pub member: String,
    /// Test files relative to the member, sorted and unique.
    pub files: Vec<String>,
}

// frob:ticket 01M48NCJSRM2PV84779RNQ92ZK
/// The vitest and jest invocations for `selected`: one per runner and member, running the files of the selected tests.
///
/// With `opts.all` every member that declares its runner (dependency or config file, not just an import) and holds a runner-found test file (`*.test.*`, `*.spec.*`) is run whole instead.
/// A selected test runs through its file, so its siblings run too; the evidence names every test that executed.
pub fn js_groups(selected: &[TestTarget], opts: &RunOptions) -> Vec<JsGroup> {
    let mut groups: BTreeMap<(Framework, String), BTreeSet<String>> = BTreeMap::new();
    if opts.all {
        let mut members = JsMembers::new(&opts.root);
        let walked = match walk(&opts.root, &WalkConfig::default()) {
            Ok(w) => w.files,
            Err(e) => {
                tracing::warn!(error = %e, "could not walk for JavaScript tests; vitest and jest skipped under --all");
                Vec::new()
            }
        };
        for f in walked.iter().filter(|f| is_runner_test_file(&f.path)) {
            // No file text: under --all only a member that declares its runner runs (a fixture that merely imports vitest does not).
            if let Some(m) = members.resolve(&f.path, None) {
                groups.entry((m.framework, m.dir)).or_default();
            }
        }
    } else {
        for t in selected
            .iter()
            .filter(|t| matches!(t.framework, Framework::Vitest | Framework::Jest))
        {
            let file = t.test_path.split("::").next().unwrap_or_default();
            let rel = if t.package.is_empty() {
                file
            } else {
                file.strip_prefix(&format!("{}/", t.package))
                    .unwrap_or(file)
            };
            groups
                .entry((t.framework, t.package.clone()))
                .or_default()
                .insert(rel.to_owned());
        }
    }
    groups
        .into_iter()
        .map(|((framework, member), files)| JsGroup {
            framework,
            member,
            files: files.into_iter().collect(),
        })
        .collect()
}

// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
/// One `dotnet test` invocation: a project and the test ids to run (empty runs the whole project).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct DotnetGroup {
    /// Repo-relative `.csproj` path.
    pub project: String,
    /// Fully qualified test ids, sorted and unique.
    pub ids: Vec<String>,
}

// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
/// The C# files of the work tree that hold tests, empty (with a warning) when the walk fails.
fn csharp_test_files(root: &Path) -> Vec<String> {
    match walk(root, &WalkConfig::default()) {
        Ok(walked) => walked
            .files
            .into_iter()
            .map(|f| f.path)
            .filter(|p| gob_symbols::is_csharp_test_file(p))
            .collect(),
        Err(e) => {
            tracing::warn!(error = %e, "could not walk for C# tests; dotnet and unity skipped under --all");
            Vec::new()
        }
    }
}

// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
/// The `dotnet test` invocations for `selected`: one per project, running the selected ids.
///
/// With `opts.all` every project that owns a C# test file is run whole instead.
pub fn dotnet_groups(selected: &[TestTarget], opts: &RunOptions) -> Vec<DotnetGroup> {
    let mut groups: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
    if opts.all {
        let mut owners = CsharpOwners::new(&opts.root);
        for file in csharp_test_files(&opts.root) {
            if let Some(CsharpOwner::Project(p)) = owners.owner(&file) {
                groups.entry(p).or_default();
            }
        }
    } else {
        for t in selected.iter().filter(|t| t.framework == Framework::Dotnet) {
            groups
                .entry(t.package.clone())
                .or_default()
                .insert(t.test_path.clone());
        }
    }
    groups
        .into_iter()
        .map(|(project, ids)| DotnetGroup {
            project,
            ids: ids.into_iter().collect(),
        })
        .collect()
}

// frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
/// The Unity assemblies `selected` (or, with `opts.all`, the work tree's test assemblies) would run, sorted and unique.
pub fn unity_assemblies(selected: &[TestTarget], opts: &RunOptions) -> Vec<String> {
    let mut found: BTreeSet<String> = BTreeSet::new();
    if opts.all {
        let mut owners = CsharpOwners::new(&opts.root);
        for file in csharp_test_files(&opts.root) {
            if let Some(CsharpOwner::Assembly(a)) = owners.owner(&file)
                && owners.is_test_assembly(&a)
            {
                found.insert(a);
            }
        }
    } else {
        found.extend(
            selected
                .iter()
                .filter(|t| t.framework == Framework::Unity)
                .map(|t| t.package.clone()),
        );
    }
    found.into_iter().collect()
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// One Unity batch run: the assemblies of one project on one test platform, and the test ids to run (empty runs them whole).
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct UnityGroup {
    /// The Unity project directory (absolute).
    pub project: PathBuf,
    /// The test platform.
    pub mode: &'static str,
    /// Repo-relative `.asmdef` paths, sorted and unique.
    pub assemblies: Vec<String>,
    /// Fully qualified test ids, sorted and unique.
    pub ids: Vec<String>,
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// The Unity batch runs for `selected`: one per (project, test platform), `EditMode` or `PlayMode` by what each assembly is.
///
/// With `opts.all` every test assembly runs whole.
pub fn unity_groups(selected: &[TestTarget], opts: &RunOptions) -> Vec<UnityGroup> {
    type Key = (PathBuf, &'static str);
    let mut owners = CsharpOwners::new(&opts.root);
    let mut groups: BTreeMap<Key, (BTreeSet<String>, BTreeSet<String>)> = BTreeMap::new();
    let mut add = |owners: &mut CsharpOwners, assembly: &str, id: Option<&str>| {
        let mode = match owners.test_mode(assembly) {
            Some(gob_symbols::UnityTestMode::PlayMode) => UnityMode::PlayMode,
            _ => UnityMode::EditMode,
        };
        let key = (unity_project_dir(&opts.root, assembly), mode.as_str());
        let entry = groups.entry(key).or_default();
        entry.0.insert(assembly.to_owned());
        if let Some(id) = id {
            entry.1.insert(id.to_owned());
        }
    };
    if opts.all {
        for assembly in unity_assemblies(selected, opts) {
            add(&mut owners, &assembly, None);
        }
    } else {
        for t in selected.iter().filter(|t| t.framework == Framework::Unity) {
            add(&mut owners, &t.package, Some(&t.test_path));
        }
    }
    groups
        .into_iter()
        .map(|((project, mode), (assemblies, ids))| UnityGroup {
            project,
            mode,
            assemblies: assemblies.into_iter().collect(),
            ids: ids.into_iter().collect(),
        })
        .collect()
}

// frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
/// Run `selected` (or the whole workspace with `opts.all`) with cargo nextest, pytest, vitest, jest and dotnet.
///
/// A runner runs only when it has selected tests (or, with `opts.all`, when the work
/// tree has tests for it); nextest runs first.
///
/// # Errors
///
/// [`crate::TestsError::Evidence`] when pytest is not allowlisted, [`crate::TestsError::Exec`] when a runner cannot be started,
/// and the errors of the unity provider (an open editor, a missing license) when Unity tests are selected.
#[allow(clippy::too_many_lines)]
pub fn run(runner: &Runner, selected: &[TestTarget], opts: &RunOptions) -> Result<RunReport> {
    let mut report = RunReport::default();
    // frob:ticket 01M4CTTRCCJMVJDYVEJZWTT8J3
    let nextest = if opts.all {
        vec![(String::new(), vec!["--workspace".to_owned()])]
    } else {
        nextest_groups(&opts.root, selected)
    };
    for (member, args) in nextest {
        tracing::info!(all = opts.all, member, "running nextest");
        let cwd = opts.root.join(&member);
        let capture = run_nextest(runner, &cwd, &args, &opts.profile, opts.timeout)?;
        report.runs.push(FrameworkRun {
            framework: Framework::Nextest,
            member,
            args,
            capture,
        });
    }
    let pytest = pytest_args(selected);
    if !pytest.is_empty() || (opts.all && has_python_tests(&opts.root)) {
        tracing::info!(all = opts.all, tests = pytest.len(), "running pytest");
        let capture = run_pytest(
            runner,
            &opts.allowed_tools,
            &opts.root,
            &opts.python,
            &pytest,
            opts.timeout,
        )?;
        report.runs.push(FrameworkRun {
            framework: Framework::Pytest,
            member: String::new(),
            args: pytest,
            capture,
        });
    }
    for group in js_groups(selected, opts) {
        tracing::info!(framework = ?group.framework, member = group.member, files = group.files.len(), "running JavaScript tests");
        let provider = match group.framework {
            Framework::Jest => Provider::Jest,
            _ => Provider::Vitest,
        };
        let capture = run_js_tests(
            runner,
            &JsRun {
                provider,
                allowed: &opts.allowed_tools,
                node: &opts.node,
                root: &opts.root,
                member: &group.member,
                args: &group.files,
                timeout: opts.timeout,
            },
        )?;
        report.runs.push(FrameworkRun {
            framework: group.framework,
            member: group.member,
            args: group.files,
            capture,
        });
    }
    // frob:ticket 01M44YQXBGJW1VKDF64YJ5RTJ6
    for group in dotnet_groups(selected, opts) {
        tracing::info!(
            project = group.project,
            ids = group.ids.len(),
            "running dotnet tests"
        );
        let mut args = vec![group.project.clone()];
        args.extend(group.ids.iter().cloned());
        let capture = run_dotnet(
            runner,
            &DotnetRun {
                allowed: &opts.allowed_tools,
                path: &opts.dotnet_path,
                cwd: &opts.root,
                args: &args,
                timeout: opts.timeout,
            },
        )?;
        report.runs.push(FrameworkRun {
            framework: Framework::Dotnet,
            member: String::new(),
            args,
            capture,
        });
    }
    // frob:ticket 01M44YR0AAJ0X0BGXX7F17DMKH
    let home = std::env::var_os("HOME").map(PathBuf::from);
    for group in unity_groups(selected, opts) {
        tracing::info!(
            project = %group.project.display(),
            mode = group.mode,
            assemblies = group.assemblies.len(),
            ids = group.ids.len(),
            "running unity tests"
        );
        let mode = UnityMode::parse(group.mode).unwrap_or(UnityMode::EditMode);
        let names: Vec<String> = group
            .assemblies
            .iter()
            .map(|a| unity_assembly_name(&opts.root, a))
            .collect();
        let capture = run_unity(
            runner,
            &UnityTestRun {
                run: UnityRun {
                    editor: &opts.unity_editor,
                    project: &group.project,
                    base: &opts.root,
                    home: home.as_deref(),
                },
                mode,
                assemblies: &names,
                ids: &group.ids,
            },
            opts.timeout,
        )?;
        let mut args = vec![group.mode.to_owned()];
        args.extend(group.assemblies.iter().cloned());
        args.extend(group.ids.iter().cloned());
        report.runs.push(FrameworkRun {
            framework: Framework::Unity,
            member: String::new(),
            args,
            capture,
        });
    }
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn t(package: &str, test_path: &str) -> TestTarget {
        TestTarget {
            framework: Framework::Nextest,
            package: package.into(),
            test_path: test_path.into(),
            symref: String::new(),
        }
    }

    #[test]
    fn pytest_targets_stay_out_of_the_nextest_filter() {
        let py = TestTarget {
            framework: Framework::Pytest,
            package: String::new(),
            test_path: "tests/test_a.py::TestC::test_m".into(),
            symref: String::new(),
        };
        let sel = [t("a", "tests::x"), py];
        assert_eq!(pytest_args(&sel), ["tests/test_a.py::TestC::test_m"]);
        assert_eq!(nextest_args(&sel), nextest_args(&sel[..1]));
        assert_eq!(sel[1].plan_line(), "pytest tests/test_a.py::TestC::test_m");
        assert!(pytest_args(&sel[..1]).is_empty());
    }

    #[test]
    fn filters_pair_each_package_with_its_tests() {
        let args = nextest_args(&[t("a", "tests::x"), t("a", "tests::y"), t("b", "tests::x")]);
        assert_eq!(
            args,
            [
                "-p",
                "a",
                "-p",
                "b",
                "-E",
                "(package(=a) & (test(=tests::x) | test(=tests::y))) | (package(=b) & (test(=tests::x)))"
            ]
        );
        let joined = join_args(&args);
        assert_eq!(frob_evidence::provider::split_args(&joined).unwrap(), args);
    }

    // frob:ticket 01M4X64ATCQ55PKCTX0HEVH0W5
    #[test]
    fn huge_selection_is_chunked_within_the_argv_budget() {
        // frob:tests crates/frob-tests/src/run.rs::chunk_targets
        let sel: Vec<TestTarget> = (0..20_000)
            .map(|i| {
                t(
                    &format!("pkg{}", i % 50),
                    &format!("module::tests::test_number_{i}"),
                )
            })
            .collect();
        let chunks = chunk_targets(&sel, MAX_FILTER_BYTES);
        assert!(chunks.len() > 1);
        assert_eq!(chunks.iter().map(Vec::len).sum::<usize>(), sel.len());
        for c in &chunks {
            let bytes: usize = nextest_args(c).iter().map(|a| a.len() + 1).sum();
            assert!(bytes <= MAX_FILTER_BYTES, "chunk of {bytes} bytes");
        }
        assert_eq!(chunk_targets(&sel[..3], MAX_FILTER_BYTES).len(), 1);
        assert!(chunk_targets(&[], MAX_FILTER_BYTES).is_empty());
    }

    // frob:ticket 01M43A5MA7GRAACT7E0M525Y1M
    #[test]
    fn a_report_passes_only_when_every_runner_passed() {
        // frob:tests crates/frob-tests/src/run.rs::RunReport.passed
        let one = |framework, passed, code, test: &str| FrameworkRun {
            framework,
            args: Vec::new(),
            member: String::new(),
            capture: Capture {
                exit_code: Some(code),
                passed,
                measured: true,
                tests: vec![test.to_owned()],
                failed_tests: if passed {
                    Vec::new()
                } else {
                    vec![test.to_owned()]
                },
                transcript: String::new(),
            },
        };
        let report = RunReport {
            runs: vec![
                one(Framework::Nextest, true, 0, "a"),
                one(Framework::Pytest, false, 1, "b"),
            ],
        };
        assert!(!report.passed());
        assert_eq!(report.executed(), ["a", "b"]);
        assert_eq!(report.failed(), ["b"]);
        assert_eq!(report.exit_code(), Some(1));
        assert_eq!(report.runs[1].provider(), Provider::Pytest);
        assert!(!RunReport::default().passed());
    }
}
