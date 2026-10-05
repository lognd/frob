//! `cargo dev wheel`: build the `PyPI` wheel of every product for this host, portably.
//!
//! One wheel per product of `packaging/pypi/products.toml` (D87), each carrying only its own
//! binary. `render.py` writes each product's maturin project under `<target>/pypi/<product>` and
//! maturin (pinned with hashes in `maturin-requirements.txt`, installed by uv into
//! `<target>/maturin-venv`) builds it. Every spawn goes through `gob-exec` as an argv of
//! `Path`-built values, so nothing depends on a POSIX shell or GNU userland (D86): the venv
//! layout (`Scripts\python.exe` versus `bin/python`) and the manylinux tag are decided here from
//! the host or the `--target` triple. [`plan`] is the pure argv construction; [`build`] runs it.
//! Never publishes. Replaces `packaging/pypi/build-wheel.sh` (ticket 1T8TCTA).
// frob:ticket 01M450VBPVEBZQZ5ANM1T8TCTA

use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};
use serde::Deserialize;

use crate::out::emit;

/// Wall-clock limit for one wheel build (a cold release build is the longest step).
const BUILD_TIMEOUT: Duration = Duration::from_mins(60);
/// Wall-clock limit for the environment and render steps.
const SETUP_TIMEOUT: Duration = Duration::from_mins(10);
/// Manylinux platform tag asked of maturin on Linux unless `WHEEL_COMPAT` overrides it.
pub const DEFAULT_COMPAT: &str = "manylinux_2_28";
/// Environment variable overriding the manylinux tag; `off` lets the host decide.
pub const COMPAT_ENV: &str = "WHEEL_COMPAT";
/// Directory of the packaging inputs, relative to the workspace root.
pub const PYPI_DIR: &str = "packaging/pypi";

/// Operating system a wheel is built or smoked for.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HostOs {
    /// Linux (manylinux wheels).
    Linux,
    /// macOS.
    Macos,
    /// Windows.
    Windows,
}

impl HostOs {
    /// The OS this process runs on.
    pub fn current() -> Self {
        if cfg!(windows) {
            Self::Windows
        } else if cfg!(target_os = "macos") {
            Self::Macos
        } else {
            Self::Linux
        }
    }

    /// The OS a Rust target triple names, `None` when it names none of the three.
    pub fn from_triple(triple: &str) -> Option<Self> {
        if triple.contains("linux") {
            Some(Self::Linux)
        } else if triple.contains("apple-darwin") {
            Some(Self::Macos)
        } else if triple.contains("windows") {
            Some(Self::Windows)
        } else {
            None
        }
    }

    /// Directory of a venv holding its executables: `Scripts` on Windows, `bin` elsewhere.
    pub fn venv_bin(self) -> &'static str {
        if self == Self::Windows {
            "Scripts"
        } else {
            "bin"
        }
    }

    /// Executable suffix: `.exe` on Windows, empty elsewhere.
    pub fn exe_suffix(self) -> &'static str {
        if self == Self::Windows { ".exe" } else { "" }
    }

    /// Path of executable `name` inside the venv at `venv`.
    pub fn venv_exe(self, venv: &Path, name: &str) -> PathBuf {
        venv.join(self.venv_bin())
            .join(format!("{name}{}", self.exe_suffix()))
    }
}

/// Why a wheel build or smoke could not complete.
#[derive(Debug, thiserror::Error)]
pub enum WheelError {
    /// `products.toml` is unreadable or malformed.
    #[error("{}: {reason}", path.display())]
    Products {
        /// The file.
        path: PathBuf,
        /// What went wrong.
        reason: String,
    },
    /// `--product` named a product that is not in `products.toml`.
    #[error("unknown product {name:?}; known products: {known}")]
    UnknownProduct {
        /// Requested name.
        name: String,
        /// Comma-separated valid names.
        known: String,
    },
    /// A path cannot be passed as an argument because it is not valid UTF-8.
    #[error("path is not valid UTF-8: {}", .0.display())]
    Path(PathBuf),
    /// A process could not be started, or ended abnormally.
    #[error("{0}")]
    Exec(String),
    /// A filesystem operation failed.
    #[error("{what}: {reason}")]
    Io {
        /// What was being done.
        what: String,
        /// The OS error.
        reason: String,
    },
    /// A smoke assertion failed.
    #[error("smoke: FAIL: {0}")]
    Smoke(String),
}

