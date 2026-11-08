//! Information-architecture files: `design/ia/sitemap.toml` (routes, labels, parent links) and
//! `design/ia/content-model.toml` (content types), validated without any project context.
//!
//! A cycle in parent links is a schema error here; route/screen agreement, depth, label and
//! reachability are project-level findings made by crunk-rules.

// frob:ticket 01M5XCZ0XPCPA1DT2QB5VGHDZC

use std::collections::{HashMap, HashSet};

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// The sitemap's home route when the file names none.
pub const DEFAULT_HOME: &str = "/";

/// The deepest page depth allowed when the file sets no `max_depth` (home is depth 0).
pub const DEFAULT_MAX_DEPTH: usize = 3;

fn default_home() -> String {
    DEFAULT_HOME.to_owned()
}

/// One sitemap file: the home route, the depth limit and the pages.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct Sitemap {
    /// The home route every page must be reachable from.
    #[serde(default = "default_home")]
    pub home: String,
    /// Deepest allowed page depth, home being 0.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_depth: Option<usize>,
    /// The pages, one per route.
    #[serde(default)]
    pub pages: Vec<SitePage>,
}

/// One page of the sitemap.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct SitePage {
    /// The route; a dynamic segment is `:name`, `[name]` or `{name}`.
    pub route: String,
    /// The navigation label.
    pub label: String,
    /// The screen id serving the route; absent means match a screen by its entry route.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub screen: Option<String>,
    /// The route of the parent page, absent for a root.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent: Option<String>,
    /// Routes this page links to besides its children.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub links: Vec<String>,
}

impl Sitemap {
    /// The deepest allowed depth, defaulted.
    #[must_use]
    pub fn depth_limit(&self) -> usize {
        self.max_depth.unwrap_or(DEFAULT_MAX_DEPTH)
    }

    /// The page with exactly this route.
    #[must_use]
    pub fn page(&self, route: &str) -> Option<&SitePage> {
        self.pages.iter().find(|p| p.route == route)
    }

    /// Depth of a page: parent hops to a root (home is a root unless it names a parent).
    #[must_use]
    pub fn depth(&self, page: &SitePage) -> usize {
        let mut depth = 0;
        let mut at = page;
        while let Some(parent) = at.parent.as_deref().and_then(|r| self.page(r)) {
            depth += 1;
            at = parent;
            if depth > self.pages.len() {
                break;
            }
        }
        depth
    }

    /// The routes reachable from home over parent-to-child and `links` edges, home included.
    #[must_use]
    pub fn reachable(&self) -> HashSet<&str> {
        let mut seen: HashSet<&str> = HashSet::new();
        let mut stack = vec![self.home.as_str()];
        while let Some(route) = stack.pop() {
            if !seen.insert(route) {
                continue;
            }
            for page in &self.pages {
                if page.parent.as_deref() == Some(route) {
                    stack.push(page.route.as_str());
                }
                if page.route == route {
                    stack.extend(page.links.iter().map(String::as_str));
                }
            }
        }
        seen
    }
}

/// One content type of the content model.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ContentType {
    /// The type name, unique in the model.
    pub name: String,
    /// The field names the type carries.
    #[serde(default)]
    pub fields: Vec<String>,
}

/// One content-model file.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ContentModel {
    /// The content types.
    #[serde(default)]
    pub types: Vec<ContentType>,
}

/// Why an IA file was rejected; every variant has a stable code.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum IaFileError {
    /// Not valid TOML, a missing or unknown key, or a wrongly typed value.
    #[error("invalid IA file: {0}")]
    Parse(String),
    /// A page route or label is blank, or a route does not start with `/`.
    #[error("`pages[{index}].{field}` is blank or not a route")]
    BadField {
        /// Position in `pages`.
        index: usize,
        /// `route` or `label`.
        field: &'static str,
    },
    /// Two pages share a route.
    #[error("`pages[{index}]` repeats route `{route}`")]
    DuplicateRoute {
        /// Position of the repeat.
        index: usize,
        /// The repeated route.
        route: String,
    },
    /// A `parent` names no page.
    #[error("`pages[{index}].parent` names unknown route `{parent}`")]
    UnknownParent {
        /// Position in `pages`.
        index: usize,
        /// The missing parent.
        parent: String,
    },
    /// Parent links loop back on themselves.
    #[error("`pages[{index}]` is in a parent cycle through `{route}`")]
    ParentCycle {
        /// Position of a page on the cycle.
        index: usize,
        /// That page's route.
        route: String,
    },
    /// Two content types share a name.
    #[error("`types[{index}]` repeats content type `{name}`")]
    DuplicateType {
        /// Position of the repeat.
        index: usize,
        /// The repeated name.
        name: String,
    },
}

