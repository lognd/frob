//! Cross-field validation of the TOML-shaped tables, one function per table.
//!
//! Every failure is a [`Problem`]: a path into the document plus a message, which the loader
//! turns into a located [`crate::SpecError`]. Nothing here touches the filesystem.

// frob:ticket 01M43ARX764095Q4VWABWXXV5H

use std::collections::{BTreeSet, HashMap, HashSet};

use crunk_values::Color;
use indexmap::IndexMap;

use crate::catalog::{
    CONTRAST_AA_FLOOR, DEFAULT_BASE_REQUIRED, RENDERER_IDS, Severity, TAILWIND_V3_BREAKPOINTS,
    is_rule_id, rule_ids,
};
use crate::dynamic::Dyn;
use crate::model::{
    BreakpointsConfig, CommandRendererParams, LintConfig, PlatformConfig, RendererParams, RolePair,
    TokensConfig, WebRendererParams,
};
use crate::table::{
    Action, RawPlatform, RawTokens, RosterEntry, ScalesConfig, ScreenConfig, ScreenState,
    TypographyConfig,
};

/// One segment of a path into the document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) enum Seg {
    /// A table key.
    Key(String),
    /// An array or array-of-tables index.
    Idx(usize),
}

/// A validation failure: where, what, and for an unknown key the offending key and a suggestion.
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct Problem {
    /// Path to the offending key or table.
    pub path: Vec<Seg>,
    /// What is wrong, already prefixed with the `[section].key` rendering of `path`.
    pub detail: String,
    /// The offending key of an unknown-key problem.
    pub key: Option<String>,
    /// Nearest valid key.
    pub suggestion: Option<String>,
}

pub(crate) type Res<T> = Result<T, Problem>;

/// Build a path of table keys.
pub(crate) fn keys(parts: &[&str]) -> Vec<Seg> {
    parts.iter().map(|p| Seg::Key((*p).to_owned())).collect()
}

fn extend(path: &[Seg], more: Vec<Seg>) -> Vec<Seg> {
    let mut out = path.to_vec();
    out.extend(more);
    out
}

fn key(name: &str) -> Seg {
    Seg::Key(name.to_owned())
}

/// Render `path` as `[a.b].c` (all but the last segment bracketed), indices as `[0]`.
fn render_path(path: &[Seg]) -> String {
    fn join(segs: &[Seg]) -> String {
        let mut out = String::new();
        for seg in segs {
            match seg {
                Seg::Key(k) if out.is_empty() => out.push_str(k),
                Seg::Key(k) => {
                    out.push('.');
                    out.push_str(k);
                }
                Seg::Idx(i) => out.push_str(&format!("[{i}]")),
            }
        }
        out
    }
    match path.split_last() {
        None => String::new(),
        Some((Seg::Key(last), head)) if !head.is_empty() => {
            format!("[{}].{last}", join(head))
        }
        Some(_) => format!("[{}]", join(path)),
    }
}

fn fail(path: Vec<Seg>, msg: impl AsRef<str>) -> Problem {
    Problem {
        detail: format!("{}: {}", render_path(&path), msg.as_ref()),
        path,
        key: None,
        suggestion: None,
    }
}

/// The candidate nearest to `word` by edit distance, if within a sane bound.
pub(crate) fn nearest<'a>(
    word: &str,
    candidates: impl IntoIterator<Item = &'a str>,
) -> Option<String> {
    let limit = (word.len() / 2).max(2);
    candidates
        .into_iter()
        .map(|c| (strsim::levenshtein(word, c), c))
        .filter(|(d, _)| *d <= limit)
        .min_by_key(|(d, _)| *d)
        .map(|(_, c)| c.to_owned())
}

fn ascending(values: &[f64]) -> bool {
    values.windows(2).all(|w| w[0] < w[1])
}

