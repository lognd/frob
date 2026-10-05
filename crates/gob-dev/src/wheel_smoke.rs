//! `cargo dev wheel-smoke`: smoke the built wheel set from the local wheels only.
//!
//! Replaces `packaging/pypi/smoke.sh` (ticket 1T8TCTA). Every install uses
//! `--no-index --find-links <dir>`, never the network index. Metadata of each wheel is checked
//! (name, platform tag, only its own binary, sibling pins at its own version), then four
//! scenarios run in throwaway uv venvs: each product alone (grimble, crunk), `frob` pulling
//! its dependencies and running the fixture-repository loop, and `uv tool install frob` where
//! only frob is on `PATH` and still finds grimble beside itself. Spawns go through `gob-exec`
//! with `Path`-built argv (D86); the fixture loop stays `packaging/smoke/fixture-loop.sh`
//! (shared with the archive smoke), run through `sh`.
// frob:ticket 01M450VBPVEBZQZ5ANM1T8TCTA

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::Spec;

use crate::out::emit;
use crate::wheel::{
    HostOs, Product, WheelError, exe, path_arg, read_products, run_ok, tool, wheels_of,
};

/// Wall-clock limit for one smoke step.
const STEP_TIMEOUT: Duration = Duration::from_mins(15);
/// The product whose binary is the CLI the fixture loop and tool-install scenarios drive.
const FROB: &str = "frob";
/// Fixture loop script, relative to the workspace root (forward slashes: it is handed to `sh`).
const FIXTURE_LOOP: &str = "packaging/smoke/fixture-loop.sh";

/// Python run in a venv to read one wheel: prints JSON with tag, name, version, requires, scripts.
const WHEEL_INFO_PY: &str = r#"import json, sys, zipfile
z = zipfile.ZipFile(sys.argv[1])
def read(suffix):
    name = next(n for n in z.namelist() if n.endswith(".dist-info/" + suffix))
    return z.read(name).decode().replace("\r", "").splitlines()
meta, wheel = read("METADATA"), read("WHEEL")
def first(lines, key):
    return next((l[len(key):] for l in lines if l.startswith(key)), "")
print(json.dumps({
    "name": first(meta, "Name: "),
    "version": first(meta, "Version: "),
    "requires": [l[len("Requires-Dist: "):] for l in meta if l.startswith("Requires-Dist: ")],
    "tag": first(wheel, "Tag: "),
    "scripts": sorted(n.rsplit("/", 1)[1] for n in z.namelist()
                      if ".data/scripts/" in n and not n.endswith("/")),
}))"#;

/// What [`WHEEL_INFO_PY`] reports about one wheel.
#[derive(Debug, serde::Deserialize)]
pub struct WheelInfo {
    /// Metadata `Name`.
    pub name: String,
    /// Metadata `Version`.
    pub version: String,
    /// Metadata `Requires-Dist` values.
    pub requires: Vec<String>,
    /// First platform `Tag` of the wheel.
    pub tag: String,
    /// File names under `.data/scripts/`.
    pub scripts: Vec<String>,
}

/// Inputs of a wheel smoke.
#[derive(Debug, Clone)]
pub struct SmokeOptions {
    /// Workspace root.
    pub root: PathBuf,
    /// Directory holding exactly the wheel set.
    pub dir: PathBuf,
    /// Version every tool must report; `None` skips the version check.
    pub want: Option<String>,
    /// `WHEEL_COMPAT=off`: skip the manylinux tag check.
    pub compat_off: bool,
    /// OS this process runs on.
    pub host: HostOs,
}

fn fail<T>(msg: String) -> Result<T, WheelError> {
    tracing::error!(%msg, "smoke assertion failed");
    Err(WheelError::Smoke(msg))
}

/// `uv venv -q <venv>`.
///
/// # Errors
/// [`WheelError::Path`] when a path is not valid UTF-8.
pub fn venv_spec(venv: &Path, cwd: &Path) -> Result<Spec, WheelError> {
    Ok(tool(
        "uv",
        vec!["venv".into(), "-q".into(), path_arg(venv)?],
        cwd,
        STEP_TIMEOUT,
    ))
}

