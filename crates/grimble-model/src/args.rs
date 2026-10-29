//! Typed `may` grant arguments and how an observed call argument is judged against them.
//!
//! A grant such as `may fs.read("config/**")` narrows an atom to the arguments it lists. Each
//! atom that takes arguments has one [`ArgKind`]: a filesystem path pattern, a network host
//! pattern, an environment variable name or a binary name. [`validate`] rejects a grant argument
//! that is malformed for its kind (MDL008) and [`judge`] compares one statically observed call
//! argument with one grant argument. The verdict is three-valued: [`Judgement::Unknown`] means
//! the observed value cannot be compared soundly (a glob metacharacter in a path, a host with no
//! known port against a port-scoped grant), and callers must treat it as unresolved, never clean.
//!
//! [`judge`] compares paths lexically: `.` and empty segments drop, `..` pops a segment, and a
//! path that climbs above its start never matches. It reads nothing from disk, so it cannot see
//! symbolic links. [`judge_resolved`] is the link-aware form: it resolves the observed path (and
//! the literal prefix of an absolute grant) against a root, following every link component by
//! component, and fails closed with a [`ResolveError`] when the path cannot be resolved soundly.
//! Hosts compare case-insensitively on labels; a `*.` prefix matches subdomains
//! only, never the apex.

// frob:ticket 01M5XNNH61Z437EDDB05X9CAQE
// frob:ticket 01M61Y35DTKGERGNVE1SPT1F4A

use std::ffi::OsString;
use std::path::{Component, Path, PathBuf};

/// What an atom's `may` arguments mean.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ArgKind {
    /// A filesystem path glob (`config/**`, `/etc/hosts`).
    Path,
    /// A network host pattern with an optional port (`api.example.com:443`, `*.example.com`).
    Host,
    /// An environment variable name.
    EnvName,
    /// The binary a process spawn runs, as written at the call.
    Binary,
}

impl ArgKind {
    /// A short noun phrase for diagnostics ("a path pattern").
    #[must_use]
    pub fn describe(self) -> &'static str {
        match self {
            ArgKind::Path => "a path pattern",
            ArgKind::Host => "a host pattern",
            ArgKind::EnvName => "an environment variable name",
            ArgKind::Binary => "a binary name",
        }
    }
}

/// The argument kind of a canonical or parent atom name, or `None` when the atom takes no
/// arguments (a grant argument on it is a malformed grant).
#[must_use]
pub fn arg_kind(atom: &str) -> Option<ArgKind> {
    match atom {
        "fs" | "fs.read" | "fs.write" => Some(ArgKind::Path),
        "net" | "net.connect" | "net.listen" => Some(ArgKind::Host),
        "process.env" => Some(ArgKind::EnvName),
        "process.spawn" | "exec" => Some(ArgKind::Binary),
        _ => None,
    }
}

/// Outcome of comparing one observed argument with one grant argument.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Judgement {
    /// The observed argument is inside the grant argument.
    Match,
    /// It provably is not.
    NoMatch,
    /// It cannot be decided statically.
    Unknown,
}

/// Checks one grant argument against its atom's kind; `Err` carries the reason.
///
/// # Errors
/// A message naming what is wrong with `arg` for `kind`.
pub fn validate(kind: ArgKind, arg: &str) -> Result<(), String> {
    if arg.is_empty() {
        return Err("the argument is empty".into());
    }
    if arg.contains('\0') {
        return Err("the argument contains a NUL byte".into());
    }
    match kind {
        ArgKind::Path => validate_path(arg),
        ArgKind::Host => validate_host(arg),
        ArgKind::EnvName => {
            if arg.contains('=') || arg.chars().any(char::is_whitespace) {
                Err("an environment variable name has no `=` or whitespace".into())
            } else {
                Ok(())
            }
        }
        ArgKind::Binary => {
            if arg.chars().any(char::is_whitespace) {
                Err("a binary name has no whitespace; name the program, not a command line".into())
            } else {
                Ok(())
            }
        }
    }
}