fn check_scale(table: &str, name: &str, values: &[f64], required: bool) -> Res<()> {
    let path = keys(&[table, name]);
    if required && values.is_empty() {
        return Err(fail(path, "list should have at least 1 item"));
    }
    if !ascending(values) {
        return Err(fail(
            path,
            format!("scale is not strictly ascending: {values:?}"),
        ));
    }
    Ok(())
}

/// `[scales]`: non-empty strictly ascending required lists, ascending optional ones.
pub(crate) fn scales(s: &ScalesConfig) -> Res<()> {
    check_scale("scales", "spacing", &s.spacing, true)?;
    check_scale("scales", "font_sizes", &s.font_sizes, true)?;
    check_scale("scales", "radii", &s.radii, false)?;
    check_scale("scales", "sizes", &s.sizes, false)
}

/// `[typography]`: non-empty lists, and stacks of declared families only.
pub(crate) fn typography(t: &TypographyConfig) -> Res<()> {
    if t.families.is_empty() {
        return Err(fail(
            keys(&["typography", "families"]),
            "list should have at least 1 item",
        ));
    }
    if t.weights.is_empty() {
        return Err(fail(
            keys(&["typography", "weights"]),
            "list should have at least 1 item",
        ));
    }
    let declared: HashSet<String> = t.families.iter().map(|f| f.to_lowercase()).collect();
    for (name, members) in &t.stacks {
        let path = keys(&["typography", "stacks", name]);
        if members.is_empty() {
            return Err(fail(path, format!("stack `{name}` must not be empty")));
        }
        for member in members {
            if !declared.contains(&member.to_lowercase()) {
                return Err(fail(
                    path,
                    format!(
                        "stack `{name}` member `{member}` is not in declared families {:?}",
                        t.families
                    ),
                ));
            }
        }
    }
    Ok(())
}

/// `[org]`: at least one bucket.
pub(crate) fn org(o: &crate::table::OrgConfig) -> Res<()> {
    if o.buckets.is_empty() {
        return Err(fail(
            keys(&["org", "buckets"]),
            "list should have at least 1 item",
        ));
    }
    Ok(())
}

fn valid_prefix(value: &str) -> bool {
    let mut chars = value.chars();
    chars.next().is_some_and(|c| c.is_ascii_lowercase())
        && chars.all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-')
}

fn check_prefix(name: &str, value: &str, allow_empty: bool) -> Res<()> {
    let path = keys(&["tokens", "prefixes", name]);
    if value.is_empty() {
        return if allow_empty {
            Ok(())
        } else {
            Err(fail(path, "prefix must not be empty"))
        };
    }
    if valid_prefix(value) {
        Ok(())
    } else {
        Err(fail(
            path,
            format!("prefix must match [a-z][a-z0-9-]*, got {value:?}"),
        ))
    }
}

fn check_header(value: &str) -> Res<()> {
    let path = keys(&["tokens", "header"]);
    if value.is_empty() {
        return Ok(());
    }
    if !value.starts_with("/*") {
        return Err(fail(path, "header must start with '/*'"));
    }
    if !value.ends_with("*/") {
        return Err(fail(path, "header must end with '*/'"));
    }
    if value[..value.len() - 2].contains("*/") {
        return Err(fail(path, "header must not contain an interior '*/'"));
    }
    Ok(())
}

/// `[tokens]`: validate prefixes and header, flatten into the naming config.
pub(crate) fn tokens(raw: &RawTokens) -> Res<TokensConfig> {
    let p = &raw.prefixes;
    check_prefix("color", &p.color, true)?;
    check_prefix("space", &p.space, false)?;
    check_prefix("font_size", &p.font_size, false)?;
    check_prefix("radius", &p.radius, false)?;
    check_prefix("layer", &p.layer, true)?;
    check_prefix("font_family", &p.font_family, true)?;
    check_prefix("size", &p.size, false)?;
    check_header(&raw.header)?;
    Ok(TokensConfig {
        color: p.color.clone(),
        space: p.space.clone(),
        font_size: p.font_size.clone(),
        radius: p.radius.clone(),
        layer: p.layer.clone(),
        font_family: p.font_family.clone(),
        size: p.size.clone(),
        header: raw.header.clone(),
        json_file: raw.json_file.clone(),
    })
}

