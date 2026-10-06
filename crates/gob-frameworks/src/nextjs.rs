//! Next.js routes from the `app` and `pages` directory conventions (also under `src/`).
//!
//! App router: `page` files are GET pages, `route` files answer once per exported HTTP method, `layout`
//! files wrap everything below their directory; route groups `(group)` add no segment, `@slot` and `_private`
//! directories add no route, and an intercepting route `(.)x` is reported `Unknown` without a pattern.
//! Pages router: every file is a page except `_app`, `_document` and `_error`; `pages/api` files answer any
//! method. Dynamic segments are written `:name`, `:name+` (catch-all) and `:name*` (optional catch-all). A
//! page behind a `"use client"` directive carries `client`.

// frob:ticket 01M47QKVBB5G9N1QZP3AVXTRHX

use std::collections::BTreeSet;

use gob_symbols::Visibility;
use tracing::{debug, trace};

use crate::registry::{Detector, FrameworkEntry, join};
use crate::repo::Repo;
use crate::types::{Detection, Discovery, Entrypoint, EntrypointKind, Method, Route, Status};

/// The registry entry of Next.js.
pub(crate) const ENTRY: FrameworkEntry = FrameworkEntry {
    name: "nextjs",
    detectors: &[
        Detector::Dependency("next"),
        Detector::ConfigFile("next.config"),
    ],
    discover,
};

/// Source extensions a route file may have.
const EXTENSIONS: [&str; 4] = ["tsx", "ts", "jsx", "js"];

/// Which router a directory holds.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Router {
    /// The `app` directory.
    App,
    /// The `pages` directory.
    Pages,
}

/// The path segment of one directory or file name, or `None` when it adds none; `Err(())` when the segment
/// cannot be turned into a static pattern (an intercepting route).
fn segment(name: &str) -> Result<Option<String>, ()> {
    if name.starts_with("(.") {
        return Err(());
    }
    if name.starts_with('(') && name.ends_with(')') {
        return Ok(None);
    }
    if let Some(inner) = name
        .strip_prefix("[[...")
        .and_then(|n| n.strip_suffix("]]"))
    {
        return Ok(Some(format!(":{inner}*")));
    }
    if let Some(inner) = name.strip_prefix("[...").and_then(|n| n.strip_suffix(']')) {
        return Ok(Some(format!(":{inner}+")));
    }
    if let Some(inner) = name.strip_prefix('[').and_then(|n| n.strip_suffix(']')) {
        return Ok(Some(format!(":{inner}")));
    }
    Ok(Some(name.to_owned()))
}

/// The pattern of the path segments `names`, or `None` when one of them has no static pattern.
fn pattern(names: &[&str]) -> Option<String> {
    let mut segs = Vec::new();
    for n in names {
        match segment(n) {
            Ok(Some(s)) => segs.push(s),
            Ok(None) => {}
            Err(()) => return None,
        }
    }
    Some(format!("/{}", segs.join("/")))
}

/// Splits a file name into stem and extension when the extension is a source extension.
fn split_ext(name: &str) -> Option<(&str, &str)> {
    let (stem, ext) = name.rsplit_once('.')?;
    (EXTENSIONS.contains(&ext) && stem.rsplit_once('.').is_none_or(|(_, e)| e != "d"))
        .then_some((stem, ext))
}

/// True when `text` starts with a `"use client"` directive (comments and blank lines may come first).
fn use_client(text: &str) -> bool {
    text.lines()
        .map(str::trim)
        .find(|l| {
            !(l.is_empty() || l.starts_with("//") || l.starts_with("/*") || l.starts_with('*'))
        })
        .is_some_and(|l| l.starts_with("\"use client\"") || l.starts_with("'use client'"))
}

/// Finds the routes and entrypoints of one detected member.
fn discover(repo: &Repo<'_>, det: &Detection) -> Discovery {
    let mut out = Discovery::default();
    let files: BTreeSet<&str> = repo.files().iter().map(String::as_str).collect();
    for (router, sub) in [
        (Router::App, "app"),
        (Router::App, "src/app"),
        (Router::Pages, "pages"),
        (Router::Pages, "src/pages"),
    ] {
        let root = join(&det.dir, sub);
        let prefix = format!("{root}/");
        let inside: Vec<&str> = files
            .iter()
            .copied()
            .filter(|f| f.starts_with(&prefix))
            .collect();
        if inside.is_empty() {
            continue;
        }
        debug!(
            member = det.member,
            root,
            files = inside.len(),
            "next.js routing root"
        );
        for file in inside {
            let rel = &file[prefix.len()..];
            match router {
                Router::App => app_file(repo, det, &root, rel, file, &files, &mut out),
                Router::Pages => pages_file(repo, det, &root, rel, file, &files, &mut out),
            }
        }
    }
    for base in [det.dir.clone(), join(&det.dir, "src")] {
        for ext in EXTENSIONS {
            let file = join(&base, &format!("middleware.{ext}"));
            if files.contains(file.as_str()) {
                out.entrypoints
                    .push(entry(det, EntrypointKind::Middleware, &file));
            }
        }
    }
    out
}

/// An entrypoint of `det`.
fn entry(det: &Detection, kind: EntrypointKind, file: &str) -> Entrypoint {
    Entrypoint {
        framework: ENTRY.name,
        member: det.member.clone(),
        kind,
        file: file.to_owned(),
    }
}