/// Compares the observed argument `observed` with the grant argument `grant` of `kind`.
#[must_use]
pub fn judge(kind: ArgKind, grant: &str, observed: &str) -> Judgement {
    let verdict = match kind {
        ArgKind::Path => judge_path(grant, observed),
        ArgKind::Host => judge_host(grant, observed),
        ArgKind::EnvName | ArgKind::Binary => {
            if grant == observed {
                Judgement::Match
            } else {
                Judgement::NoMatch
            }
        }
    };
    tracing::trace!(?kind, grant, observed, ?verdict, "grant argument judged");
    verdict
}

// ---------------------------------------------------------------------------------- paths

/// Most symbolic links followed while resolving one path before it counts as a loop.
const MAX_LINK_HOPS: usize = 40;

/// Why a path could not be resolved against the file system; callers treat it as unresolved.
#[derive(Debug, thiserror::Error)]
pub enum ResolveError {
    /// More than [`MAX_LINK_HOPS`] links were followed, so the path is (or may be) a loop.
    #[error("symbolic link loop while resolving {0:?}")]
    Loop(PathBuf),
    /// The real location is not valid Unicode, so it cannot be compared with a text grant.
    #[error("real location {0:?} is not valid unicode")]
    NotUnicode(PathBuf),
    /// A component could not be inspected (permissions, I/O), so its target is unknown.
    #[error("cannot inspect {path:?}: {source}")]
    Io {
        /// The component that failed.
        path: PathBuf,
        /// The underlying error.
        source: std::io::Error,
    },
}

/// One owned path component awaiting resolution.
enum Tok {
    Root,
    Parent,
    Name(OsString),
}

/// The components of `p` as owned tokens, last first, so a stack pop yields the next one.
fn toks_rev(p: &Path) -> Vec<Tok> {
    let mut v: Vec<Tok> = p
        .components()
        .filter_map(|c| match c {
            Component::RootDir => Some(Tok::Root),
            Component::ParentDir => Some(Tok::Parent),
            Component::Normal(n) => Some(Tok::Name(n.to_owned())),
            Component::CurDir | Component::Prefix(_) => None,
        })
        .collect();
    v.reverse();
    v
}

/// Resolves `path` (relative to `base`, which must already be resolved) through every symbolic
/// link, applying `..` after link expansion; components that do not exist are kept lexically.
///
/// # Errors
/// [`ResolveError::Loop`] past [`MAX_LINK_HOPS`] links; [`ResolveError::Io`] when a component
/// cannot be inspected for any reason other than not existing.
pub fn resolve_real(base: &Path, path: &Path) -> Result<PathBuf, ResolveError> {
    let mut cur = base.to_path_buf();
    let mut todo = toks_rev(path);
    let mut hops = 0usize;
    let mut missing = false;
    while let Some(tok) = todo.pop() {
        match tok {
            Tok::Root => {
                cur = PathBuf::from("/");
                missing = false;
            }
            Tok::Parent => {
                cur.pop();
            }
            Tok::Name(name) => {
                let next = cur.join(&name);
                if missing {
                    cur = next;
                    continue;
                }
                match std::fs::symlink_metadata(&next) {
                    Ok(m) if m.file_type().is_symlink() => {
                        hops += 1;
                        if hops > MAX_LINK_HOPS {
                            tracing::warn!(path = ?path, "symlink loop; failing closed");
                            return Err(ResolveError::Loop(path.to_path_buf()));
                        }
                        let target =
                            std::fs::read_link(&next).map_err(|source| ResolveError::Io {
                                path: next.clone(),
                                source,
                            })?;
                        tracing::debug!(link = ?next, target = ?target, "following symlink");
                        // a relative target resolves from the link's directory, which is `cur`
                        todo.extend(toks_rev(&target));
                    }
                    Ok(_) => cur = next,
                    Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                        missing = true;
                        cur = next;
                    }
                    Err(source) => {
                        return Err(ResolveError::Io { path: next, source });
                    }
                }
            }
        }
    }
    Ok(cur)
}

/// `p` as text, or [`ResolveError::NotUnicode`] so a lossy name can never match a grant.
fn text_of(p: &Path) -> Result<&str, ResolveError> {
    gob_path::exact_text(p).ok_or_else(|| ResolveError::NotUnicode(p.to_path_buf()))
}