/// The parsed colors and the raw `roles` subtable of `[palette]`.
pub(crate) type PaletteParts = (IndexMap<String, Color>, IndexMap<String, Dyn>);

/// `[palette]`: split off `roles` and parse every color literal.
pub(crate) fn palette(raw: &IndexMap<String, Dyn>) -> Res<PaletteParts> {
    let mut colors = IndexMap::new();
    let mut roles = IndexMap::new();
    for (name, value) in raw {
        if name == "roles" {
            match value {
                Dyn::Table(t) => roles.clone_from(t),
                _ => return Err(fail(keys(&["palette", "roles"]), "must be a table")),
            }
            continue;
        }
        let path = keys(&["palette", name]);
        let Dyn::Str(literal) = value else {
            return Err(fail(path, "color literal must be a string"));
        };
        match Color::parse(literal) {
            Ok(color) => {
                colors.insert(name.clone(), color);
            }
            Err(_) => {
                return Err(fail(path, format!("unparseable color literal {literal:?}")));
            }
        }
    }
    Ok((colors, roles))
}

fn pair_names(path: &[Seg], value: &Dyn) -> Res<(String, String)> {
    let Dyn::Array(items) = value else {
        return Err(fail(
            path.to_vec(),
            "must be a [foreground, background] pair",
        ));
    };
    if items.len() != 2 {
        return Err(fail(
            path.to_vec(),
            "must be a [foreground, background] pair",
        ));
    }
    match (&items[0], &items[1]) {
        (Dyn::Str(fg), Dyn::Str(bg)) => Ok((fg.clone(), bg.clone())),
        _ => Err(fail(path.to_vec(), "names must be strings")),
    }
}

/// `[palette.roles]`: pairs of declared palette names with an optional contrast floor.
pub(crate) fn roles(
    raw: &IndexMap<String, Dyn>,
    palette: &IndexMap<String, Color>,
) -> Res<IndexMap<String, RolePair>> {
    let mut out = IndexMap::new();
    for (name, value) in raw {
        let path = keys(&["palette", "roles", name]);
        let (pair, floor) = match value {
            Dyn::Array(_) => (pair_names(&path, value)?, CONTRAST_AA_FLOOR),
            Dyn::Table(t) => {
                if let Some(unknown) = t.keys().find(|k| *k != "pair" && *k != "floor") {
                    let mut p = fail(
                        extend(&path, vec![key(unknown)]),
                        format!("unknown key `{unknown}`"),
                    );
                    p.key = Some(unknown.clone());
                    p.suggestion = nearest(unknown, ["pair", "floor"]);
                    return Err(p);
                }
                let Some(pair_value) = t.get("pair") else {
                    return Err(fail(path, "table form needs `pair`"));
                };
                let pair = pair_names(&extend(&path, vec![key("pair")]), pair_value)?;
                let floor = match t.get("floor") {
                    None => CONTRAST_AA_FLOOR,
                    Some(v) => v.as_number().ok_or_else(|| {
                        fail(extend(&path, vec![key("floor")]), "floor must be a number")
                    })?,
                };
                (pair, floor)
            }
            _ => {
                return Err(fail(
                    path,
                    "must be a [foreground, background] pair or a { pair, floor } table",
                ));
            }
        };
        for reference in [&pair.0, &pair.1] {
            if !palette.contains_key(reference) {
                return Err(fail(
                    path,
                    format!("`{reference}` is not a declared palette name"),
                ));
            }
        }
        if floor <= 0.0 {
            return Err(fail(path, "floor must be > 0"));
        }
        out.insert(
            name.clone(),
            RolePair {
                foreground: pair.0,
                background: pair.1,
                floor,
            },
        );
    }
    Ok(out)
}

/// A TOML number (integer or float) at `path`.
fn number(path: Vec<Seg>, value: &Dyn) -> Res<f64> {
    value
        .as_number()
        .ok_or_else(|| fail(path, format!("must be a number, got {}", value.type_name())))
}