impl IaFileError {
    /// The stable error code.
    #[must_use]
    pub fn code(&self) -> &'static str {
        match self {
            Self::Parse(_) => "E-IA-PARSE",
            Self::BadField { .. } => "E-IA-FIELD",
            Self::DuplicateRoute { .. } => "E-IA-DUP-ROUTE",
            Self::UnknownParent { .. } => "E-IA-PARENT",
            Self::ParentCycle { .. } => "E-IA-CYCLE",
            Self::DuplicateType { .. } => "E-IA-DUP-TYPE",
        }
    }
}

/// True when `route` is a non-blank path starting with `/`.
fn is_route(route: &str) -> bool {
    route.starts_with('/') && !route.contains(char::is_whitespace)
}

/// The route with every dynamic segment (`:id`, `[id]`, `{id}`) replaced by `{}`: its param shape.
#[must_use]
pub fn route_shape(route: &str) -> String {
    let segments: Vec<&str> = route
        .split('/')
        .map(|seg| {
            let dynamic = seg.starts_with(':')
                || (seg.starts_with('[') && seg.ends_with(']'))
                || (seg.starts_with('{') && seg.ends_with('}'));
            if dynamic { "{}" } else { seg }
        })
        .collect();
    let joined = segments.join("/");
    if joined.len() > 1 {
        joined.trim_end_matches('/').to_owned()
    } else {
        joined
    }
}

/// Check each page's fields and route uniqueness.
fn check_pages(map: &Sitemap) -> Result<(), IaFileError> {
    let mut seen: HashSet<&str> = HashSet::new();
    for (index, page) in map.pages.iter().enumerate() {
        if !is_route(&page.route) {
            return Err(IaFileError::BadField {
                index,
                field: "route",
            });
        }
        if page.label.trim().is_empty() {
            return Err(IaFileError::BadField {
                index,
                field: "label",
            });
        }
        if !seen.insert(page.route.as_str()) {
            return Err(IaFileError::DuplicateRoute {
                index,
                route: page.route.clone(),
            });
        }
    }
    Ok(())
}

/// Check every parent names a page and no parent chain loops.
fn check_parents(map: &Sitemap) -> Result<(), IaFileError> {
    let parents: HashMap<&str, &str> = map
        .pages
        .iter()
        .filter_map(|p| p.parent.as_deref().map(|par| (p.route.as_str(), par)))
        .collect();
    for (index, page) in map.pages.iter().enumerate() {
        if let Some(parent) = page.parent.as_deref()
            && map.page(parent).is_none()
        {
            return Err(IaFileError::UnknownParent {
                index,
                parent: parent.to_owned(),
            });
        }
        let mut at = page.route.as_str();
        for _ in 0..=map.pages.len() {
            match parents.get(at) {
                Some(next) => at = next,
                None => break,
            }
            if at == page.route {
                return Err(IaFileError::ParentCycle {
                    index,
                    route: page.route.clone(),
                });
            }
        }
    }
    Ok(())
}

/// Parse and validate a sitemap file's text.
///
/// # Errors
/// [`IaFileError`] on bad TOML, an unknown key, a blank or non-`/` route, a blank label, a
/// repeated route, a parent naming no page, or a cycle in parent links.
pub fn parse_sitemap(text: &str) -> Result<Sitemap, IaFileError> {
    let map: Sitemap =
        toml_edit::de::from_str(text).map_err(|e| IaFileError::Parse(e.to_string()))?;
    check_pages(&map)?;
    check_parents(&map)?;
    tracing::debug!(pages = map.pages.len(), home = %map.home, "parsed sitemap");
    Ok(map)
}