/// One product of `products.toml`.
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct Product {
    /// `PyPI` project, wheel name and binary.
    pub name: String,
    /// Sibling products pinned at the same version.
    #[serde(default)]
    pub depends: Vec<String>,
}

#[derive(Deserialize)]
struct ProductsFile {
    product: Vec<Product>,
}

/// Parse the text of `products.toml` into its products, in file order.
///
/// # Errors
/// [`WheelError::Products`] when the text is not the expected TOML.
pub fn parse_products(path: &Path, text: &str) -> Result<Vec<Product>, WheelError> {
    toml::from_str::<ProductsFile>(text)
        .map(|f| f.product)
        .map_err(|e| WheelError::Products {
            path: path.to_path_buf(),
            reason: e.to_string(),
        })
}

/// Read the products of `<root>/packaging/pypi/products.toml`.
///
/// # Errors
/// [`WheelError::Products`] when the file is unreadable or malformed.
pub fn read_products(root: &Path) -> Result<Vec<Product>, WheelError> {
    let path = root.join(PYPI_DIR).join("products.toml");
    let text = std::fs::read_to_string(&path).map_err(|e| WheelError::Products {
        path: path.clone(),
        reason: e.to_string(),
    })?;
    parse_products(&path, &text)
}

/// A path as an argument string.
///
/// # Errors
/// [`WheelError::Path`] when the path is not valid UTF-8 (`gob-exec` argv are strings).
pub fn path_arg(path: &Path) -> Result<String, WheelError> {
    path.to_str()
        .map(str::to_owned)
        .ok_or_else(|| WheelError::Path(path.to_path_buf()))
}

fn strings(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| (*s).to_owned()).collect()
}

/// Spec of a program found on `PATH`, run in `cwd`, output inherited.
pub fn tool(name: &str, args: Vec<String>, cwd: &Path, timeout: Duration) -> Spec {
    Spec {
        program: Program::Tool {
            name: name.to_owned(),
        },
        args,
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout,
        capture: false,
    }
}

/// Spec of the executable at `path` (a venv tool), run in `cwd`, output inherited.
pub fn exe(path: &Path, args: Vec<String>, cwd: &Path, timeout: Duration) -> Spec {
    Spec {
        program: Program::Hook {
            path: path.to_path_buf(),
        },
        args,
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout,
        capture: false,
    }
}

/// Run `spec`, requiring exit 0; returns the captured stdout (empty unless `spec.capture`).
///
/// # Errors
/// [`WheelError::Exec`] when the process cannot run or exits non-zero.
pub fn run_ok(what: &str, spec: &Spec) -> Result<String, WheelError> {
    tracing::info!(what, program = %spec.program.label(), args = ?spec.args, "spawning");
    let out = Runner::new(Limits { jobs: 1 })
        .run(spec)
        .map_err(|e| WheelError::Exec(format!("{what}: {e}")))?;
    match out.status {
        Outcome::Exited(0) => Ok(out.stdout),
        other => {
            tracing::error!(what, ?other, stderr = %out.stderr, "step failed");
            Err(WheelError::Exec(format!(
                "{what}: ended {other:?}{}",
                if out.stderr.is_empty() {
                    String::new()
                } else {
                    format!(": {}", out.stderr.trim())
                }
            )))
        }
    }
}

/// Inputs of a wheel build, resolved to absolute paths.
#[derive(Debug, Clone)]
pub struct BuildOptions {
    /// Workspace root (holds `packaging/pypi`).
    pub root: PathBuf,
    /// Cargo target directory (`CARGO_TARGET_DIR`, default `<root>/target`).
    pub target_dir: PathBuf,
    /// Directory the wheels are written to.
    pub out: PathBuf,
    /// Rust target triple for a cross build; `None` builds for the host.
    pub triple: Option<String>,
    /// Products to build, in order; empty builds every product of `products.toml`.
    pub products: Vec<String>,
    /// Value of `WHEEL_COMPAT` (`off` lets the host decide); `None` when unset.
    pub compat: Option<String>,
    /// OS this process runs on (decides the venv layout).
    pub host: HostOs,
}

/// One planned process: a label, a directory to empty first, and the spawn.
#[derive(Debug, Clone)]
pub struct Planned {
    /// Human label printed before the step runs.
    pub label: String,
    /// Directory removed before the step runs.
    pub clean: Option<PathBuf>,
    /// The process to run.
    pub spec: Spec,
}