/// `[lint]`: rule severities plus the two tolerances, defaulting when absent.
pub(crate) fn lint(raw: Option<&IndexMap<String, Dyn>>) -> Res<LintConfig> {
    let mut out = LintConfig::default();
    let Some(raw) = raw else {
        return Ok(out);
    };
    for (name, value) in raw {
        let path = keys(&["lint", name]);
        match name.as_str() {
            "fix_tolerance" => {
                let v = number(path.clone(), value)?;
                if !(v > 0.0 && v < 1.0) {
                    return Err(fail(
                        path,
                        "fix_tolerance must be greater than 0 and less than 1",
                    ));
                }
                out.fix_tolerance = v;
            }
            "color_tolerance" => {
                let v = number(path.clone(), value)?;
                if v <= 0.0 {
                    return Err(fail(path, "color_tolerance must be greater than 0"));
                }
                out.color_tolerance = v;
            }
            id if is_rule_id(id) => {
                let severity = match value {
                    Dyn::Str(s) => Severity::parse(s),
                    _ => None,
                };
                let Some(severity) = severity else {
                    return Err(fail(
                        path,
                        format!("severity must be error/warn/off, got {}", describe(value)),
                    ));
                };
                out.rules.insert(id.to_owned(), severity);
            }
            unknown => {
                let ids = rule_ids();
                let candidates = ids
                    .iter()
                    .map(String::as_str)
                    .chain(["fix_tolerance", "color_tolerance"]);
                let mut p = fail(path, "unknown rule id");
                p.key = Some(unknown.to_owned());
                p.suggestion = nearest(unknown, candidates);
                return Err(p);
            }
        }
    }
    Ok(out)
}

fn describe(value: &Dyn) -> String {
    match value {
        Dyn::Str(s) => format!("{s:?}"),
        Dyn::Int(i) => i.to_string(),
        Dyn::Float(f) => f.to_string(),
        Dyn::Bool(b) => b.to_string(),
        other => other.type_name().to_owned(),
    }
}

/// `[breakpoints]`: declared wins, then the Tailwind v3 defaults, then off.
pub(crate) fn breakpoints(
    raw: Option<&IndexMap<String, Dyn>>,
    tailwind_declared: bool,
) -> Res<BreakpointsConfig> {
    let Some(raw) = raw else {
        if tailwind_declared {
            tracing::info!("breakpoints absent and tailwind declared: using v3 defaults");
            return Ok(BreakpointsConfig {
                points: TAILWIND_V3_BREAKPOINTS
                    .iter()
                    .map(|(k, v)| ((*k).to_owned(), *v))
                    .collect(),
                base_required: DEFAULT_BASE_REQUIRED
                    .iter()
                    .map(|s| (*s).to_owned())
                    .collect(),
            });
        }
        tracing::info!("breakpoints absent and no tailwind: BP rules off");
        return Ok(BreakpointsConfig::default());
    };
    let mut out = BreakpointsConfig {
        points: IndexMap::new(),
        base_required: DEFAULT_BASE_REQUIRED
            .iter()
            .map(|s| (*s).to_owned())
            .collect(),
    };
    for (name, value) in raw {
        let path = keys(&["breakpoints", name]);
        if name == "base_required" {
            let ok = match value {
                Dyn::Array(items) => items
                    .iter()
                    .map(|i| match i {
                        Dyn::Str(s) => Some(s.clone()),
                        _ => None,
                    })
                    .collect::<Option<Vec<_>>>(),
                _ => None,
            };
            let Some(list) = ok else {
                return Err(fail(path, "must be a list of strings"));
            };
            out.base_required = list;
        } else if let Dyn::Int(px) = value {
            out.points.insert(name.clone(), *px);
        } else {
            return Err(fail(path, "must be an integer px value"));
        }
    }
    Ok(out)
}

