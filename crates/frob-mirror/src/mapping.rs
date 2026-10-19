//! The materialized field mapping (mirror.md 2, 2.1): validated at load, applied to projections.
//!
//! Every mappable projection field must be routed or explicitly dropped, so nothing
//! disappears silently; routes are checked against the adapter's [`Capabilities`].

// frob:ticket 01M3ZX83E71BKE3PHY83G2NT7K

use std::collections::BTreeMap;

use tracing::{debug, trace, warn};

use crate::adapter::Capabilities;
use crate::config::{ConfigError, MAPPING_VERSION, MappingConfig, Route};
use crate::projection::IssueProjection;

/// Projection fields a mapping must account for (identity, title, sections, relations and
/// provenance have fixed treatment and are not mappable).
pub const MAPPABLE: &[&str] = &[
    "ticket_type",
    "labels",
    "priority",
    "points",
    "milestone",
    "epic",
    "category",
    "outcome",
    "owner",
    "assignee",
];

/// The tracker-side changes a projection plans under a mapping.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct PlannedOps {
    /// Labels to carry.
    pub labels: Vec<String>,
    /// Custom field name to value.
    pub fields: BTreeMap<String, String>,
    /// Issue type, if routed.
    pub issue_type: Option<String>,
    /// State inputs (`category`, `outcome`) to value, for the adapter's state mapping.
    pub state: BTreeMap<String, String>,
}

/// A validated mapping.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Mapping {
    routes: BTreeMap<String, Route>,
}

fn check_route(field: &str, route: &Route, caps: &Capabilities) -> Result<(), ConfigError> {
    let bad = |reason: &str| ConfigError::Unsupported {
        field: field.to_owned(),
        reason: reason.to_owned(),
    };
    match route {
        Route::Label { .. } if matches!(field, "category" | "outcome") => {
            Err(bad("state fields route to `state` or `drop`"))
        }
        Route::Field { .. } if !caps.custom_fields => Err(bad("tracker has no custom fields")),
        Route::Drop | Route::Label { .. } | Route::Field { .. } => Ok(()),
        Route::IssueType if field == "ticket_type" => Ok(()),
        Route::IssueType => Err(bad("only ticket_type routes to an issue type")),
        Route::State if matches!(field, "category" | "outcome") => Ok(()),
        Route::State => Err(bad("only category and outcome route to state")),
    }
}

impl Mapping {
    /// Validate `cfg` against the projection fields and `caps`; the first problem is returned.
    ///
    /// # Errors
    /// A [`ConfigError`] for a bad version, unknown or unrouted field, or unsupported route.
    pub fn load(cfg: &MappingConfig, caps: &Capabilities) -> Result<Self, ConfigError> {
        if cfg.version != MAPPING_VERSION {
            warn!(found = cfg.version, "mapping version unsupported");
            return Err(ConfigError::Version { found: cfg.version });
        }
        if let Some(unknown) = cfg.fields.keys().find(|k| !MAPPABLE.contains(&k.as_str())) {
            return Err(ConfigError::UnknownField(unknown.clone()));
        }
        for field in MAPPABLE {
            match cfg.fields.get(*field) {
                None => {
                    warn!(field, "projection field neither routed nor dropped");
                    return Err(ConfigError::Unrouted((*field).to_owned()));
                }
                Some(route) => check_route(field, route, caps)?,
            }
        }
        debug!(routes = cfg.fields.len(), "mapping loaded");
        Ok(Self {
            routes: cfg.fields.clone(),
        })
    }

    /// Plan the tracker changes for `p`; absent (or withheld) values plan nothing.
    pub fn apply(&self, p: &IssueProjection) -> PlannedOps {
        let c = &p.classification;
        let mut values: Vec<(&str, Vec<String>)> = vec![
            ("ticket_type", c.ticket_type.iter().cloned().collect()),
            ("labels", c.labels.clone().unwrap_or_default()),
            ("priority", c.priority.iter().cloned().collect()),
            ("points", c.points.iter().map(u32::to_string).collect()),
            ("milestone", c.milestone.iter().cloned().collect()),
            ("epic", c.epic.iter().cloned().collect()),
            ("category", vec![snake(&p.state.category)]),
            ("outcome", p.state.outcome.iter().map(snake).collect()),
            ("owner", p.people.owner.iter().cloned().collect()),
            ("assignee", p.people.assignee.iter().cloned().collect()),
        ];
        let mut ops = PlannedOps::default();
        for (field, vals) in values.drain(..) {
            let Some(route) = self.routes.get(field) else {
                continue;
            };
            for v in vals {
                trace!(field, value = %v, "applying route");
                match route {
                    Route::Drop => {}
                    Route::Label { prefix } => ops.labels.push(format!("{prefix}{v}")),
                    Route::Field { name } => {
                        ops.fields.insert(name.clone(), v);
                    }
                    Route::IssueType => ops.issue_type = Some(v),
                    Route::State => {
                        ops.state.insert(field.to_owned(), v);
                    }
                }
            }
        }
        ops
    }
}

