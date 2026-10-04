//! Field-level validators; each returns a reason string on failure.

/// Checks a kebab-case identifier: `[a-z][a-z0-9-]*`, at most `max` bytes.
pub(crate) fn kebab(s: &str, max: usize) -> Result<(), String> {
    let mut chars = s.chars();
    let ok = chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-');
    if !ok {
        return Err("must be kebab-case ([a-z][a-z0-9-]*)".into());
    }
    bound(s, max)
}

/// Checks a rule family prefix: 2 to `max` ASCII capital letters.
pub(crate) fn family(s: &str, max: usize) -> Result<(), String> {
    if s.len() < 2 || !s.bytes().all(|b| b.is_ascii_uppercase()) {
        return Err("must be 2 or more capital letters A-Z".into());
    }
    bound(s, max)
}

/// Checks `X.Y.Z` with an optional `-pre` suffix (no ranges).
pub(crate) fn semver(s: &str, max: usize) -> Result<(), String> {
    bound(s, max)?;
    let (core, pre) = match s.split_once('-') {
        Some((c, p)) => (c, Some(p)),
        None => (s, None),
    };
    let parts: Vec<&str> = core.split('.').collect();
    let num = |p: &&str| {
        !p.is_empty()
            && p.bytes().all(|b| b.is_ascii_digit())
            && (p.len() == 1 || !p.starts_with('0'))
    };
    if parts.len() != 3 || !parts.iter().all(num) {
        return Err("must be an exact semver X.Y.Z with an optional -pre".into());
    }
    if let Some(p) = pre
        && (p.is_empty()
            || !p
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'-'))
    {
        return Err("pre-release must be [0-9A-Za-z.-]+".into());
    }
    Ok(())
}

/// Checks a version requirement: non-empty printable ASCII, no control bytes.
pub(crate) fn requirement(s: &str, max: usize) -> Result<(), String> {
    if s.is_empty() || !s.bytes().all(|b| (0x20..0x7f).contains(&b)) {
        return Err("must be non-empty printable ASCII".into());
    }
    bound(s, max)
}

/// Checks a pack-relative path or glob: relative, forward slashes, no `..`.
pub(crate) fn rel_path(s: &str, max: usize) -> Result<(), String> {
    bound(s, max)?;
    if s.is_empty() || !s.bytes().all(|b| (0x21..0x7f).contains(&b)) {
        return Err("must be non-empty printable ASCII without spaces".into());
    }
    if s.starts_with('/') || s.contains('\\') || s.contains(':') {
        return Err("must be a relative path with forward slashes".into());
    }
    if s.split('/')
        .any(|seg| seg.is_empty() || seg == ".." || seg == ".")
    {
        return Err("must not contain empty, `.` or `..` segments".into());
    }
    Ok(())
}

/// Checks an effect key or grant: non-empty printable ASCII.
pub(crate) fn effect_token(s: &str, max: usize) -> Result<(), String> {
    if s.is_empty() || !s.bytes().all(|b| (0x21..0x7f).contains(&b)) {
        return Err("must be non-empty printable ASCII without spaces".into());
    }
    bound(s, max)
}

fn bound(s: &str, max: usize) -> Result<(), String> {
    if s.len() > max {
        return Err(format!("is {} bytes, the limit is {max}", s.len()));
    }
    Ok(())
}