fn web_only(p: &RawPlatform) -> Vec<&'static str> {
    let mut v = Vec::new();
    let mut add = |present: bool, name| {
        if present {
            v.push(name);
        }
    };
    add(p.engine.is_some(), "engine");
    add(p.viewport.is_some(), "viewport");
    add(p.device_scale.is_some(), "device_scale");
    add(p.media.is_some(), "media");
    add(p.locale.is_some(), "locale");
    add(p.settle_ms.is_some(), "settle_ms");
    add(p.init_scripts.is_some(), "init_scripts");
    add(p.java_script_enabled.is_some(), "java_script_enabled");
    add(p.cpu_throttle.is_some(), "cpu_throttle");
    add(p.network_throttle.is_some(), "network_throttle");
    add(p.base_url.is_some(), "base_url");
    v
}

fn command_only(p: &RawPlatform) -> Vec<&'static str> {
    let mut v = Vec::new();
    if p.command.is_some() {
        v.push("command");
    }
    if p.cwd.is_some() {
        v.push("cwd");
    }
    if p.env.is_some() {
        v.push("env");
    }
    v
}

fn web_params(p: &RawPlatform, at: &[Seg]) -> Res<WebRendererParams> {
    let field = |name: &str| extend(at, vec![key(name)]);
    let Some(engine) = p.engine else {
        return Err(fail(at.to_vec(), "renderer `web` requires `engine`"));
    };
    let Some(viewport) = p.viewport.clone() else {
        return Err(fail(at.to_vec(), "renderer `web` requires `viewport`"));
    };
    if viewport.width == 0 || viewport.height == 0 {
        return Err(fail(
            extend(at, vec![key("viewport")]),
            "viewport width and height must be greater than 0",
        ));
    }
    let device_scale = p.device_scale.unwrap_or(1.0);
    if device_scale <= 0.0 {
        return Err(fail(
            field("device_scale"),
            "device_scale must be greater than 0",
        ));
    }
    if let Some(cpu) = p.cpu_throttle
        && cpu < 1.0
    {
        return Err(fail(
            field("cpu_throttle"),
            "cpu_throttle must be at least 1",
        ));
    }
    if let Some(net) = &p.network_throttle {
        let path = field("network_throttle");
        if net.download <= 0.0 || net.upload <= 0.0 {
            return Err(fail(path, "download and upload must be greater than 0"));
        }
        if net.latency < 0.0 {
            return Err(fail(path, "latency must be at least 0"));
        }
    }
    Ok(WebRendererParams {
        engine,
        viewport,
        device_scale,
        media: p.media.clone().unwrap_or_default(),
        locale: p.locale.clone(),
        settle_ms: p.settle_ms.unwrap_or(500),
        init_scripts: p.init_scripts.clone().unwrap_or_default(),
        java_script_enabled: p.java_script_enabled.unwrap_or(true),
        cpu_throttle: p.cpu_throttle,
        network_throttle: p.network_throttle.clone(),
        base_url: p.base_url.clone(),
    })
}

fn command_params(p: &RawPlatform, at: &[Seg]) -> Res<CommandRendererParams> {
    let Some(command) = p.command.clone() else {
        return Err(fail(at.to_vec(), "renderer `command` requires `command`"));
    };
    if command.is_empty() {
        return Err(fail(
            extend(at, vec![key("command")]),
            "command must not be empty",
        ));
    }
    Ok(CommandRendererParams {
        command,
        cwd: p.cwd.clone(),
        env: p.env.clone().unwrap_or_default(),
    })
}