/// The `--compatibility` value to give maturin, `None` to let the host decide.
///
/// Linux wheels ask for [`DEFAULT_COMPAT`] unless `WHEEL_COMPAT` says otherwise; other OSes
/// never pass the flag. The OS is the target triple's when given, else the host's.
pub fn compatibility(opts: &BuildOptions) -> Option<String> {
    let os = opts
        .triple
        .as_deref()
        .and_then(HostOs::from_triple)
        .unwrap_or(opts.host);
    if os != HostOs::Linux {
        return None;
    }
    match opts.compat.as_deref() {
        Some("off") => None,
        Some(value) => Some(value.to_owned()),
        None => Some(DEFAULT_COMPAT.to_owned()),
    }
}

/// The ordered processes that build the wheels of the selected products.
///
/// # Errors
/// [`WheelError::UnknownProduct`] for a name not in `products`; [`WheelError::Path`] for a
/// non-UTF-8 path.
pub fn plan(opts: &BuildOptions, products: &[Product]) -> Result<Vec<Planned>, WheelError> {
    let selected: Vec<&str> = if opts.products.is_empty() {
        products.iter().map(|p| p.name.as_str()).collect()
    } else {
        for name in &opts.products {
            if !products.iter().any(|p| &p.name == name) {
                return Err(WheelError::UnknownProduct {
                    name: name.clone(),
                    known: products
                        .iter()
                        .map(|p| p.name.as_str())
                        .collect::<Vec<_>>()
                        .join(", "),
                });
            }
        }
        opts.products.iter().map(String::as_str).collect()
    };
    let pypi = opts.root.join(PYPI_DIR);
    let venv = opts.target_dir.join("maturin-venv");
    let python = opts.host.venv_exe(&venv, "python");
    let maturin = opts.host.venv_exe(&venv, "maturin");
    let compat = compatibility(opts);
    let mut steps = vec![
        Planned {
            label: format!("maturin environment in {}", venv.display()),
            clean: None,
            spec: tool(
                "uv",
                vec![
                    "venv".into(),
                    "-q".into(),
                    "--clear".into(),
                    "--python".into(),
                    ">=3.11".into(),
                    path_arg(&venv)?,
                ],
                &opts.root,
                SETUP_TIMEOUT,
            ),
        },
        Planned {
            label: "installing the pinned maturin".to_owned(),
            clean: None,
            spec: tool(
                "uv",
                vec![
                    "pip".into(),
                    "install".into(),
                    "-q".into(),
                    "--require-hashes".into(),
                    "--no-deps".into(),
                    "--python".into(),
                    path_arg(&python)?,
                    "-r".into(),
                    path_arg(&pypi.join("maturin-requirements.txt"))?,
                ],
                &opts.root,
                SETUP_TIMEOUT,
            ),
        },
        Planned {
            label: "maturin version".to_owned(),
            clean: None,
            spec: exe(&maturin, strings(&["--version"]), &opts.root, SETUP_TIMEOUT),
        },
    ];
    for name in selected {
        let project = opts.target_dir.join("pypi").join(name);
        steps.push(Planned {
            label: format!("{name}: rendering {}", project.display()),
            clean: Some(project.clone()),
            spec: exe(
                &python,
                vec![
                    path_arg(&pypi.join("render.py"))?,
                    "render".into(),
                    name.to_owned(),
                    path_arg(&project)?,
                ],
                &opts.root,
                SETUP_TIMEOUT,
            ),
        });
        let mut args = strings(&["build", "--release", "--locked", "--out"]);
        args.push(path_arg(&opts.out)?);
        if let Some(c) = &compat {
            args.extend(["--compatibility".to_owned(), c.clone()]);
        }
        if let Some(t) = &opts.triple {
            args.extend(["--target".to_owned(), t.clone()]);
        }
        args.extend(["--target-dir".to_owned(), path_arg(&opts.target_dir)?]);
        steps.push(Planned {
            label: format!("{name}: building the wheel into {}", opts.out.display()),
            clean: None,
            spec: exe(&maturin, args, &project, BUILD_TIMEOUT),
        });
    }
    Ok(steps)
}

