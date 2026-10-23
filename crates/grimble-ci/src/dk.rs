//! DK001 to DK004 over one Dockerfile.

// frob:ticket 01M3Z7157776CWEKRPG8886VJ4

use gob_rules::Severity;

use crate::CiConfig;
use crate::docker::{Instruction, Stage, is_internal, split_ref, stages};
use crate::finding::fire;
use grimble_verdict::Verdict;

/// Rule id: the image runs as root.
pub const DK001: &str = "DK001";
/// Rule id: a base image is not pinned by digest.
pub const DK002: &str = "DK002";
/// Rule id: a base image has no tag or the `latest` tag.
pub const DK003: &str = "DK003";
/// Rule id: a download is piped into a shell.
pub const DK004: &str = "DK004";

/// Findings of DK001 to DK004 for the Dockerfile `path`; the count is the subjects examined per rule.
pub(crate) fn check(path: &str, text: &str, cfg: &CiConfig) -> Vec<Verdict> {
    let all = stages(text);
    tracing::debug!(path, stages = all.len(), "checking Dockerfile");
    let mut out = Vec::new();
    root_user(path, &all, &mut out);
    for (i, stage) in all.iter().enumerate() {
        base_image(path, stage, &all[..i], cfg, &mut out);
        for ins in stage.body.iter().filter(|i| i.keyword == "RUN") {
            pipe_to_shell(path, ins, cfg, &mut out);
        }
    }
    out
}

/// The user in effect at the end of stage `idx` (`None` when no USER was ever set).
fn effective_user(all: &[Stage], idx: usize, depth: usize) -> Option<String> {
    let stage = &all[idx];
    if let Some(u) = stage.body.iter().rev().find(|i| i.keyword == "USER") {
        return Some(u.args.split_whitespace().next().unwrap_or("").to_owned());
    }
    let base = stage.image.to_ascii_lowercase();
    if depth < all.len()
        && let Some(j) = all[..idx]
            .iter()
            .position(|s| s.name.as_deref() == Some(&base))
    {
        return effective_user(all, j, depth + 1);
    }
    None
}

/// DK001 on the final stage.
fn root_user(path: &str, all: &[Stage], out: &mut Vec<Verdict>) {
    let Some(last) = all.last() else { return };
    if last.image.eq_ignore_ascii_case("scratch") {
        tracing::debug!(path, "DK001 skips a scratch final stage");
        return;
    }
    let user = effective_user(all, all.len() - 1, 0);
    let name = user.as_deref().map(|u| u.split(':').next().unwrap_or(u));
    let root = matches!(name, None | Some("root" | "0"));
    if root {
        let why = if user.is_none() {
            "never sets USER"
        } else {
            "ends as root"
        };
        out.push(fire(
            DK001,
            Severity::Advisory,
            (path, last.from_range),
            format!("the final stage {why}, so the container runs as root; add `USER <non-root>` (for example `RUN useradd -r app` then `USER app`) before the entrypoint"),
            format!("{path}:final-stage"),
        ));
    }
}

/// DK002 and DK003 on the base image of `stage`.
fn base_image(
    path: &str,
    stage: &Stage,
    earlier: &[Stage],
    cfg: &CiConfig,
    out: &mut Vec<Verdict>,
) {
    let image = stage.image.as_str();
    if image.is_empty() || image.contains('$') || is_internal(image, earlier) {
        return;
    }
    let (_, tag, digest) = split_ref(image);
    if digest.is_none() && cfg.require_digest {
        out.push(fire(
            DK002,
            Severity::Advisory,
            (path, stage.from_range),
            format!("base image `{image}` is not pinned by digest; resolve it and write `{image}@sha256:<digest>`"),
            format!("{path}:{image}:digest"),
        ));
    }
    if digest.is_none() && matches!(tag, None | Some("latest")) {
        out.push(fire(
            DK003,
            Severity::Warn,
            (path, stage.from_range),
            format!(
                "base image `{image}` floats on `latest`; pin a version tag such as `{}:<version>`",
                split_ref(image).0
            ),
            format!("{path}:{image}:tag"),
        ));
    }
}

/// DK004 on one `RUN`.
fn pipe_to_shell(path: &str, ins: &Instruction, cfg: &CiConfig, out: &mut Vec<Verdict>) {
    if ins.args.starts_with('[') {
        return;
    }
    let Some(url) = piped_download(&ins.args) else {
        return;
    };
    let host = url_host(&url);
    if cfg
        .allow_pipe_hosts
        .iter()
        .any(|h| host == *h || host.ends_with(&format!(".{h}")))
    {
        tracing::debug!(path, host, "DK004 allows this host");
        return;
    }
    out.push(fire(
        DK004,
        Severity::Advisory,
        (path, ins.range),
        format!("a download from `{host}` is piped straight into a shell; fetch it to a file, verify a checksum, then run it"),
        format!("{path}:{}", ins.range.0),
    ));
}

/// The first word of `cmd` after `sudo` and `env`/`VAR=` prefixes.
fn command_word(cmd: &str) -> &str {
    cmd.split_whitespace()
        .find(|w| !matches!(*w, "sudo" | "env") && !w.contains('='))
        .unwrap_or("")
}

/// True for a shell interpreter name.
fn is_shell(word: &str) -> bool {
    let base = word.rsplit('/').next().unwrap_or(word);
    matches!(base, "sh" | "bash" | "zsh" | "dash" | "ash")
}

/// The URL (or the word `?`) of a download piped into, or substituted into, a shell.
fn piped_download(args: &str) -> Option<String> {
    let flat = args.replace("||", "\u{1}");
    let segs: Vec<&str> = flat.split('|').collect();
    for pair in segs.windows(2) {
        let left = pair[0].rsplit(['&', ';']).next().unwrap_or("");
        let dl = matches!(command_word(left), "curl" | "wget");
        if dl && is_shell(command_word(pair[1].trim_start_matches(['&', ';']))) {
            return Some(first_url(left));
        }
    }
    for marker in ["$(curl", "$(wget", "<(curl", "<(wget", "`curl", "`wget"] {
        if let Some(at) = args.find(marker) {
            let before = &args[..at];
            let shellish = before.split_whitespace().any(is_shell);
            if shellish {
                return Some(first_url(&args[at..]));
            }
        }
    }
    None
}

/// The first `http(s)://` word of `s`, else `?`.
fn first_url(s: &str) -> String {
    s.split(|c: char| c.is_whitespace() || matches!(c, '"' | '\'' | ')' | '`'))
        .find(|w| w.starts_with("http://") || w.starts_with("https://") || w.starts_with("ftp://"))
        .unwrap_or("?")
        .to_owned()
}

/// The host of a URL (`?` stays `?`).
fn url_host(url: &str) -> String {
    let rest = url.split_once("://").map_or(url, |(_, r)| r);
    rest.split(['/', ':', '?'])
        .next()
        .unwrap_or(rest)
        .to_owned()
}