/// Parse and validate a content-model file's text.
///
/// # Errors
/// [`IaFileError`] on bad TOML, an unknown key or a repeated type name.
pub fn parse_content_model(text: &str) -> Result<ContentModel, IaFileError> {
    let model: ContentModel =
        toml_edit::de::from_str(text).map_err(|e| IaFileError::Parse(e.to_string()))?;
    let mut seen: HashSet<&str> = HashSet::new();
    for (index, ty) in model.types.iter().enumerate() {
        if !seen.insert(ty.name.as_str()) {
            return Err(IaFileError::DuplicateType {
                index,
                name: ty.name.clone(),
            });
        }
    }
    tracing::debug!(types = model.types.len(), "parsed content model");
    Ok(model)
}

#[cfg(test)]
mod tests {
    use super::*;

    const GOOD: &str = "home = \"/\"\n[[pages]]\nroute = \"/\"\nlabel = \"Home\"\n[[pages]]\nroute = \"/a\"\nlabel = \"A\"\nparent = \"/\"\n";

    fn code(text: &str) -> &'static str {
        parse_sitemap(text).expect_err("rejected").code()
    }

    // frob:tests crates/crunk-spec/src/ia.rs::parse_sitemap
    // frob:tests crates/crunk-spec/src/ia.rs::Sitemap.depth
    #[test]
    fn a_good_sitemap_parses_and_measures_depth() {
        let map = parse_sitemap(GOOD).expect("parses");
        assert_eq!(map.depth(map.page("/a").expect("a")), 1);
        assert_eq!(map.depth_limit(), DEFAULT_MAX_DEPTH);
        assert!(map.reachable().contains("/a"));
    }

    // frob:tests crates/crunk-spec/src/ia.rs::parse_sitemap
    // frob:tests crates/crunk-spec/src/ia.rs::IaFileError.code
    #[test]
    fn bad_sitemaps_get_a_code_including_a_parent_cycle() {
        assert_eq!(code("x = 1"), "E-IA-PARSE");
        assert_eq!(
            code("[[pages]]\nroute = \"a\"\nlabel = \"A\"\n"),
            "E-IA-FIELD"
        );
        assert_eq!(
            code("[[pages]]\nroute = \"/a\"\nlabel = \" \"\n"),
            "E-IA-FIELD"
        );
        let dup =
            "[[pages]]\nroute = \"/a\"\nlabel = \"A\"\n[[pages]]\nroute = \"/a\"\nlabel = \"B\"\n";
        assert_eq!(code(dup), "E-IA-DUP-ROUTE");
        let orphan = "[[pages]]\nroute = \"/a\"\nlabel = \"A\"\nparent = \"/z\"\n";
        assert_eq!(code(orphan), "E-IA-PARENT");
        let cycle = "[[pages]]\nroute = \"/a\"\nlabel = \"A\"\nparent = \"/b\"\n[[pages]]\nroute = \"/b\"\nlabel = \"B\"\nparent = \"/a\"\n";
        assert_eq!(code(cycle), "E-IA-CYCLE");
    }

    // frob:tests crates/crunk-spec/src/ia.rs::route_shape
    #[test]
    fn dynamic_segments_share_one_shape() {
        assert_eq!(route_shape("/u/:id"), route_shape("/u/[name]"));
        assert_eq!(route_shape("/u/{x}/"), "/u/{}");
        assert_ne!(route_shape("/u/:id"), route_shape("/u"));
        assert_eq!(route_shape("/"), "/");
    }

    // frob:tests crates/crunk-spec/src/ia.rs::Sitemap.reachable
    #[test]
    fn links_extend_reachability_and_orphans_stay_out() {
        let text = "[[pages]]\nroute = \"/\"\nlabel = \"H\"\nlinks = [\"/l\"]\n[[pages]]\nroute = \"/l\"\nlabel = \"L\"\n[[pages]]\nroute = \"/o\"\nlabel = \"O\"\n";
        let map = parse_sitemap(text).expect("parses");
        let r = map.reachable();
        assert!(r.contains("/l") && !r.contains("/o"));
    }

    // frob:tests crates/crunk-spec/src/ia.rs::parse_content_model
    #[test]
    fn content_model_rejects_a_repeated_type() {
        let ok = parse_content_model("[[types]]\nname = \"post\"\nfields = [\"title\"]\n");
        assert_eq!(ok.expect("parses").types.len(), 1);
        let dup = "[[types]]\nname = \"a\"\n[[types]]\nname = \"a\"\n";
        assert_eq!(
            parse_content_model(dup).expect_err("dup").code(),
            "E-IA-DUP-TYPE"
        );
    }
}
