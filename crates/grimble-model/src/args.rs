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
//! Paths are compared lexically: `.` and empty segments drop, `..` pops a segment, and a path
//! that climbs above its start never matches. Symbolic links are not followed, since nothing is
//! read from disk. Hosts compare case-insensitively on labels; a `*.` prefix matches subdomains
//! only, never the apex.

// frob:ticket 01M5XNNH61Z437EDDB05X9CAQE

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
        assert_eq!(j("config/**", "/home/u/.ssh/id_rsa"), Judgement::NoMatch);
        assert_eq!(j("config/**", "config/../secret"), Judgement::NoMatch);
        assert_eq!(j("config/*.toml", "config/a/b.toml"), Judgement::NoMatch);
        assert_eq!(j("/etc/hosts", "/etc/./hosts"), Judgement::Match);
        assert_eq!(j("config/**", "../config/x"), Judgement::NoMatch);
        assert_eq!(j("**", "../x"), Judgement::NoMatch);
        assert_eq!(j("config/**", "config/*"), Judgement::Unknown);
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
