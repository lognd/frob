//! ORG003: in `components/<name>.css` every class must be `<name>`, `<name>__*` or `<name>--*` (port
//! of `crunk/rules/_org.py` `org003`). Silent under the `utility-first` model and when
//! `[org] component_prefix` is off.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use crunk_ingest::Bucket;
use crunk_spec::table::OrgModel;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::org::carries_prefix;
use crate::sheets::{examined_sheets, line_offset, site_path};

/// A component stylesheet class that does not carry the component name.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG003",
    slug = "component-prefix",
    severity = Error,
    polarity = Pplus,
    must_measure = true,
    scope = Repo,
    fix = Manual,
    applies = universal(needs = [Style], min_fidelity = F1),
    host = CrunkHost,
    version = 1,
    since = "0.532.0",
)]
pub struct Org003;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org003 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        for sheet in &styles.sheets {
            let (Some(Bucket::Components), Some(component)) = (sheet.bucket, &sheet.component)
            else {
                continue;
            };
            let path = site_path(spec, &sheet.path);
            for selector in &sheet.class_selectors {
                if carries_prefix(&selector.name, component) {
                    continue;
                }
                tracing::debug!(%path, line = selector.line, name = %selector.name, "ORG003: missing prefix");
                out.fire_in(
                    &path,
                    line_offset(&sheet.source, selector.line),
                    format!(
                        "class '{}' does not carry the component prefix '{component}'",
                        selector.name
                    ),
                );
            }
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if let Some(why) = missing_inputs(host) {
            return Some(why);
        }
        let spec = host.spec()?;
        if spec.org.model == OrgModel::UtilityFirst {
            return Some("[org] model is utility-first, which ignores buckets".to_owned());
        }
        (!spec.org.component_prefix).then(|| "[org] component_prefix is off".to_owned())
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Org003 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