/// A route of `det` with the common fields filled in.
fn route(det: &Detection, file: &str, pattern: Option<String>, method: Method) -> Route {
    Route {
        framework: ENTRY.name,
        member: det.member.clone(),
        status: if pattern.is_some() {
            Status::Must
        } else {
            Status::Unknown
        },
        pattern,
        method,
        handler: None,
        component: None,
        layouts: Vec::new(),
        file: file.to_owned(),
        line: 1,
        client: false,
    }
}

/// The layout files from the app root down to the directory `dirs`.
fn layouts(repo: &Repo<'_>, root: &str, dirs: &[&str], files: &BTreeSet<&str>) -> Vec<String> {
    let mut chain = Vec::new();
    for depth in 0..=dirs.len() {
        let dir = std::iter::once(root)
            .chain(dirs[..depth].iter().copied())
            .collect::<Vec<_>>()
            .join("/");
        if let Some(found) = EXTENSIONS
            .iter()
            .map(|e| format!("{dir}/layout.{e}"))
            .find(|f| files.contains(f.as_str()))
        {
            chain.push(repo.default_export(&found));
        }
    }
    chain
}

/// One file of an `app` directory.
fn app_file(
    repo: &Repo<'_>,
    det: &Detection,
    root: &str,
    rel: &str,
    file: &str,
    files: &BTreeSet<&str>,
    out: &mut Discovery,
) {
    let parts: Vec<&str> = rel.split('/').collect();
    let Some((name, dirs)) = parts.split_last() else {
        return;
    };
    let Some((stem, _)) = split_ext(name) else {
        return;
    };
    if !matches!(stem, "page" | "route")
        || dirs
            .iter()
            .any(|d| d.starts_with('@') || d.starts_with('_'))
    {
        return;
    }
    let pat = pattern(dirs);
    let layouts = layouts(repo, root, dirs, files);
    trace!(file, stem, "next.js app file");
    if stem == "page" {
        let mut r = route(det, file, pat, Method::Get);
        r.component = Some(repo.default_export(file));
        r.layouts = layouts;
        r.client = repo.text(file).is_some_and(use_client);
        out.routes.push(r);
        out.entrypoints.push(entry(det, EntrypointKind::Page, file));
        return;
    }
    let handlers: Vec<(Method, String)> = repo
        .folded(file)
        .map(|f| {
            f.file
                .symbols
                .iter()
                .filter(|s| s.visibility == Visibility::Public)
                .filter_map(|s| {
                    let m = Method::from_export(s.symref.name()?)?;
                    Some((m, s.symref.to_string()))
                })
                .collect()
        })
        .unwrap_or_default();
    if handlers.is_empty() {
        // The exports are not declared here (a re-export): a handler exists but its methods are not known.
        let mut r = route(det, file, pat.clone(), Method::Any);
        r.status = r.status.min(Status::May);
        r.layouts = Vec::new();
        out.routes.push(r);
    }
    for (method, symref) in handlers {
        let mut r = route(det, file, pat.clone(), method);
        r.handler = Some(symref);
        out.routes.push(r);
    }
    out.entrypoints
        .push(entry(det, EntrypointKind::Handler, file));
}

/// One file of a `pages` directory.
fn pages_file(
    repo: &Repo<'_>,
    det: &Detection,
    root: &str,
    rel: &str,
    file: &str,
    files: &BTreeSet<&str>,
    out: &mut Discovery,
) {
    let mut parts: Vec<&str> = rel.split('/').collect();
    let Some(name) = parts.pop() else {
        return;
    };
    let Some((stem, _)) = split_ext(name) else {
        return;
    };
    if matches!(stem, "_app" | "_document" | "_error" | "_middleware") {
        return;
    }
    let api = parts.first() == Some(&"api");
    if stem != "index" {
        parts.push(stem);
    }
    let mut r = route(
        det,
        file,
        pattern(&parts),
        if api { Method::Any } else { Method::Get },
    );
    let default = repo.default_export(file);
    if api {
        r.handler = Some(default);
        out.entrypoints
            .push(entry(det, EntrypointKind::Handler, file));
    } else {
        r.component = Some(default);
        r.client = false;
        if let Some(app) = EXTENSIONS
            .iter()
            .map(|e| format!("{root}/_app.{e}"))
            .find(|f| files.contains(f.as_str()))
        {
            r.layouts = vec![repo.default_export(&app)];
        }
        out.entrypoints.push(entry(det, EntrypointKind::Page, file));
    }
    out.routes.push(r);
}

#[cfg(test)]
mod tests {
    use super::{pattern, use_client};

    #[test]
    // frob:tests crates/gob-frameworks/src/nextjs.rs::pattern
    fn directory_names_become_patterns() {
        assert_eq!(pattern(&[]).as_deref(), Some("/"));
        assert_eq!(pattern(&["(shop)", "p", "[id]"]).as_deref(), Some("/p/:id"));
        assert_eq!(pattern(&["[...rest]"]).as_deref(), Some("/:rest+"));
        assert_eq!(pattern(&["a", "[[...rest]]"]).as_deref(), Some("/a/:rest*"));
        assert_eq!(pattern(&["(..)photo"]), None);
    }

    #[test]
    // frob:tests crates/gob-frameworks/src/nextjs.rs::use_client
    fn the_use_client_directive_must_come_first() {
        assert!(use_client("// c\n\n'use client';\nexport {}"));
        assert!(use_client("\"use client\"\n"));
        assert!(!use_client("import x from 'y';\n'use client';"));
    }
}