/// The local-only index arguments: `--no-index --find-links <dir>`.
///
/// # Errors
/// [`WheelError::Path`] when a path is not valid UTF-8.
pub fn local_index_args(dir: &Path) -> Result<Vec<String>, WheelError> {
    Ok(vec![
        "--no-index".into(),
        "--find-links".into(),
        path_arg(dir)?,
    ])
}

/// `uv pip install -q --python <python> --no-index --find-links <dir> <name>`.
///
/// # Errors
/// [`WheelError::Path`] when a path is not valid UTF-8.
pub fn install_spec(python: &Path, dir: &Path, name: &str, cwd: &Path) -> Result<Spec, WheelError> {
    let mut args = vec![
        "pip".to_owned(),
        "install".into(),
        "-q".into(),
        "--python".into(),
        path_arg(python)?,
    ];
    args.extend(local_index_args(dir)?);
    args.push(name.to_owned());
    Ok(tool("uv", args, cwd, STEP_TIMEOUT))
}

/// `uv tool install -q --no-index --find-links <dir> <name>` with the tool and bin dirs set.
///
/// # Errors
/// [`WheelError::Path`] when a path is not valid UTF-8.
pub fn tool_install_spec(
    dir: &Path,
    name: &str,
    tool_dir: &Path,
    bin_dir: &Path,
    cwd: &Path,
) -> Result<Spec, WheelError> {
    let mut args = vec!["tool".to_owned(), "install".into(), "-q".into()];
    args.extend(local_index_args(dir)?);
    args.push(name.to_owned());
    let mut spec = tool("uv", args, cwd, STEP_TIMEOUT);
    spec.env = vec![
        ("UV_TOOL_DIR".to_owned(), path_arg(tool_dir)?),
        ("UV_TOOL_BIN_DIR".to_owned(), path_arg(bin_dir)?),
    ];
    Ok(spec)
}

/// `sh packaging/smoke/fixture-loop.sh <bin_dir> [version]`, run from the workspace root.
///
/// # Errors
/// [`WheelError::Path`] when a path is not valid UTF-8.
pub fn fixture_loop_spec(
    root: &Path,
    bin_dir: &Path,
    want: Option<&str>,
) -> Result<Spec, WheelError> {
    let mut args = vec![FIXTURE_LOOP.to_owned(), path_arg(bin_dir)?];
    args.extend(want.map(str::to_owned));
    Ok(tool("sh", args, root, STEP_TIMEOUT))
}

fn captured(mut spec: Spec) -> Spec {
    spec.capture = true;
    spec
}

/// The names `uv pip freeze` lists for the venv at `venv`, sorted.
fn installed(opts: &SmokeOptions, venv: &Path) -> Result<Vec<String>, WheelError> {
    let python = opts.host.venv_exe(venv, "python");
    let spec = captured(tool(
        "uv",
        vec![
            "pip".into(),
            "freeze".into(),
            "--python".into(),
            path_arg(&python)?,
        ],
        &opts.root,
        STEP_TIMEOUT,
    ));
    let mut names: Vec<String> = run_ok("uv pip freeze", &spec)?
        .lines()
        .filter_map(|l| l.split_once("==").map(|(n, _)| n.trim().to_owned()))
        .collect();
    names.sort();
    Ok(names)
}

/// Run `<venv>/<bin>/<name> --version` and compare it with `<name> <want>` when `want` is set.
fn version_of(opts: &SmokeOptions, bin: &Path, name: &str) -> Result<String, WheelError> {
    let spec = captured(exe(bin, vec!["--version".into()], &opts.root, STEP_TIMEOUT));
    let got = run_ok(&format!("{name} --version"), &spec)?
        .trim()
        .to_owned();
    emit(&got);
    if let Some(want) = &opts.want
        && got != format!("{name} {want}")
    {
        return fail(format!("expected '{name} {want}', got '{got}'"));
    }
    Ok(got)
}

/// The single wheel of `name` in the wheel directory.
fn one_wheel(opts: &SmokeOptions, name: &str) -> Result<PathBuf, WheelError> {
    let mut found = wheels_of(&opts.dir, name)?;
    if found.len() != 1 {
        return fail(format!(
            "expected exactly one {name} wheel in {}, found: {found:?}",
            opts.dir.display()
        ));
    }
    Ok(found.remove(0))
}