/// The grant with its leading glob-free segments resolved through links (absolute grants only;
/// a relative grant is rooted at the resolved root by the caller).
fn resolve_grant(grant: &str) -> Result<String, ResolveError> {
    let segs: Vec<&str> = grant.split('/').collect();
    let lit = segs.iter().take_while(|s| !s.contains(['*', '?'])).count();
    let prefix = segs[..lit].join("/");
    let rest = segs[lit..].join("/");
    let real = resolve_real(
        Path::new("/"),
        Path::new(if prefix.is_empty() { "/" } else { &prefix }),
    )?;
    let mut out = text_of(&real)?.to_owned();
    if !rest.is_empty() {
        if !out.ends_with('/') {
            out.push('/');
        }
        out.push_str(&rest);
    }
    Ok(out)
}

/// Link-aware [`judge`] for a path grant: `observed` and an absolute `grant`'s literal prefix are
/// resolved through symbolic links first. A relative observed path and a relative grant are both
/// taken from `root`. An observed path whose real location leaves `root` never matches a
/// relative grant. Other kinds delegate to [`judge`].
///
/// # Errors
/// A [`ResolveError`] when a link loop or an uninspectable component makes the real location
/// unknowable; callers must treat that as unresolved, never as a match.
pub fn judge_resolved(
    kind: ArgKind,
    grant: &str,
    observed: &str,
    root: &Path,
) -> Result<Judgement, ResolveError> {
    if kind != ArgKind::Path || observed.contains(['*', '?', '[', '{', '}', '$', '~']) {
        return Ok(judge(kind, grant, observed));
    }
    let real_root = resolve_real(Path::new("/"), root)?;
    let real = resolve_real(&real_root, Path::new(observed))?;
    let verdict = if grant.starts_with('/') {
        let g = resolve_grant(grant)?;
        judge_path(&g, text_of(&real)?)
    } else {
        match real.strip_prefix(&real_root) {
            Ok(inside) => judge_path(grant, text_of(inside)?),
            Err(_) => Judgement::NoMatch,
        }
    };
    tracing::trace!(grant, observed, real = ?real, ?verdict, "grant path judged by real location");
    Ok(verdict)
}

/// A lexically normalized path: whether it is absolute and its segments. `climbs` is set when a
/// relative path pops above its start (`../x`).
struct Norm {
    absolute: bool,
    segs: Vec<String>,
    climbs: bool,
}

fn normalize(p: &str) -> Norm {
    let absolute = p.starts_with('/');
    let mut segs: Vec<String> = Vec::new();
    let mut climbs = false;
    for s in p.split('/') {
        match s {
            "" | "." => {}
            ".." => {
                if segs.pop().is_none() && !absolute {
                    climbs = true;
                }
            }
            other => segs.push(other.to_owned()),
        }
    }
    Norm {
        absolute,
        segs,
        climbs,
    }
}

fn validate_path(arg: &str) -> Result<(), String> {
    if arg.split('/').any(|s| s == "..") {
        return Err("a path pattern has no `..` segment; write the normalized path".into());
    }
    if arg.contains(['[', ']', '{', '}']) {
        return Err("a path pattern supports only `*`, `?` and `**`".into());
    }
    if arg.split('/').any(|s| s.contains("**") && s != "**") {
        return Err("`**` must be a whole path segment".into());
    }
    Ok(())
}

/// `*` and `?` within one segment.
fn seg_match(pat: &[char], s: &[char]) -> bool {
    match pat.split_first() {
        None => s.is_empty(),
        Some(('*', rest)) => (0..=s.len()).any(|i| seg_match(rest, &s[i..])),
        Some(('?', rest)) => s.split_first().is_some_and(|(_, t)| seg_match(rest, t)),
        Some((c, rest)) => s
            .split_first()
            .is_some_and(|(d, t)| d == c && seg_match(rest, t)),
    }
}

/// Segment-wise glob where a `**` segment matches zero or more segments.
fn glob_match(pat: &[String], segs: &[String]) -> bool {
    match pat.split_first() {
        None => segs.is_empty(),
        Some((p, rest)) if p == "**" => (0..=segs.len()).any(|i| glob_match(rest, &segs[i..])),
        Some((p, rest)) => segs.split_first().is_some_and(|(s, t)| {
            let pc: Vec<char> = p.chars().collect();
            let sc: Vec<char> = s.chars().collect();
            seg_match(&pc, &sc) && glob_match(rest, t)
        }),
    }
}

