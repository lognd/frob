//! Sibling discovery: next to the running executable first, then on `PATH` (D87).
//!
//! `uv tool install frob` exposes only `frob` on `PATH`; the sibling binaries its
//! dependencies installed sit in the same tool environment, in the directory of the
//! real `frob` executable (`bin/` on Unix, `Scripts\` on Windows). One function,
//! [`find_sibling`], is the discovery for `frob check` and `frob doctor`.
//!
//! The decision is a pure function over candidate directories and an `is_file`
//! probe ([`plan`]), parameterised by [`Platform`], so the Windows rules (the `.exe`
//! suffix, case-insensitive) are tested on any host (`paths.md` section 4). Only
//! [`Origin`] and `Path`/`OsStr` APIs are used: no path is turned into text.
//!
//! On Windows the executable on `PATH` is a copy in the installer's bin directory, not a link
//! into the tool environment, so [`tool_env_dirs`] adds the environment's `Scripts` directory
//! (found from the installers' tool roots, never from `PATH`) to the beside-frob search.
// frob:ticket 01M452Q6THBSZGVHRAYHA1TTRM

use std::ffi::{OsStr, OsString};
use std::path::{Path, PathBuf};

use crate::ExecError;
use crate::program::bare_name;

/// The executable naming rules of a platform.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Platform {
    /// Executables carry no suffix.
    Unix,
    /// Executables carry `.exe`, compared ignoring case.
    Windows,
}

impl Platform {
    /// The platform this binary was built for.
    pub const fn host() -> Self {
        if cfg!(windows) {
            Self::Windows
        } else {
            Self::Unix
        }
    }
}

/// Where a sibling was found.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Origin {
    /// In the directory of the running executable (the same tool environment).
    BesideFrob,
    /// On `PATH`.
    Path,
}

impl Origin {
    /// Stable label for reports: `beside-frob` or `path`.
    pub const fn label(self) -> &'static str {
        match self {
            Self::BesideFrob => "beside-frob",
            Self::Path => "path",
        }
    }
}

/// A discovered sibling: the copy used, where it came from, and a different second copy.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Sibling {
    /// The executable that will run.
    pub path: PathBuf,
    /// Which location supplied it.
    pub origin: Origin,
    /// A second copy in the other location (a different file), for `doctor` to compare.
    pub other: Option<PathBuf>,
}

/// File names `name` may have in a directory on `platform`, best first.
pub fn executable_names(platform: Platform, name: &OsStr) -> Vec<OsString> {
    match platform {
        Platform::Unix => vec![name.to_owned()],
        Platform::Windows => {
            let has_exe = Path::new(name)
                .extension()
                .is_some_and(|e| e.eq_ignore_ascii_case("exe"));
            if has_exe {
                vec![name.to_owned()]
            } else {
                let mut with = name.to_owned();
                with.push(".exe");
                vec![with]
            }
        }
    }
}

/// The first existing candidate for `name` in `dirs`, in order.
fn first_in(
    platform: Platform,
    name: &OsStr,
    dirs: &[PathBuf],
    is_file: &dyn Fn(&Path) -> bool,
) -> Option<PathBuf> {
    let names = executable_names(platform, name);
    dirs.iter()
        .flat_map(|d| names.iter().map(move |n| d.join(n)))
        .find(|p| is_file(p))
}

/// The pure decision: the copy beside the executable and the first one on `PATH`, either may be absent.
pub fn plan(
    platform: Platform,
    name: &OsStr,
    beside_dirs: &[PathBuf],
    path_dirs: &[PathBuf],
    is_file: &dyn Fn(&Path) -> bool,
) -> (Option<PathBuf>, Option<PathBuf>) {
    (
        first_in(platform, name, beside_dirs, is_file),
        first_in(platform, name, path_dirs, is_file),
    )
}

/// Directories to search beside `exe`: its canonical parent (symlinks resolved), then its raw parent when different.
pub fn beside_dirs(exe: &Path) -> Vec<PathBuf> {
    let mut dirs = Vec::new();
    match crate::path::canonical(exe) {
        Ok(real) => dirs.extend(real.parent().map(Path::to_path_buf)),
        Err(e) => tracing::debug!(error = %e, "running executable did not canonicalize"),
    }
    if let Some(raw) = exe.parent().map(Path::to_path_buf)
        && !dirs.contains(&raw)
    {
        dirs.push(raw);
    }
    dirs
}