/// The wheel files of product `name` (`<name>-*.whl`) in `dir`, sorted.
///
/// # Errors
/// [`WheelError::Io`] when `dir` cannot be listed.
pub fn wheels_of(dir: &Path, name: &str) -> Result<Vec<PathBuf>, WheelError> {
    let prefix = format!("{name}-");
    let entries = std::fs::read_dir(dir).map_err(|e| WheelError::Io {
        what: format!("listing {}", dir.display()),
        reason: e.to_string(),
    })?;
    let mut found: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|e| e.path())
        .filter(|p| {
            p.is_file()
                && p.file_name().and_then(|n| n.to_str()).is_some_and(|n| {
                    n.starts_with(&prefix)
                        && Path::new(n)
                            .extension()
                            .is_some_and(|x| x.eq_ignore_ascii_case("whl"))
                })
        })
        .collect();
    found.sort();
    Ok(found)
}

/// Build the wheels described by `opts`, printing progress; nothing is published.
///
/// # Errors
/// Any [`WheelError`]: a bad product name, a failed step, or a product with no wheel after
/// its build.
pub fn build(opts: &BuildOptions) -> Result<(), WheelError> {
    let products = read_products(&opts.root)?;
    let steps = plan(opts, &products)?;
    std::fs::create_dir_all(&opts.out).map_err(|e| WheelError::Io {
        what: format!("creating {}", opts.out.display()),
        reason: e.to_string(),
    })?;
    for step in &steps {
        emit(&format!("wheel: {}", step.label));
        if let Some(dir) = &step.clean
            && dir.exists()
        {
            tracing::info!(dir = %dir.display(), "removing the stale rendered project");
            std::fs::remove_dir_all(dir).map_err(|e| WheelError::Io {
                what: format!("removing {}", dir.display()),
                reason: e.to_string(),
            })?;
        }
        run_ok(&step.label, &step.spec)?;
    }
    let built: Vec<String> = if opts.products.is_empty() {
        products.into_iter().map(|p| p.name).collect()
    } else {
        opts.products.clone()
    };
    for name in built {
        let found = wheels_of(&opts.out, &name)?;
        if found.is_empty() {
            return Err(WheelError::Exec(format!(
                "{name}: maturin produced no wheel in {}",
                opts.out.display()
            )));
        }
        for wheel in found {
            emit(&wheel.display().to_string());
        }
    }
    Ok(())
}