fn judge_path(grant: &str, observed: &str) -> Judgement {
    if observed.contains(['*', '?', '[', '{', '}', '$', '~']) {
        return Judgement::Unknown;
    }
    let (g, o) = (normalize(grant), normalize(observed));
    if o.climbs || g.absolute != o.absolute {
        return Judgement::NoMatch;
    }
    if glob_match(&g.segs, &o.segs) {
        Judgement::Match
    } else {
        Judgement::NoMatch
    }
}

// ---------------------------------------------------------------------------------- hosts

/// A host (lowercase, no trailing dot, IPv6 unbracketed) and its port, if stated.
struct HostPort {
    host: String,
    port: Option<u16>,
}

fn split_port(s: &str) -> Option<(String, Option<u16>)> {
    if let Some(rest) = s.strip_prefix('[') {
        let (inner, after) = rest.split_once(']')?;
        let port = match after.strip_prefix(':') {
            Some(p) => Some(p.parse::<u16>().ok()?),
            None if after.is_empty() => None,
            None => return None,
        };
        return Some((inner.to_owned(), port));
    }
    match s.rsplit_once(':') {
        Some((h, p)) if !h.contains(':') => Some((h.to_owned(), Some(p.parse::<u16>().ok()?))),
        // a bare IPv6 address has several colons and no port
        _ => Some((s.to_owned(), None)),
    }
}

fn clean_host(h: &str) -> Option<String> {
    let h = h.trim_end_matches('.').to_ascii_lowercase();
    let ok = !h.is_empty()
        && h.chars()
            .all(|c| c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | ':'));
    ok.then_some(h)
}

fn validate_host(arg: &str) -> Result<(), String> {
    if arg.contains("://") || arg.contains('/') || arg.contains('@') {
        return Err("a host pattern is `host[:port]`, with no scheme, path or user".into());
    }
    if arg.chars().any(char::is_whitespace) {
        return Err("a host pattern has no whitespace".into());
    }
    let Some((host, port)) = split_port(arg) else {
        return Err("the port must be a number in 1..65535".into());
    };
    if port == Some(0) {
        return Err("the port must be a number in 1..65535".into());
    }
    if arg != arg.to_ascii_lowercase() {
        return Err("write the host in lowercase".into());
    }
    let body = host.strip_prefix("*.").unwrap_or(&host);
    if body.contains('*') || body.is_empty() || clean_host(body).is_none() {
        return Err(
            "a host pattern allows a `*.` prefix only, then letters, digits, `-`, `.`".into(),
        );
    }
    Ok(())
}

/// Parses an observed `scheme://user@host:port/path`, `host:port` or `host`.
fn observed_host(s: &str) -> Option<HostPort> {
    if s.contains(['\\', '%', '*', '{', '}']) || s.chars().any(char::is_whitespace) {
        return None;
    }
    let (scheme, rest) = match s.split_once("://") {
        Some((sc, r)) => (Some(sc.to_ascii_lowercase()), r),
        None => (None, s),
    };
    let authority = rest.split(['/', '?', '#']).next().unwrap_or("");
    // the host is what follows the LAST `@`: `https://api.example.com@evil.com/` is evil.com
    let hostport = authority.rsplit_once('@').map_or(authority, |(_, h)| h);
    let (host, port) = split_port(hostport)?;
    let host = clean_host(&host)?;
    let port = port.or(match scheme.as_deref() {
        Some("http" | "ws") => Some(80),
        Some("https" | "wss") => Some(443),
        _ => None,
    });
    Some(HostPort { host, port })
}

