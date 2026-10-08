//! The node runtime bridge against stub `tailwindcss`, `postcss` and `@tailwindcss/node`
//! modules: the real helper runs under real node, only Tailwind itself is faked, so these tests
//! need `node` but no npm install. Without node they skip loudly (set `CRUNK_REQUIRE_NODE=1` in
//! the node CI job to fail instead).

// frob:ticket 01M43ARYX61ESX3S9XG1WS0DQ4

#![cfg(feature = "runtime")]

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use crunk_tailwind::runtime::{
    ClassStatus, Evaluation, Options, Runtime, RuntimeError, Sources, TailwindVersion,
    UNRESOLVED_CODE, Unresolved,
};
use gob_cache::Cache;

fn node_present() -> bool {
    let found = gob_exec::Program::Tool {
        name: "node".into(),
    }
    .resolve()
    .is_ok();
    if !found {
        assert!(
            std::env::var_os("CRUNK_REQUIRE_NODE").is_none(),
            "CRUNK_REQUIRE_NODE is set but node is not on PATH"
        );
        eprintln!("SKIP: node is not on PATH (set CRUNK_REQUIRE_NODE=1 to make this a failure)");
    }
    found
}

fn write(path: &Path, text: &str) {
    std::fs::create_dir_all(path.parent().unwrap()).unwrap();
    std::fs::write(path, text).unwrap();
}

/// A project with a stub Tailwind of `major` installed in `node_modules`.
struct Project {
    dir: tempfile::TempDir,
    state: tempfile::TempDir,
}

impl Project {
    fn new(major: u64) -> Self {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        write(&root.join("package.json"), "{}");
        let nm = root.join("node_modules");
        write(
            &nm.join("tailwindcss/package.json"),
            &format!("{{\"name\":\"tailwindcss\",\"version\":\"{major}.9.9\"}}"),
        );
        if major == 3 {
            // postcss([plugin]).process(): emit one rule per candidate in `content[0].raw`,
            // except candidates containing "bogus"; log each run to runs.log.
            write(
                &nm.join("postcss/index.js"),
                r#"const fs = require("fs");
module.exports = (plugins) => ({
  async process() {
    fs.appendFileSync("runs.log", "run\n");
    if (process.env.STUB_MODE === "hang") { await new Promise(() => setTimeout(() => {}, 60000)); }
    const cfg = plugins[0].config;
    const raw = cfg.content[0].raw.split(" ").filter(Boolean);
    if (cfg.theme && cfg.theme.explode) throw new Error("boom from config");
    let css = "";
    for (const c of raw) {
      if (c.includes("bogus")) continue;
      const sel = "." + c.replace(/[^a-zA-Z0-9_-]/g, (m) => "\\" + m);
      css += `${sel} { display: flex; }\n`;
    }
    if (raw.includes("flood")) css += "/*" + "x".repeat(4096) + "*/";
    return { css };
  },
});
"#,
            );
            write(
                &nm.join("tailwindcss/index.js"),
                "module.exports = (opts) => ({ config: opts.config });\n",
            );
            write(
                &nm.join("tailwindcss/loadConfig.js"),
                "module.exports = (p) => require(p);\n",
            );
            write(
                &nm.join("tailwindcss/resolveConfig.js"),
                r##"module.exports = (cfg) => ({
  theme: { colors: { white: "#fff", ...((cfg.theme && cfg.theme.extend && cfg.theme.extend.colors) || {}) } },
});
"##,
            );
        } else {
            write(
                &nm.join("@tailwindcss/node/index.js"),
                r#"const fs = require("fs");
module.exports = {
  async compile() {
    fs.appendFileSync("runs.log", "run\n");
    return { build: (cands) => cands.filter((c) => !c.includes("bogus")).map((c) => `.${c} { display: grid; }`).join("\n") };
  },
  async __unstable__loadDesignSystem(css) {
    const entries = css.includes("--color-brand")
      ? [["--color-brand", { value: "red" }], ["--spacing", { value: "0.25rem" }]]
      : [["--spacing", { value: "0.25rem" }]];
    return { theme: { entries: () => entries } };
  },
};
"#,
            );
        }
        Self {
            dir,
            state: tempfile::tempdir().unwrap(),
        }
    }

    fn root(&self) -> &Path {
        self.dir.path()
    }

    fn runtime(&self, mutate: impl FnOnce(&mut Options)) -> (Runtime, Arc<Mutex<Vec<String>>>) {
        let mut options = Options {
            state_dir: Some(self.state.path().to_path_buf()),
            ..Options::default()
        };
        mutate(&mut options);
        let notices = Arc::new(Mutex::new(Vec::new()));
        let seen = Arc::clone(&notices);
        let cache = Cache::open(&self.state.path().join("cache"));
        let rt =
            Runtime::new(self.root(), options, cache).with_notice_sink(Arc::new(move |t: &str| {
                seen.lock().unwrap().push(t.to_owned());
            }));
        (rt, notices)
    }

    fn runs(&self) -> usize {
        std::fs::read_to_string(self.root().join("runs.log")).map_or(0, |t| t.lines().count())
    }
}