/// Roots under which Python tool installers keep one virtual environment per tool, on `platform`.
///
/// Windows only: there `uv tool install` and `pipx install` put a copy of the executable in a
/// bin directory that is on `PATH`, so the executable's own directory is not the tool
/// environment and a sibling installed by a dependency is invisible from it (Unix symlinks the
/// executable into the environment, which [`beside_dirs`] resolves). `env` reads one
/// environment variable; the order is the installers' precedence: explicit `UV_TOOL_DIR`, then
/// uv's default data directory, then pipx's.
pub fn tool_env_roots(platform: Platform, env: &dyn Fn(&str) -> Option<OsString>) -> Vec<PathBuf> {
    if platform != Platform::Windows {
        return Vec::new();
    }
    let var = |name: &str| env(name).filter(|v| !v.is_empty()).map(PathBuf::from);
    let mut roots = Vec::new();
    roots.extend(var("UV_TOOL_DIR"));
    roots.extend(var("XDG_DATA_HOME").map(|d| d.join("uv").join("tools")));
    roots.extend(var("APPDATA").map(|d| d.join("uv").join("tools")));
    roots.extend(var("PIPX_LOCAL_VENVS"));
    roots.extend(var("PIPX_HOME").map(|d| d.join("venvs")));
    roots.extend(var("USERPROFILE").map(|d| d.join("pipx").join("venvs")));
    roots.extend(var("LOCALAPPDATA").map(|d| d.join("pipx").join("pipx").join("venvs")));
    roots
}

/// The `Scripts` directories of the tool environments named after `exe`'s file stem.
///
/// A candidate `<root>/<stem>` counts only when it is a virtual environment (holds
/// `pyvenv.cfg`) whose `Scripts` directory holds the tool's own executable, so a stray
/// directory of the same name never becomes a search path. No `PATH` is consulted.
pub fn tool_env_dirs(
    platform: Platform,
    exe: &Path,
    env: &dyn Fn(&str) -> Option<OsString>,
    is_file: &dyn Fn(&Path) -> bool,
) -> Vec<PathBuf> {
    let Some(stem) = exe.file_stem() else {
        return Vec::new();
    };
    let own = executable_names(platform, stem);
    let mut dirs = Vec::new();
    for root in tool_env_roots(platform, env) {
        let venv = root.join(stem);
        let scripts = venv.join("Scripts");
        let is_env = is_file(&venv.join("pyvenv.cfg"));
        if is_env && own.iter().any(|n| is_file(&scripts.join(n))) && !dirs.contains(&scripts) {
            tracing::debug!(env = %venv.display(), "tool environment of the running executable found");
            dirs.push(scripts);
        }
    }
    dirs
}

/// True when `a` and `b` are the same file once symlinks are resolved.
fn same_file(a: &Path, b: &Path) -> bool {
    match (crate::path::canonical(a), crate::path::canonical(b)) {
        (Ok(x), Ok(y)) => x == y,
        _ => a == b,
    }
}

/// Find the sibling binary `name`: beside the running executable first, then on `PATH`.
///
/// # Errors
/// [`ExecError::NotAllowed`] for an empty or path-like name and
/// [`ExecError::NotFound`] when neither location has it.
pub fn find_sibling(name: &str) -> Result<Sibling, ExecError> {
    let bare = bare_name(name)?;
    let exe = std::env::current_exe()
        .inspect_err(|e| tracing::debug!(error = %e, "current_exe unavailable"))
        .ok();
    let mut beside = exe.as_deref().map(beside_dirs).unwrap_or_default();
    if let Some(exe) = exe.as_deref() {
        let dirs = tool_env_dirs(
            Platform::host(),
            exe,
            &|name| std::env::var_os(name),
            &|p| p.is_file(),
        );
        beside.extend(
            dirs.into_iter()
                .filter(|d| !beside.contains(d))
                .collect::<Vec<_>>(),
        );
    }
    let on_path: Vec<PathBuf> = std::env::var_os("PATH")
        .map(|p| std::env::split_paths(&p).collect())
        .unwrap_or_default();
    let (near, far) = plan(
        Platform::host(),
        OsStr::new(bare),
        &beside,
        &on_path,
        &|p| p.is_file(),
    );
    let found = match (near, far) {
        (Some(n), far) => {
            let other = far.filter(|f| !same_file(&n, f));
            Sibling {
                path: n,
                origin: Origin::BesideFrob,
                other,
            }
        }
        (None, Some(f)) => Sibling {
            path: f,
            origin: Origin::Path,
            other: None,
        },
        (None, None) => {
            tracing::info!(sibling = bare, "sibling not found beside frob or on PATH");
            return Err(ExecError::NotFound {
                program: bare.to_owned(),
            });
        }
    };
    tracing::info!(
        sibling = bare,
        origin = found.origin.label(),
        second_copy = found.other.is_some(),
        "sibling found"
    );
    Ok(found)
}