fn snake<T: serde::Serialize>(v: &T) -> String {
    serde_json::to_value(v)
        .ok()
        .and_then(|j| j.as_str().map(str::to_owned))
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::adapter::{HistoryRetention, MarkdownDialect, StateReasons};
    use crate::config::parse;
    use crate::projection::{Category, Classification, Identity, People, Provenance, State};

    fn caps(custom: bool) -> Capabilities {
        Capabilities {
            native_sub_issues: true,
            native_links: true,
            custom_fields: custom,
            state_reasons: StateReasons::Native,
            history_retention: HistoryRetention::Forever,
            markdown: MarkdownDialect::Github,
        }
    }

    fn doc(skip: &str, priority: &str) -> String {
        let mut f: Vec<String> = Vec::new();
        for m in MAPPABLE {
            if *m == skip {
                continue;
            }
            let r = match *m {
                "priority" => priority.to_owned(),
                "category" | "outcome" => r#"{"to":"state"}"#.to_owned(),
                "ticket_type" => r#"{"to":"issue_type"}"#.to_owned(),
                _ => r#"{"to":"drop"}"#.to_owned(),
            };
            f.push(format!("\"{m}\":{r}"));
        }
        format!(r#"{{"version":1,"fields":{{{}}}}}"#, f.join(","))
    }

    fn projection() -> IssueProjection {
        IssueProjection {
            identity: Identity {
                ulid: "U".into(),
                handle: "~U".into(),
                aliases: vec![],
                repository: "r".into(),
                ledger_path: "p".into(),
            },
            title: "t".into(),
            sections: vec![],
            classification: Classification {
                priority: Some("high".into()),
                ..Default::default()
            },
            state: State {
                category: Category::Todo,
                outcome: None,
                reason: None,
            },
            relations: vec![],
            people: People::default(),
            provenance: Provenance {
                last_event: "e".into(),
                render_digest: "d".into(),
                producer_version: "v".into(),
            },
            private: vec![],
        }
    }

    // frob:tests load
    #[test]
    fn unrouted_priority_is_a_config_error_naming_it() {
        let cfg = parse(&doc("priority", "")).unwrap();
        let err = Mapping::load(&cfg, &caps(true)).unwrap_err();
        assert_eq!(err, ConfigError::Unrouted("priority".into()));
        assert!(err.to_string().contains("priority"));
    }

    // frob:tests load
    #[test]
    fn capability_and_version_and_unknown_are_checked() {
        let field = r#"{"to":"field","name":"Prio"}"#;
        let cfg = parse(&doc("", field)).unwrap();
        assert!(matches!(
            Mapping::load(&cfg, &caps(false)),
            Err(ConfigError::Unsupported { .. })
        ));
        assert!(Mapping::load(&cfg, &caps(true)).is_ok());
        let mut v = cfg.clone();
        v.version = 9;
        assert_eq!(
            Mapping::load(&v, &caps(true)),
            Err(ConfigError::Version { found: 9 })
        );
        let mut u = cfg;
        u.fields.insert("bogus".into(), Route::Drop);
        assert!(matches!(
            Mapping::load(&u, &caps(true)),
            Err(ConfigError::UnknownField(_))
        ));
        assert!(matches!(parse("{"), Err(ConfigError::Malformed(_))));
    }

    // frob:tests apply
    #[test]
    fn priority_routed_to_label_appears_in_planned_operation() {
        let cfg = parse(&doc("", r#"{"to":"label","prefix":"priority:"}"#)).unwrap();
        let m = Mapping::load(&cfg, &caps(false)).unwrap();
        let ops = m.apply(&projection());
        assert_eq!(ops.labels, ["priority:high"]);
        assert_eq!(ops.state.get("category").map(String::as_str), Some("todo"));
    }
}
