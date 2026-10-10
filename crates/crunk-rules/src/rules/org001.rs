//! ORG001: a `.css` file under `css_root` that sits in no declared `[org] buckets` directory (port
//! of `crunk/rules/_org.py` `org001`). Silent under the `utility-first` model, which has no bucket
//! placement to enforce. Organisation findings describe the file, so they are never waivable.

// frob:ticket 01M43ATBPPR5QCY0CSPPTNEDQ0

use crunk_spec::table::OrgModel;
use gob_rules::{Measured, Out, RepoRule, rule};

use crate::host::{CrunkHost, missing_inputs};
use crate::sheets::{examined_sheets, site_path};

/// A stylesheet outside every declared bucket.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "ORG001",
    slug = "stylesheet-outside-buckets",
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
pub struct Org001;

impl<P: ?Sized + CrunkHost> RepoRule<P> for Org001 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles)) = (host.spec(), host.styles()) else {
            return;
        };
        for stray in &styles.strays {
            let path = site_path(spec, stray);
            tracing::debug!(%path, "ORG001: stray stylesheet");
            out.fire_in(
                &path,
                0,
                format!("{path} is outside every declared org bucket"),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        if let Some(why) = missing_inputs(host) {
            return Some(why);
        }
        host.spec()
            .is_some_and(|spec| spec.org.model == OrgModel::UtilityFirst)
            .then(|| "[org] model is utility-first, which has no bucket placement".to_owned())
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for Org001 {
    fn subjects(&self, host: &P) -> usize {
        host.styles().map_or(0, examined_sheets)
    }
}