fn candidates(names: &[&str]) -> Vec<String> {
    names.iter().map(|s| (*s).to_owned()).collect()
}

fn v3_sources(project: &Project) -> Sources {
    let config = project.root().join("tailwind.config.js");
    write(
        &config,
        "module.exports = { theme: { extend: { colors: { brand: 'red' } } } };\n",
    );
    Sources {
        config_path: Some(config),
        css_entry: None,
    }
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn compiled_utilities_are_returned_and_then_served_from_the_cache() {
    if !node_present() {
        return;
    }
    let project = Project::new(3);
    let sources = v3_sources(&project);
    let (rt, notices) = project.runtime(|_| {});
    let want = candidates(&["flex", "md:p-4", "bogus-class"]);

    let first = rt
        .evaluate_candidates(&want, &sources)
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(first.version, TailwindVersion::V3);
    let statuses: Vec<ClassStatus> = first.results.iter().map(|r| r.status).collect();
    assert_eq!(
        statuses,
        [ClassStatus::Valid, ClassStatus::Valid, ClassStatus::Invalid]
    );
    assert_eq!(first.results[1].declarations[0].selector, ".md\\:p-4");
    assert_eq!(project.runs(), 1);
    assert_eq!(
        notices.lock().unwrap().len(),
        1,
        "the first run shows the notice"
    );

    let second = rt
        .evaluate_candidates(&want, &sources)
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(second.results, first.results);
    assert_eq!(project.runs(), 1, "a warm run does not start node");

    // A subset is warm; one new candidate runs node for just that candidate.
    rt.evaluate_candidates(&candidates(&["flex"]), &sources)
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(project.runs(), 1);
    let more = rt
        .evaluate_candidates(&candidates(&["flex", "grid"]), &sources)
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(more.results.len(), 2);
    assert_eq!(project.runs(), 2);
    assert_eq!(
        notices.lock().unwrap().len(),
        1,
        "the notice shows once per config"
    );
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn editing_the_config_invalidates_the_cache() {
    if !node_present() {
        return;
    }
    let project = Project::new(3);
    let sources = v3_sources(&project);
    let (rt, _) = project.runtime(|_| {});
    let want = candidates(&["flex"]);
    rt.evaluate_candidates(&want, &sources)
        .unwrap()
        .resolved()
        .unwrap();
    write(
        sources.config_path.as_ref().unwrap(),
        "module.exports = { theme: { extend: { colors: { brand: 'blue' } } } };\n",
    );
    rt.evaluate_candidates(&want, &sources)
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(project.runs(), 2);
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn a_v4_project_compiles_through_the_css_entry() {
    if !node_present() {
        return;
    }
    let project = Project::new(4);
    let entry = project.root().join("src/index.css");
    write(&entry, "@import \"tailwindcss\";\n");
    let sources = Sources {
        config_path: None,
        css_entry: Some(entry),
    };
    let (rt, _) = project.runtime(|_| {});
    let got = rt
        .evaluate_candidates(&candidates(&["flex"]), &sources)
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(got.version, TailwindVersion::V4);
    assert_eq!(got.results[0].declarations[0].value, "grid");

    let no_entry = rt
        .evaluate_candidates(&candidates(&["x"]), &Sources::default())
        .unwrap();
    assert_eq!(
        no_entry,
        Evaluation::Unresolved(Unresolved::MissingCssEntry)
    );
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn without_node_the_result_is_unresolved_with_the_reason_never_clean() {
    let project = Project::new(3);
    let sources = v3_sources(&project);
    let (rt, notices) = project.runtime(|o| o.node_binary = "no-such-node-binary".to_owned());
    let want = candidates(&["flex"]);
    let got = rt.evaluate_candidates(&want, &sources).unwrap();
    let Evaluation::Unresolved(reason) = got else {
        panic!("expected Unresolved, got {got:?}");
    };
    assert!(
        matches!(&reason, Unresolved::NodeMissing { binary } if binary == "no-such-node-binary")
    );
    assert_eq!(reason.code(), UNRESOLVED_CODE);
    assert_eq!(UNRESOLVED_CODE, "unresolved-by-tailwind");
    assert!(reason.to_string().contains("no-such-node-binary"));
    let rows = reason.class_results(&want);
    assert_eq!(rows[0].status, ClassStatus::Unresolved);
    assert!(
        notices.lock().unwrap().is_empty(),
        "nothing ran, so no notice"
    );
    assert_eq!(project.runs(), 0);

    let theme = rt.resolve_theme(&sources).unwrap();
    assert!(matches!(
        theme,
        Evaluation::Unresolved(Unresolved::NodeMissing { .. })
    ));
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn static_mode_and_a_missing_install_are_unresolved_and_start_nothing() {
    let project = Project::new(3);
    let sources = v3_sources(&project);
    let (rt, _) = project.runtime(|o| o.static_mode = true);
    assert_eq!(
        rt.evaluate_candidates(&candidates(&["flex"]), &sources)
            .unwrap(),
        Evaluation::Unresolved(Unresolved::StaticMode)
    );
    assert_eq!(project.runs(), 0);

    let bare = tempfile::tempdir().unwrap();
    let state = tempfile::tempdir().unwrap();
    let rt = Runtime::new(
        bare.path(),
        Options {
            state_dir: Some(state.path().to_path_buf()),
            ..Options::default()
        },
        Cache::null(),
    );
    let got = rt
        .evaluate_candidates(&candidates(&["flex"]), &Sources::default())
        .unwrap();
    assert!(
        matches!(
            got,
            Evaluation::Unresolved(Unresolved::TailwindMissing { .. })
        ),
        "{got:?}"
    );
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn a_helper_over_the_output_cap_is_killed_and_the_cap_is_named() {
    if !node_present() {
        return;
    }
    let project = Project::new(3);
    let sources = v3_sources(&project);
    let (rt, _) = project.runtime(|o| o.output_cap = 1024);
    let err = rt
        .evaluate_candidates(&candidates(&["flood"]), &sources)
        .unwrap_err();
    assert_eq!(err, RuntimeError::OutputCap { limit: 1024 });
    assert!(err.to_string().contains("1024 byte cap"), "{err}");
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn a_helper_over_the_timeout_is_killed_and_reported() {
    if !node_present() {
        return;
    }
    let project = Project::new(3);
    // The stub hangs when STUB_MODE=hang; the scrubbed child cannot see it, so hang via config.
    write(
        &project.root().join("node_modules/postcss/index.js"),
        "module.exports = () => ({ process: () => new Promise(() => setInterval(() => {}, 1000)) });\n",
    );
    let sources = v3_sources(&project);
    let (rt, _) = project.runtime(|o| o.timeout = Duration::from_secs(1));
    let started = std::time::Instant::now();
    let err = rt
        .evaluate_candidates(&candidates(&["flex"]), &sources)
        .unwrap_err();
    assert_eq!(err, RuntimeError::Timeout { secs: 1 });
    assert!(started.elapsed() < Duration::from_secs(15));
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.evaluate_candidates
#[test]
fn an_error_reported_by_the_helper_is_a_typed_error_with_its_message() {
    if !node_present() {
        return;
    }
    let project = Project::new(3);
    let config = project.root().join("tailwind.config.js");
    write(&config, "module.exports = { theme: { explode: true } };\n");
    let (rt, _) = project.runtime(|_| {});
    let err = rt
        .evaluate_candidates(
            &candidates(&["flex"]),
            &Sources {
                config_path: Some(config),
                css_entry: None,
            },
        )
        .unwrap_err();
    assert!(
        matches!(&err, RuntimeError::HelperReported { error } if error.contains("boom from config")),
        "{err}"
    );
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.resolve_theme
#[test]
fn the_theme_is_the_projects_own_contribution_for_v3_and_v4() {
    if !node_present() {
        return;
    }
    let v3 = Project::new(3);
    let (rt, _) = v3.runtime(|_| {});
    let theme = rt
        .resolve_theme(&v3_sources(&v3))
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(theme.theme.get("brand").map(String::as_str), Some("red"));
    assert!(
        !theme.theme.contains_key("white"),
        "tailwind's own defaults are diffed away"
    );

    let v4 = Project::new(4);
    let entry = v4.root().join("src/index.css");
    write(
        &entry,
        "@import \"tailwindcss\";\n@theme { --color-brand: red; }\n",
    );
    let (rt, _) = v4.runtime(|_| {});
    let theme = rt
        .resolve_theme(&Sources {
            config_path: None,
            css_entry: Some(entry),
        })
        .unwrap()
        .resolved()
        .unwrap();
    assert_eq!(theme.version, TailwindVersion::V4);
    assert_eq!(
        theme.theme.get("--color-brand").map(String::as_str),
        Some("red")
    );
    assert!(!theme.theme.contains_key("--spacing"));
}

// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.doctor
#[test]
fn doctor_reports_node_tailwindcss_and_the_helper() {
    let project = Project::new(3);
    let (missing, _) = project.runtime(|o| o.node_binary = "no-such-node-binary".to_owned());
    let report = missing.doctor(&Sources::default());
    let node_row = report.rows.iter().find(|r| r.item == "node").unwrap();
    assert_eq!(node_row.state, "missing");
    assert!(
        report
            .issues
            .iter()
            .any(|i| i.contains("no-such-node-binary"))
    );
    assert!(report.info.iter().any(|i| i.contains(UNRESOLVED_CODE)));
    assert_eq!(
        report
            .rows
            .iter()
            .find(|r| r.item == "tailwindcss")
            .unwrap()
            .detail,
        "3.9.9"
    );

    if !node_present() {
        return;
    }
    let (rt, _) = project.runtime(|_| {});
    let report = rt.doctor(&v3_sources(&project));
    let helper = report.rows.iter().find(|r| r.item == "helper").unwrap();
    assert_eq!(helper.state, "ok", "{report:?}");
    assert!(report.issues.is_empty(), "{report:?}");
}

/// A real project check, off unless `CRUNK_REAL_TAILWIND_PROJECT` names a project root (with
/// `CRUNK_REAL_TAILWIND_CSS` naming its v4 CSS entry relative to it).
// frob:tests crates/crunk-tailwind/src/runtime/mod.rs::Runtime.resolve_theme
#[test]
fn a_real_project_resolves_its_theme_when_one_is_named() {
    let (Some(root), Some(css)) = (
        std::env::var_os("CRUNK_REAL_TAILWIND_PROJECT"),
        std::env::var_os("CRUNK_REAL_TAILWIND_CSS"),
    ) else {
        return;
    };
    let root = PathBuf::from(root);
    let state = tempfile::tempdir().unwrap();
    let rt = Runtime::new(
        &root,
        Options {
            state_dir: Some(state.path().to_path_buf()),
            quiet_notice: true,
            ..Options::default()
        },
        Cache::null(),
    );
    let theme = rt
        .resolve_theme(&Sources {
            config_path: None,
            css_entry: Some(root.join(css)),
        })
        .unwrap()
        .resolved()
        .unwrap();
    assert!(!theme.theme.is_empty());
}