/// Resolve CLI inputs into [`BuildOptions`] and run [`build`].
///
/// `out` defaults to `<root>/target/wheels`; a relative `out` or `CARGO_TARGET_DIR` is made
/// absolute against the current directory (no `realpath -m`: `std::path::absolute`).
///
/// # Errors
/// Any [`WheelError`] from [`build`], or [`WheelError::Io`] when a path cannot be made absolute.
pub fn build_from_env(
    root: &Path,
    out: Option<&Path>,
    triple: Option<String>,
    products: Vec<String>,
) -> Result<(), WheelError> {
    let absolute = |p: &Path| {
        std::path::absolute(p).map_err(|e| WheelError::Io {
            what: format!("resolving {}", p.display()),
            reason: e.to_string(),
        })
    };
    let target_dir = match std::env::var_os("CARGO_TARGET_DIR") {
        Some(dir) => absolute(Path::new(&dir))?,
        None => root.join("target"),
    };
    let out = match out {
        Some(dir) => absolute(dir)?,
        None => root.join("target").join("wheels"),
    };
    build(&BuildOptions {
        root: root.to_path_buf(),
        target_dir,
        out,
        triple,
        products,
        compat: std::env::var(COMPAT_ENV).ok(),
        host: HostOs::current(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const TRIPLES: [&str; 5] = [
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "x86_64-apple-darwin",
        "aarch64-apple-darwin",
        "x86_64-pc-windows-msvc",
    ];

    fn products() -> Vec<Product> {
        parse_products(
            Path::new("products.toml"),
            "[[product]]\nname = \"frob\"\ndepends = [\"grimble\"]\n[[product]]\nname = \"grimble\"\n",
        )
        .unwrap()
    }

    fn opts(host: HostOs, triple: Option<&str>) -> BuildOptions {
        let (root, target) = if host == HostOs::Windows {
            ("C:/w/repo", "C:/w/repo/target")
        } else {
            ("/w/repo", "/w/repo/target")
        };
        BuildOptions {
            root: PathBuf::from(root),
            target_dir: PathBuf::from(target),
            out: PathBuf::from(target).join("wheels"),
            triple: triple.map(str::to_owned),
            products: Vec::new(),
            compat: None,
            host,
        }
    }

    fn host_of(triple: &str) -> HostOs {
        HostOs::from_triple(triple).unwrap()
    }

    // frob:tests crates/gob-dev/src/wheel.rs::plan
    #[test]
    fn plan_builds_every_product_for_each_of_the_five_targets() {
        for triple in TRIPLES {
            let host = host_of(triple);
            let o = opts(host, Some(triple));
            let steps = plan(&o, &products()).unwrap();
            // venv, install, version, then render + build per product.
            assert_eq!(steps.len(), 3 + 2 * 2, "{triple}");
            let venv = o.target_dir.join("maturin-venv");
            let python = host.venv_exe(&venv, "python");
            assert_eq!(
                steps[0].spec.args.last().unwrap(),
                &path_arg(&venv).unwrap()
            );
            assert!(steps[0].spec.args.contains(&">=3.11".to_owned()));
            assert!(steps[1].spec.args.contains(&path_arg(&python).unwrap()));
            assert!(steps[1].spec.args.contains(&"--require-hashes".to_owned()));
            let build = &steps[4].spec;
            assert_eq!(build.args[0], "build");
            assert!(
                build.args.windows(2).any(|w| w == ["--target", triple]),
                "{triple}"
            );
            assert!(build.args.contains(&"--locked".to_owned()));
            assert_eq!(
                build.cwd.as_deref(),
                Some(o.target_dir.join("pypi/frob").as_path())
            );
            let compat = build.args.windows(2).find(|w| w[0] == "--compatibility");
            if host == HostOs::Linux {
                assert_eq!(
                    compat.map(|w| w[1].as_str()),
                    Some("manylinux_2_28"),
                    "{triple}"
                );
            } else {
                assert!(compat.is_none(), "{triple}");
            }
        }
    }

    // frob:tests crates/gob-dev/src/wheel.rs::HostOs
    #[test]
    fn venv_executables_follow_the_os_layout_never_a_bare_python() {
        let v = Path::new("v");
        assert_eq!(
            HostOs::Windows.venv_exe(v, "python"),
            v.join("Scripts").join("python.exe")
        );
        assert_eq!(
            HostOs::Linux.venv_exe(v, "maturin"),
            v.join("bin").join("maturin")
        );
        assert_eq!(
            HostOs::Macos.venv_exe(v, "maturin"),
            v.join("bin").join("maturin")
        );
        for t in TRIPLES {
            assert!(HostOs::from_triple(t).is_some(), "{t}");
        }
        assert!(HostOs::from_triple("wasm32-unknown-unknown").is_none());
    }

    // frob:tests crates/gob-dev/src/wheel.rs::compatibility
    #[test]
    fn compatibility_defaults_on_linux_and_honours_the_override() {
        let mut o = opts(HostOs::Linux, None);
        assert_eq!(compatibility(&o).as_deref(), Some("manylinux_2_28"));
        o.compat = Some("off".to_owned());
        assert_eq!(compatibility(&o), None);
        o.compat = Some("manylinux_2_34".to_owned());
        assert_eq!(compatibility(&o).as_deref(), Some("manylinux_2_34"));
        // A macOS runner cross-building nothing Linux never passes the flag.
        assert_eq!(compatibility(&opts(HostOs::Macos, None)), None);
        // A Linux host building a macOS target does not ask for manylinux.
        assert_eq!(
            compatibility(&opts(HostOs::Linux, Some("aarch64-apple-darwin"))),
            None
        );
    }

    // frob:tests crates/gob-dev/src/wheel.rs::plan
    #[test]
    fn product_filter_keeps_order_and_rejects_unknown_names() {
        let mut o = opts(HostOs::Linux, None);
        o.products = vec!["grimble".to_owned()];
        let steps = plan(&o, &products()).unwrap();
        assert_eq!(steps.len(), 5);
        assert_eq!(steps[3].spec.args[2], "grimble");
        assert_eq!(
            steps[3].clean.as_deref(),
            Some(o.target_dir.join("pypi/grimble").as_path())
        );
        o.products = vec!["nope".to_owned()];
        let e = plan(&o, &products()).unwrap_err();
        assert!(
            e.to_string().contains("known products: frob, grimble"),
            "{e}"
        );
    }

    // frob:tests crates/gob-dev/src/wheel.rs::read_products
    #[test]
    fn the_real_products_file_lists_frob_grimble_and_crunk() {
        let root = crate::find_workspace_root(&std::env::current_dir().unwrap()).unwrap();
        let names: Vec<String> = read_products(&root)
            .unwrap()
            .into_iter()
            .map(|p| p.name)
            .collect();
        assert_eq!(names, ["frob", "grimble", "crunk"]);
    }
}
