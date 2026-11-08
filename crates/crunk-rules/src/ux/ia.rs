//! The information-architecture checks: every sitemap route has a screen and every screen a
//! route, code routes appear in the sitemap, depth, label uniqueness and reachability from home.
//! Reads `design/ia/sitemap.toml`; an absent sitemap is silent.

// frob:ticket 01M5XCZ0XPCPA1DT2QB5VGHDZC

use std::collections::{BTreeMap, BTreeSet};

use crunk_spec::DesignSpec;
use crunk_spec::ia::{Sitemap, parse_sitemap, route_shape};

use crate::sheets::site_path;

/// The sitemap file, relative to the project root.
pub const SITEMAP_PATH: &str = "design/ia/sitemap.toml";

/// What an IA finding is about.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum IaIssue {
    /// The sitemap file is malformed or violates the schema (a parent cycle included).
    Schema,
    /// A sitemap route has no screen.
    RouteWithoutScreen,
    /// A screen has no sitemap route.
    ScreenWithoutRoute,
    /// A route found in code is absent from the sitemap.
    CodeRouteMissing,
    /// Route discovery was unavailable, so the code comparison could not run.
    Unresolved,
    /// A page sits deeper than the configured maximum.
    TooDeep,
    /// Sibling pages share a label, ignoring case.
    LabelCollision,
    /// A page cannot be reached from home.
    Unreachable,
}

/// One IA finding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IaFinding {
    /// What kind of finding.
    pub issue: IaIssue,
    /// The file it is about, relative to the project root.
    pub path: String,
    /// The 1-based line, when the issue has one.
    pub line: Option<usize>,
    /// The human message.
    pub message: String,
}

/// A screen as the IA checks see it: its id and entry route.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScreenRoute {
    /// The screen id.
    pub id: String,
    /// The route the screen is entered at.
    pub entry: String,
}

/// The loaded sitemap, or the finding explaining why it did not load; `None` fields when absent.
#[derive(Debug, Clone, Default)]
pub struct IaFacts {
    /// The sitemap file's path and text, when the file exists.
    pub source: Option<(String, String)>,
    /// The parsed sitemap.
    pub sitemap: Option<Sitemap>,
    /// A load failure as a finding.
    pub load_findings: Vec<IaFinding>,
}

impl IaFacts {
    /// Read `design/ia/sitemap.toml`; a missing file gives empty facts, a bad one a schema finding.
    pub fn load(spec: &DesignSpec) -> Self {
        let path = spec.root.join(SITEMAP_PATH);
        let rel = site_path(spec, &path);
        let Ok(text) = std::fs::read_to_string(&path) else {
            tracing::debug!(path = %rel, "no sitemap; IA checks are silent");
            return Self::default();
        };
        match parse_sitemap(&text) {
            Ok(map) => Self {
                source: Some((rel, text)),
                sitemap: Some(map),
                load_findings: Vec::new(),
            },
            Err(err) => {
                tracing::warn!(path = %rel, code = err.code(), %err, "sitemap invalid");
                let finding = IaFinding {
                    issue: IaIssue::Schema,
                    path: rel.clone(),
                    line: None,
                    message: format!("{}: {err}", err.code()),
                };
                Self {
                    source: Some((rel, text)),
                    sitemap: None,
                    load_findings: vec![finding],
                }
            }
        }
    }
}

/// The checker's view of one sitemap file.
struct Ctx<'a> {
    map: &'a Sitemap,
    path: &'a str,
    text: &'a str,
}

impl Ctx<'_> {
    /// The 1-based line of the first line mentioning `needle`.
    fn line_of(&self, needle: &str) -> Option<usize> {
        let quoted = format!("\"{needle}\"");
        self.text
            .lines()
            .position(|l| l.contains(&quoted))
            .map(|i| i + 1)
    }

    fn finding(&self, issue: IaIssue, route: &str, message: String) -> IaFinding {
        IaFinding {
            issue,
            path: self.path.to_owned(),
            line: self.line_of(route),
            message,
        }
    }
}