fn wheel_info(
    opts: &SmokeOptions,
    reader_python: &Path,
    wheel: &Path,
) -> Result<WheelInfo, WheelError> {
    let spec = captured(exe(
        reader_python,
        vec!["-c".into(), WHEEL_INFO_PY.into(), path_arg(wheel)?],
        &opts.root,
        STEP_TIMEOUT,
    ));
    let text = run_ok("reading wheel metadata", &spec)?;
    serde_json::from_str(text.trim())
        .map_err(|e| WheelError::Smoke(format!("{}: unreadable wheel info: {e}", wheel.display())))
}

/// Metadata checks of every wheel: name, platform tag, only its own binary, dependency pins.
fn check_metadata(
    opts: &SmokeOptions,
    reader_python: &Path,
    products: &[Product],
) -> Result<(), WheelError> {
    for product in products {
        let wheel = one_wheel(opts, &product.name)?;
        let info = wheel_info(opts, reader_python, &wheel)?;
        emit(&format!(
            "smoke: wheel {} tag={}",
            wheel.display(),
            info.tag
        ));
        if info.name != product.name {
            return fail(format!(
                "{}: metadata name is not {}",
                wheel.display(),
                product.name
            ));
        }
        if opts.host == HostOs::Linux && !opts.compat_off && !info.tag.contains("manylinux_2_28") {
            return fail(format!(
                "{}: linux tag is not manylinux_2_28 ({})",
                wheel.display(),
                info.tag
            ));
        }
        let mut scripts: Vec<String> = info
            .scripts
            .iter()
            .map(|s| s.strip_suffix(".exe").unwrap_or(s).to_owned())
            .collect();
        scripts.sort();
        if scripts != [product.name.clone()] {
            return fail(format!(
                "{} carries {scripts:?}, expected only {}",
                wheel.display(),
                product.name
            ));
        }
        for dep in &product.depends {
            let pin = format!("{dep}=={}", info.version);
            if !info.requires.contains(&pin) {
                return fail(format!("{} wheel does not require {pin}", product.name));
            }
        }
    }
    Ok(())
}

/// Whether executable `name` is on the `PATH` value `path`.
pub fn on_path(host: HostOs, path: &std::ffi::OsStr, name: &str) -> Option<PathBuf> {
    std::env::split_paths(path)
        .map(|d| d.join(format!("{name}{}", host.exe_suffix())))
        .find(|p| p.is_file())
}

/// Scenario: install product `name` alone into a fresh venv and check what it brought.
fn scenario_venv(
    opts: &SmokeOptions,
    work: &Path,
    products: &[Product],
    p: &Product,
) -> Result<(), WheelError> {
    let venv = work.join(&p.name);
    run_ok("uv venv", &venv_spec(&venv, &opts.root)?)?;
    let python = opts.host.venv_exe(&venv, "python");
    run_ok(
        &format!("installing {}", p.name),
        &install_spec(&python, &opts.dir, &p.name, &opts.root)?,
    )?;
    let mut expect: Vec<String> = std::iter::once(p.name.clone())
        .chain(p.depends.iter().cloned())
        .collect();
    expect.sort();
    let got = installed(opts, &venv)?;
    if got != expect {
        return fail(format!(
            "{}: expected {expect:?} installed, got {got:?}",
            p.name
        ));
    }
    for other in products.iter().filter(|o| !expect.contains(&o.name)) {
        if opts.host.venv_exe(&venv, &other.name).exists() {
            return fail(format!("{} alone installed {}", p.name, other.name));
        }
    }
    let own = version_of(opts, &opts.host.venv_exe(&venv, &p.name), &p.name)?;
    for dep in &p.depends {
        let dep_got = version_of(opts, &opts.host.venv_exe(&venv, dep), dep)?;
        if dep_got.strip_prefix(&format!("{dep} ")) != own.strip_prefix(&format!("{} ", p.name)) {
            return fail(format!(
                "{}: {dep} version differs: '{dep_got}' vs '{own}'",
                p.name
            ));
        }
    }
    if p.name == FROB {
        run_ok(
            "fixture loop",
            &fixture_loop_spec(
                &opts.root,
                &venv.join(opts.host.venv_bin()),
                opts.want.as_deref(),
            )?,
        )?;
    }
    emit(&format!("smoke: {} ok: installed {expect:?}", p.name));
    Ok(())
}