/// `[[platform]]`: unique ids, known renderers, renderer-specific params.
pub(crate) fn platforms(raw: &[RawPlatform]) -> Res<IndexMap<String, PlatformConfig>> {
    let mut out: IndexMap<String, PlatformConfig> = IndexMap::new();
    for (i, p) in raw.iter().enumerate() {
        let at = vec![key("platform"), Seg::Idx(i)];
        if out.contains_key(&p.id) {
            return Err(fail(
                extend(&at, vec![key("id")]),
                format!("duplicate platform id `{}`", p.id),
            ));
        }
        if !RENDERER_IDS.contains(&p.renderer.as_str()) {
            let mut problem = fail(
                extend(&at, vec![key("renderer")]),
                format!(
                    "unknown renderer id `{}`, expected one of {RENDERER_IDS:?}",
                    p.renderer
                ),
            );
            problem.suggestion = nearest(&p.renderer, RENDERER_IDS.iter().copied());
            return Err(problem);
        }
        let (foreign, other) = if p.renderer == "web" {
            (command_only(p), "web")
        } else {
            (web_only(p), "command")
        };
        if let Some(name) = foreign.first() {
            let mut problem = fail(
                extend(&at, vec![key(name)]),
                format!("`{name}` is not a key of the `{other}` renderer"),
            );
            problem.key = Some((*name).to_owned());
            return Err(problem);
        }
        let params = if p.renderer == "web" {
            RendererParams::Web(web_params(p, &at)?)
        } else {
            RendererParams::Command(command_params(p, &at)?)
        };
        out.insert(
            p.id.clone(),
            PlatformConfig {
                id: p.id.clone(),
                renderer: p.renderer.clone(),
                params,
                tags: p.tags.clone(),
            },
        );
    }
    Ok(out)
}

/// `[[session]]` and `[[mock_set]]`: unique ids.
pub(crate) fn rosters(table: &str, raw: &[RosterEntry]) -> Res<IndexMap<String, RosterEntry>> {
    let mut out = IndexMap::new();
    for (i, entry) in raw.iter().enumerate() {
        if out.contains_key(&entry.id) {
            return Err(fail(
                vec![key(table), Seg::Idx(i), key("id")],
                format!("duplicate {table} id `{}`", entry.id),
            ));
        }
        out.insert(entry.id.clone(), entry.clone());
    }
    Ok(out)
}

/// Platform ids and tag index the screens resolve `applies_to` against.
pub(crate) struct Platforms<'a> {
    ids: HashSet<&'a str>,
    tags: HashMap<&'a str, BTreeSet<&'a str>>,
}

impl<'a> Platforms<'a> {
    /// Index the declared platforms by id and by tag.
    pub(crate) fn new(platforms: &'a IndexMap<String, PlatformConfig>) -> Self {
        let mut tags: HashMap<&str, BTreeSet<&str>> = HashMap::new();
        for p in platforms.values() {
            for tag in &p.tags {
                tags.entry(tag.as_str()).or_default().insert(p.id.as_str());
            }
        }
        Self {
            ids: platforms.keys().map(String::as_str).collect(),
            tags,
        }
    }

    /// Resolve an `applies_to` list to the platform ids it names; `None` is every platform.
    fn resolve(&self, names: Option<&Vec<String>>, at: &[Seg]) -> Res<Option<BTreeSet<&'a str>>> {
        let Some(names) = names else {
            return Ok(None);
        };
        let mut out = BTreeSet::new();
        for (i, name) in names.iter().enumerate() {
            let path = extend(at, vec![Seg::Idx(i)]);
            if let Some(tag) = name.strip_prefix("tag:") {
                let Some(ids) = self.tags.get(tag) else {
                    return Err(fail(path, format!("unknown tag `{name}`")));
                };
                out.extend(ids.iter().copied());
            } else if let Some(id) = self.ids.get(name.as_str()) {
                out.insert(*id);
            } else {
                return Err(fail(path, format!("undeclared platform id `{name}`")));
            }
        }
        Ok(Some(out))
    }
}

fn non_empty(path: Vec<Seg>, value: &str, what: &str) -> Res<()> {
    if value.is_empty() {
        Err(fail(path, format!("{what} must not be empty")))
    } else {
        Ok(())
    }
}