/// Route/screen agreement: pages with no screen, screens with no page.
fn check_screens(cx: &Ctx, screens: &[ScreenRoute]) -> Vec<IaFinding> {
    let by_shape: BTreeMap<String, &ScreenRoute> =
        screens.iter().map(|s| (route_shape(&s.entry), s)).collect();
    let ids: BTreeSet<&str> = screens.iter().map(|s| s.id.as_str()).collect();
    let mut served: BTreeSet<&str> = BTreeSet::new();
    let mut out = Vec::new();
    for page in &cx.map.pages {
        let screen = match page.screen.as_deref() {
            Some(id) if ids.contains(id) => Some(id),
            Some(_) => None,
            None => by_shape
                .get(&route_shape(&page.route))
                .map(|s| s.id.as_str()),
        };
        match screen {
            Some(id) => {
                served.insert(id);
            }
            None => out.push(cx.finding(
                IaIssue::RouteWithoutScreen,
                &page.route,
                format!("route `{}` has no screen", page.route),
            )),
        }
    }
    let shapes: BTreeSet<String> = cx.map.pages.iter().map(|p| route_shape(&p.route)).collect();
    for screen in screens {
        if !served.contains(screen.id.as_str()) && !shapes.contains(&route_shape(&screen.entry)) {
            out.push(cx.finding(
                IaIssue::ScreenWithoutRoute,
                &screen.id,
                format!("screen `{}` has no sitemap route", screen.id),
            ));
        }
    }
    out
}

/// Sitemap versus routes found in code; `None` means discovery was unavailable.
fn check_code_routes(cx: &Ctx, code_routes: Option<&[String]>) -> Vec<IaFinding> {
    let Some(code) = code_routes else {
        return vec![
            cx.finding(
                IaIssue::Unresolved,
                "",
                "routes in code could not be discovered; the sitemap/code comparison is unresolved"
                    .to_owned(),
            ),
        ];
    };
    let shapes: BTreeSet<String> = cx.map.pages.iter().map(|p| route_shape(&p.route)).collect();
    code.iter()
        .filter(|r| !shapes.contains(&route_shape(r)))
        .map(|r| {
            cx.finding(
                IaIssue::CodeRouteMissing,
                r,
                format!("route `{r}` exists in code but not in the sitemap"),
            )
        })
        .collect()
}

/// One finding per deepest path: leaf pages deeper than the limit.
fn check_depth(cx: &Ctx) -> Vec<IaFinding> {
    let limit = cx.map.depth_limit();
    let is_parent = |route: &str| {
        cx.map
            .pages
            .iter()
            .any(|p| p.parent.as_deref() == Some(route))
    };
    cx.map
        .pages
        .iter()
        .filter(|p| !is_parent(&p.route))
        .filter_map(|p| {
            let depth = cx.map.depth(p);
            (depth > limit).then(|| {
                cx.finding(
                    IaIssue::TooDeep,
                    &p.route,
                    format!("`{}` is {depth} levels deep; the limit is {limit}", p.route),
                )
            })
        })
        .collect()
}

/// Sibling labels equal ignoring case.
fn check_labels(cx: &Ctx) -> Vec<IaFinding> {
    let mut groups: BTreeMap<(Option<&str>, String), Vec<&str>> = BTreeMap::new();
    for page in &cx.map.pages {
        let key = (page.parent.as_deref(), page.label.trim().to_lowercase());
        groups.entry(key).or_default().push(page.route.as_str());
    }
    groups
        .into_iter()
        .filter(|(_, routes)| routes.len() > 1)
        .map(|((_, label), routes)| {
            cx.finding(
                IaIssue::LabelCollision,
                routes[1],
                format!(
                    "sibling pages {} share the label `{label}`",
                    routes.join(", ")
                ),
            )
        })
        .collect()
}

/// Pages not reachable from home.
fn check_reachability(cx: &Ctx) -> Vec<IaFinding> {
    let reached = cx.map.reachable();
    cx.map
        .pages
        .iter()
        .filter(|p| !reached.contains(p.route.as_str()))
        .map(|p| {
            cx.finding(
                IaIssue::Unreachable,
                &p.route,
                format!(
                    "`{}` cannot be reached from home `{}`",
                    p.route, cx.map.home
                ),
            )
        })
        .collect()
}

/// Run every IA check; no sitemap gives no findings, a bad one only its schema finding.
#[must_use]
pub fn check_ia(
    facts: &IaFacts,
    screens: &[ScreenRoute],
    code_routes: Option<&[String]>,
) -> Vec<IaFinding> {
    let mut out = facts.load_findings.clone();
    let (Some(map), Some((path, text))) = (&facts.sitemap, &facts.source) else {
        return out;
    };
    let cx = Ctx { map, path, text };
    out.extend(check_screens(&cx, screens));
    out.extend(check_code_routes(&cx, code_routes));
    out.extend(check_depth(&cx));
    out.extend(check_labels(&cx));
    out.extend(check_reachability(&cx));
    tracing::debug!(findings = out.len(), "IA checks done");
    out
}