fn judge_host(grant: &str, observed: &str) -> Judgement {
    let Some(o) = observed_host(observed) else {
        return Judgement::Unknown;
    };
    let Some((gh, gp)) = split_port(grant) else {
        return Judgement::NoMatch;
    };
    let host_ok = match gh.strip_prefix("*.") {
        Some(suffix) => o
            .host
            .strip_suffix(suffix)
            .is_some_and(|pre| pre.len() > 1 && pre.ends_with('.')),
        None => gh == o.host,
    };
    if !host_ok {
        return Judgement::NoMatch;
    }
    match (gp, o.port) {
        (None, _) => Judgement::Match,
        (Some(g), Some(p)) if g == p => Judgement::Match,
        (Some(_), Some(_)) => Judgement::NoMatch,
        (Some(_), None) => Judgement::Unknown,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/grimble-model/src/args.rs::judge
    #[test]
    fn path_glob_matches_inside_and_rejects_outside() {
        let j = |g, o| judge(ArgKind::Path, g, o);
        assert_eq!(j("config/**", "config/app.toml"), Judgement::Match);
        assert_eq!(j("config/**", "./config/a/b"), Judgement::Match);
        let abs = ["", "home/u/.ssh/id_rsa"].join("/");
        assert_eq!(j("config/**", &abs), Judgement::NoMatch);
        assert_eq!(j("config/**", "config/../secret"), Judgement::NoMatch);
        assert_eq!(j("config/*.toml", "config/a/b.toml"), Judgement::NoMatch);
        assert_eq!(j("/etc/hosts", "/etc/./hosts"), Judgement::Match);
        assert_eq!(j("config/**", "../config/x"), Judgement::NoMatch);
        assert_eq!(j("**", "../x"), Judgement::NoMatch);
        assert_eq!(j("config/**", "config/*"), Judgement::Unknown);
    }

    /// A fresh scratch directory (resolved) holding `root/` and `outside/`.
    #[cfg(unix)]
    fn scratch(tag: &str) -> (std::path::PathBuf, std::path::PathBuf) {
        let base = std::env::temp_dir().join(format!("args-resolve-{}-{tag}", std::process::id()));
        let _ = std::fs::remove_dir_all(&base);
        std::fs::create_dir_all(base.join("root/config")).unwrap();
        std::fs::create_dir_all(base.join("outside")).unwrap();
        std::fs::write(base.join("outside/secret"), "x").unwrap();
        let base = resolve_real(Path::new("/"), &base).unwrap();
        (base.join("root"), base.join("outside"))
    }

    // frob:tests crates/grimble-model/src/args.rs::judge_resolved
    #[cfg(unix)]
    #[test]
    fn symlink_out_of_the_grant_is_no_match() {
        use std::os::unix::fs::symlink;
        let (root, outside) = scratch("escape");
        symlink(&outside, root.join("config/out")).unwrap();
        let j = |g, o| judge_resolved(ArgKind::Path, g, o, &root).unwrap();
        // lexically inside, really outside
        assert_eq!(
            judge(ArgKind::Path, "config/**", "config/out/secret"),
            Judgement::Match
        );
        assert_eq!(j("config/**", "config/out/secret"), Judgement::NoMatch);
        // `..` after a link applies to the link target, not the link's directory
        assert_eq!(j("config/**", "config/out/../x"), Judgement::NoMatch);
        assert_eq!(j("config/**", "config/app.toml"), Judgement::Match);
        // an absolute observed path is resolved too
        let abs = root.join("config/out/secret");
        assert_eq!(j("config/**", text_of(&abs).unwrap()), Judgement::NoMatch);
    }

    // frob:tests crates/grimble-model/src/args.rs::judge_resolved
    #[cfg(unix)]
    #[test]
    fn symlink_inside_the_grant_matches_by_real_location() {
        use std::os::unix::fs::symlink;
        let (root, outside) = scratch("inside");
        std::fs::create_dir_all(root.join("data")).unwrap();
        symlink(root.join("config"), root.join("data/alias")).unwrap();
        let j = |g, o| judge_resolved(ArgKind::Path, g, o, &root).unwrap();
        assert_eq!(j("config/**", "data/alias/app.toml"), Judgement::Match);
        assert_eq!(j("data/**", "data/alias/app.toml"), Judgement::NoMatch);
        // an absolute grant naming the outside dir through a link in its prefix
        symlink(&outside, root.join("data/o")).unwrap();
        let g = format!("{}/**", text_of(&root.join("data/o")).unwrap());
        let o = outside.join("secret");
        let jr = judge_resolved(ArgKind::Path, &g, text_of(&o).unwrap(), &root).unwrap();
        assert_eq!(jr, Judgement::Match);
    }

    // frob:tests crates/grimble-model/src/args.rs::judge_resolved
    #[cfg(unix)]
    #[test]
    fn dangling_missing_and_loop_paths_fail_closed() {
        use std::os::unix::fs::symlink;
        let (root, outside) = scratch("edge");
        let j = |g, o| judge_resolved(ArgKind::Path, g, o, &root);
        // a dangling link whose target would be outside: follow it, no match
        symlink(outside.join("nope"), root.join("config/dangle")).unwrap();
        assert_eq!(j("config/**", "config/dangle").unwrap(), Judgement::NoMatch);
        // a dangling link to a missing path inside the grant still matches
        symlink(root.join("config/later"), root.join("config/ok")).unwrap();
        assert_eq!(j("config/**", "config/ok").unwrap(), Judgement::Match);
        // a nonexistent target keeps lexical semantics
        assert_eq!(j("config/**", "config/new/file").unwrap(), Judgement::Match);
        assert_eq!(
            j("config/**", "config/new/../../x").unwrap(),
            Judgement::NoMatch
        );
        // a loop is an error, not a verdict
        symlink(root.join("config/b"), root.join("config/a")).unwrap();
        symlink(root.join("config/a"), root.join("config/b")).unwrap();
        assert!(matches!(
            j("config/**", "config/a/x"),
            Err(ResolveError::Loop(_))
        ));
        // glob characters stay Unknown and other kinds delegate
        assert_eq!(j("config/**", "config/*").unwrap(), Judgement::Unknown);
        let h = judge_resolved(ArgKind::Host, "a.com", "a.com", &root).unwrap();
        assert_eq!(h, Judgement::Match);
    }

    // frob:tests crates/grimble-model/src/args.rs::judge
    #[test]
    fn host_judgement_reads_the_real_host() {
        let j = |g, o| judge(ArgKind::Host, g, o);
        assert_eq!(
            j("api.example.com", "https://api.example.com/v1"),
            Judgement::Match
        );
        assert_eq!(
            j("api.example.com", "https://api.example.com@evil.com/"),
            Judgement::NoMatch
        );
        assert_eq!(j("api.example.com", "API.Example.com."), Judgement::Match);
        assert_eq!(j("*.example.com", "a.example.com"), Judgement::Match);
        assert_eq!(j("*.example.com", "example.com"), Judgement::NoMatch);
        assert_eq!(j("*.example.com", "evilexample.com"), Judgement::NoMatch);
        assert_eq!(
            j("example.com:443", "https://example.com"),
            Judgement::Match
        );
        assert_eq!(j("example.com:443", "example.com:8080"), Judgement::NoMatch);
        assert_eq!(j("example.com:443", "example.com"), Judgement::Unknown);
        assert_eq!(j("example.com", "example.com:22"), Judgement::Match);
        assert_eq!(j("[::1]:80", "[::1]:80"), Judgement::Match);
        assert_eq!(j("example.com", "ex\\@mple.com"), Judgement::Unknown);
    }

    // frob:tests crates/grimble-model/src/args.rs::validate
    #[test]
    fn malformed_grant_arguments_are_rejected() {
        assert!(validate(ArgKind::Path, "config/**").is_ok());
        assert!(validate(ArgKind::Path, "a/../b").is_err());
        assert!(validate(ArgKind::Path, "a/[x]").is_err());
        assert!(validate(ArgKind::Path, "").is_err());
        assert!(validate(ArgKind::Host, "api.example.com:443").is_ok());
        assert!(validate(ArgKind::Host, "*.example.com").is_ok());
        assert!(validate(ArgKind::Host, "https://example.com").is_err());
        assert!(validate(ArgKind::Host, "example.com:99999").is_err());
        assert!(validate(ArgKind::Host, "Example.com").is_err());
        assert!(validate(ArgKind::Host, "a*.example.com").is_err());
        assert!(validate(ArgKind::EnvName, "HOME").is_ok());
        assert!(validate(ArgKind::EnvName, "A=B").is_err());
        assert!(validate(ArgKind::Binary, "git").is_ok());
        assert!(validate(ArgKind::Binary, "git status").is_err());
    }

    // frob:tests crates/grimble-model/src/args.rs::arg_kind
    #[test]
    fn atoms_map_to_kinds() {
        assert_eq!(arg_kind("fs.read"), Some(ArgKind::Path));
        assert_eq!(arg_kind("net.connect"), Some(ArgKind::Host));
        assert_eq!(arg_kind("process.env"), Some(ArgKind::EnvName));
        assert_eq!(arg_kind("exec"), Some(ArgKind::Binary));
        assert_eq!(arg_kind("process"), None);
        assert_eq!(arg_kind("pack.custom"), None);
    }
}