/// Scenario: `uv tool install frob` exposes only frob, which finds grimble beside itself.
fn scenario_tool_install(
    opts: &SmokeOptions,
    work: &Path,
    products: &[Product],
) -> Result<(), WheelError> {
    let (tool_dir, bin_dir, repo) = (
        work.join("c/tools"),
        work.join("c/bin"),
        work.join("c/repo"),
    );
    run_ok(
        "uv tool install frob",
        &tool_install_spec(&opts.dir, FROB, &tool_dir, &bin_dir, &opts.root)?,
    )?;
    let exe_of = |name: &str| bin_dir.join(format!("{name}{}", opts.host.exe_suffix()));
    if !exe_of(FROB).exists() {
        return fail("c: uv tool install exposed no frob".to_owned());
    }
    for other in products.iter().filter(|p| p.name != FROB) {
        if exe_of(&other.name).exists() {
            return fail(format!(
                "c: {} is exposed on PATH by the tool install",
                other.name
            ));
        }
    }
    let rest = std::env::var_os("PATH").unwrap_or_default();
    let path =
        std::env::join_paths(std::iter::once(bin_dir.clone()).chain(std::env::split_paths(&rest)))
            .map_err(|e| WheelError::Smoke(format!("c: cannot extend PATH: {e}")))?;
    if let Some(found) = on_path(opts.host, &path, "grimble") {
        return fail(format!(
            "c: a grimble is already on PATH ({}); the scenario needs none",
            found.display()
        ));
    }
    std::fs::create_dir_all(&repo).map_err(|e| WheelError::Io {
        what: format!("creating {}", repo.display()),
        reason: e.to_string(),
    })?;
    let path_env = path
        .to_str()
        .map(str::to_owned)
        .ok_or_else(|| WheelError::Path(PathBuf::from(&path)))?;
    let git = |args: &[&str]| {
        run_ok(
            "git",
            &tool(
                "git",
                args.iter().map(|s| (*s).to_owned()).collect(),
                &repo,
                STEP_TIMEOUT,
            ),
        )
    };
    git(&["init", "-q"])?;
    git(&["symbolic-ref", "HEAD", "refs/heads/main"])?;
    let frob = |args: &[&str]| -> Result<String, WheelError> {
        let mut spec = captured(exe(
            &exe_of(FROB),
            args.iter().map(|s| (*s).to_owned()).collect(),
            &repo,
            STEP_TIMEOUT,
        ));
        spec.env = vec![("PATH".to_owned(), path_env.clone())];
        run_ok(&format!("frob {}", args.join(" ")), &spec)
    };
    let doctor = frob(&["--json", "doctor"])?;
    let beside =
        doctor.contains(r#""location":"beside-frob""#) && doctor.contains(r#""product":"grimble""#);
    if !beside {
        return fail(format!(
            "c: frob doctor did not find grimble beside frob: {doctor}"
        ));
    }
    if !doctor.contains(r#""product":"grimble","version":"grimble "#) {
        return fail("c: frob doctor could not run the grimble it found".to_owned());
    }
    frob(&["--json", "init"])?;
    let checked = frob(&["--json", "check"])?;
    if !checked.contains(r#""ok":true"#) {
        return fail(format!("c: frob check failed: {checked}"));
    }
    emit("smoke: c ok: uv tool install frob finds grimble without it on PATH");
    Ok(())
}

/// Smoke the wheel set described by `opts`.
///
/// # Errors
/// [`WheelError::Smoke`] for a failed assertion; other variants for a step that cannot run.
pub fn smoke(opts: &SmokeOptions) -> Result<(), WheelError> {
    let products = read_products(&opts.root)?;
    let work = tempfile::tempdir().map_err(|e| WheelError::Io {
        what: "creating the smoke work directory".to_owned(),
        reason: e.to_string(),
    })?;
    let reader = work.path().join("reader");
    run_ok("uv venv", &venv_spec(&reader, &opts.root)?)?;
    check_metadata(opts, &opts.host.venv_exe(&reader, "python"), &products)?;
    for p in &products {
        scenario_venv(opts, work.path(), &products, p)?;
    }
    scenario_tool_install(opts, work.path(), &products)?;
    emit("smoke: ok");
    Ok(())
}

/// Resolve CLI inputs into [`SmokeOptions`] and run [`smoke`].
///
/// # Errors
/// Any [`WheelError`] from [`smoke`], or [`WheelError::Io`] when `dir` cannot be made absolute.
pub fn smoke_from_env(root: &Path, dir: &Path, want: Option<String>) -> Result<(), WheelError> {
    let dir = std::path::absolute(dir).map_err(|e| WheelError::Io {
        what: format!("resolving {}", dir.display()),
        reason: e.to_string(),
    })?;
    smoke(&SmokeOptions {
        root: root.to_path_buf(),
        dir,
        want,
        compat_off: std::env::var(crate::wheel::COMPAT_ENV).is_ok_and(|v| v == "off"),
        host: HostOs::current(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-dev/src/wheel_smoke.rs::install_spec
    #[test]
    fn installs_use_the_local_wheels_only_for_each_venv_layout() {
        for host in [HostOs::Linux, HostOs::Macos, HostOs::Windows] {
            let venv = Path::new("w").join("a");
            let python = host.venv_exe(&venv, "python");
            let spec =
                install_spec(&python, Path::new("wheels"), "grimble", Path::new(".")).unwrap();
            let args: Vec<&str> = spec.args.iter().map(String::as_str).collect();
            assert_eq!(&args[..4], ["pip", "install", "-q", "--python"]);
            assert_eq!(args[4], python.to_str().unwrap());
            assert_eq!(
                &args[5..],
                ["--no-index", "--find-links", "wheels", "grimble"]
            );
        }
    }

    // frob:tests crates/gob-dev/src/wheel_smoke.rs::tool_install_spec
    #[test]
    fn tool_install_sets_isolated_tool_and_bin_dirs() {
        let spec = tool_install_spec(
            Path::new("wh"),
            "frob",
            Path::new("t"),
            Path::new("b"),
            Path::new("."),
        )
        .unwrap();
        assert_eq!(
            spec.args,
            [
                "tool",
                "install",
                "-q",
                "--no-index",
                "--find-links",
                "wh",
                "frob"
            ]
        );
        assert_eq!(
            spec.env,
            [
                ("UV_TOOL_DIR".to_owned(), "t".to_owned()),
                ("UV_TOOL_BIN_DIR".to_owned(), "b".to_owned())
            ]
        );
    }

    // frob:tests crates/gob-dev/src/wheel_smoke.rs::fixture_loop_spec
    #[test]
    fn fixture_loop_gets_a_forward_slash_script_path_and_the_bin_dir() {
        let spec = fixture_loop_spec(Path::new("/r"), Path::new("/v/bin"), Some("1.2.3")).unwrap();
        assert_eq!(
            spec.args,
            ["packaging/smoke/fixture-loop.sh", "/v/bin", "1.2.3"]
        );
        assert_eq!(spec.cwd.as_deref(), Some(Path::new("/r")));
        let none = fixture_loop_spec(Path::new("/r"), Path::new("/v/bin"), None).unwrap();
        assert_eq!(none.args.len(), 2);
    }

    // frob:tests crates/gob-dev/src/wheel_smoke.rs::on_path
    #[test]
    fn on_path_finds_executables_with_the_host_suffix() {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("grimble.exe"), "").unwrap();
        let path = std::env::join_paths([dir.path()]).unwrap();
        assert!(on_path(HostOs::Windows, &path, "grimble").is_some());
        assert!(on_path(HostOs::Linux, &path, "grimble").is_none());
    }

    // frob:tests crates/gob-dev/src/wheel_smoke.rs::check_metadata
    #[test]
    fn wheel_info_script_is_valid_json_producer() {
        assert!(WHEEL_INFO_PY.contains("json.dumps"));
        let info: WheelInfo = serde_json::from_str(
            r#"{"name":"frob","version":"1.0.0","requires":["grimble==1.0.0"],"tag":"py3-none-any","scripts":["frob.exe"]}"#,
        )
        .unwrap();
        assert_eq!(info.requires, ["grimble==1.0.0"]);
    }
}