fn action(a: &Action, at: &[Seg]) -> Res<()> {
    let field = |name: &str| extend(at, vec![key(name)]);
    match a {
        Action::Click { selector }
        | Action::Hover { selector }
        | Action::Focus { selector }
        | Action::Fill { selector, .. } => non_empty(field("selector"), selector, "selector"),
        Action::Press { selector, key } => {
            non_empty(field("selector"), selector, "selector")?;
            non_empty(field("key"), key, "key")
        }
        Action::WaitFor {
            selector,
            timeout_ms,
        } => {
            non_empty(field("selector"), selector, "selector")?;
            if *timeout_ms == Some(0) {
                return Err(fail(
                    field("timeout_ms"),
                    "timeout_ms must be greater than 0",
                ));
            }
            Ok(())
        }
    }
}

fn state_local(state: &ScreenState, at: &[Seg]) -> Res<()> {
    for (i, a) in state.actions.iter().enumerate() {
        action(a, &extend(at, vec![key("actions"), Seg::Idx(i)]))?;
    }
    for (i, n) in state.network.iter().enumerate() {
        let path = extend(at, vec![key("network"), Seg::Idx(i)]);
        non_empty(
            extend(&path, vec![key("url_pattern")]),
            &n.url_pattern,
            "url_pattern",
        )?;
        if let Some(status) = n.status
            && !(100..=599).contains(&status)
        {
            return Err(fail(
                extend(&path, vec![key("status")]),
                format!("status must be a valid HTTP status code, got {status}"),
            ));
        }
        if n.delay_ms == Some(0) {
            return Err(fail(
                extend(&path, vec![key("delay_ms")]),
                "delay_ms must be greater than 0",
            ));
        }
    }
    Ok(())
}

/// `[[screen]]`: unique ids, at least one state, and every cross-reference resolving.
pub(crate) fn screens(
    raw: &[ScreenConfig],
    platforms: &Platforms<'_>,
    sessions: &IndexMap<String, RosterEntry>,
    mock_sets: &IndexMap<String, RosterEntry>,
) -> Res<IndexMap<String, ScreenConfig>> {
    let mut out: IndexMap<String, ScreenConfig> = IndexMap::new();
    for (i, screen) in raw.iter().enumerate() {
        let at = vec![key("screen"), Seg::Idx(i)];
        if out.contains_key(&screen.id) {
            return Err(fail(
                extend(&at, vec![key("id")]),
                format!("duplicate screen id `{}`", screen.id),
            ));
        }
        if screen.states.is_empty() {
            return Err(fail(
                extend(&at, vec![key("states")]),
                "a screen needs at least one state",
            ));
        }
        let screen_platforms = platforms.resolve(
            screen.applies_to.as_ref(),
            &extend(&at, vec![key("applies_to")]),
        )?;
        let state_ids: HashSet<&str> = screen.states.iter().map(|s| s.id.as_str()).collect();
        for (j, state) in screen.states.iter().enumerate() {
            let sat = extend(&at, vec![key("states"), Seg::Idx(j)]);
            state_local(state, &sat)?;
            let state_platforms = platforms.resolve(
                state.applies_to.as_ref(),
                &extend(&sat, vec![key("applies_to")]),
            )?;
            if let (Some(sp), Some(scp)) = (&state_platforms, &screen_platforms)
                && !sp.is_subset(scp)
            {
                return Err(fail(
                    extend(&sat, vec![key("applies_to")]),
                    "not a subset of the screen's",
                ));
            }
            if let Some(id) = &state.session
                && !sessions.contains_key(id)
            {
                return Err(fail(
                    extend(&sat, vec![key("session")]),
                    format!("dangling session id `{id}`"),
                ));
            }
            if let Some(id) = &state.mock
                && !mock_sets.contains_key(id)
            {
                return Err(fail(
                    extend(&sat, vec![key("mock")]),
                    format!("dangling mock id `{id}`"),
                ));
            }
            if let Some(id) = &state.diff_against
                && !state_ids.contains(id.as_str())
            {
                return Err(fail(
                    extend(&sat, vec![key("diff_against")]),
                    format!("dangling sibling state id `{id}`"),
                ));
            }
        }
        out.insert(screen.id.clone(), screen.clone());
    }
    Ok(out)
}
