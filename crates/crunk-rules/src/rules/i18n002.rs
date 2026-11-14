//! I18N002: a project with a right-to-left locale styles with physical left/right properties or utilities, so the layout does not mirror. Off when the project has no content files.

// frob:ticket 01M5H5P5H1CSMP9Q3NF4RY4M26

use gob_rules::{Measured, Out, RepoRule, rule};

use crate::craft::ui_sheets;
use crate::host::{CrunkHost, content_subjects, missing_content_inputs};
use crate::i18n::{is_rtl_locale, logical_for_declaration, logical_for_utility};
use crate::sheets::{line_offset, site_path};

/// A physical left/right style in a project that ships a right-to-left locale.
#[derive(Debug, Clone, Copy, Default)]
#[rule(
    id = "I18N002",
    slug = "rtl-physical-direction",
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
pub struct I18n002;

impl<P: ?Sized + CrunkHost> RepoRule<P> for I18n002 {
    fn check(&self, host: &P, out: &mut Out<'_, Self>) {
        let (Some(spec), Some(styles), Some(facts)) = (host.spec(), host.styles(), host.content())
        else {
            return;
        };
        let Some(rtl) = facts
            .files
            .iter()
            .filter_map(|f| f.content.locale.as_deref())
            .find(|l| is_rtl_locale(l))
        else {
            tracing::debug!("I18N002: no right-to-left locale");
            return;
        };
        for sheet in ui_sheets(styles) {
            let path = site_path(spec, &sheet.path);
            let hit = sheet
                .declarations
                .iter()
                .find_map(|d| {
                    logical_for_declaration(&d.prop, &d.value).map(|logical| {
                        (d.line, format!("'{}: {}'", d.prop, d.value.trim()), logical)
                    })
                })
                .or_else(|| {
                    sheet.utilities.iter().find_map(|u| {
                        logical_for_utility(&u.name)
                            .map(|logical| (u.line, format!("'{}'", u.name), logical))
                    })
                });
            let Some((line, found, logical)) = hit else {
                continue;
            };
            tracing::debug!(%path, line, %found, "I18N002: physical direction");
            out.fire_in(
                &path,
                line_offset(&sheet.source, line),
                format!(
                    "{found} is physical but locale '{rtl}' reads right to left; use the logical form ({logical})"
                ),
            );
        }
    }

    fn inapplicable(&self, host: &P) -> Option<String> {
        missing_content_inputs(host)
    }
}

impl<P: ?Sized + CrunkHost> Measured<P> for I18n002 {
    fn subjects(&self, host: &P) -> usize {
        content_subjects(host)
    }
}
