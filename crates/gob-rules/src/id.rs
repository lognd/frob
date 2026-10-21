//! `RuleId`: a validated FAMILY + three digits identifier.

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Deserializer, Serialize, Serializer};

/// The longest family prefix a rule id may carry (`SYSDESIGN101` has a 9-letter family).
pub const MAX_FAMILY_LEN: usize = 12;

/// Why a string is not a valid rule id.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
#[error(
    "invalid rule id `{0}`: expected a 2-12 character uppercase family (letters, digits after the first) then 3 digits (e.g. COV006, A11Y101)"
)]
pub struct ParseRuleIdError(pub String);

/// A rule identifier such as `COV006`: an uppercase family plus 3 digits.
///
/// ```
/// use gob_rules::RuleId;
/// assert_eq!("A11Y101".parse::<RuleId>().unwrap().family(), "A11Y");
/// assert!("cov006".parse::<RuleId>().is_err());
/// assert_eq!("EXC001".parse::<RuleId>().unwrap().to_string(), "EXC001");
/// ```
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RuleId(String);

impl RuleId {
    /// The family prefix (capital letters, digits allowed after the first).
    pub fn family(&self) -> &str {
        &self.0[..self.0.len() - 3]
    }

    /// The three-digit number as an integer.
    pub fn number(&self) -> u16 {
        self.0[self.0.len() - 3..].parse().unwrap_or(0)
    }

    /// The full id string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl FromStr for RuleId {
    type Err = ParseRuleIdError;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        let bad = || ParseRuleIdError(s.to_owned());
        let split = s.len().checked_sub(3).ok_or_else(bad)?;
        let (fam, digits) = s.split_at_checked(split).ok_or_else(bad)?;
        let ok = (2..=MAX_FAMILY_LEN).contains(&fam.len())
            && fam.bytes().next().is_some_and(|b| b.is_ascii_uppercase())
            && fam
                .bytes()
                .all(|b| b.is_ascii_uppercase() || b.is_ascii_digit())
            && digits.bytes().all(|b| b.is_ascii_digit());
        if ok {
            Ok(Self(s.to_owned()))
        } else {
            Err(bad())
        }
    }
}

impl fmt::Display for RuleId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

impl Serialize for RuleId {
    fn serialize<S: Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        s.serialize_str(&self.0)
    }
}

impl<'de> Deserialize<'de> for RuleId {
    fn deserialize<D: Deserializer<'de>>(d: D) -> Result<Self, D::Error> {
        let s = String::deserialize(d)?;
        s.parse().map_err(serde::de::Error::custom)
    }
}

#[cfg(test)]
mod tests {
    use super::RuleId;

    // frob:tests RuleId
    #[test]
    fn families_may_carry_digits_after_the_first_letter() {
        assert!("A11Y101".parse::<RuleId>().is_ok());
        assert!("1ABC101".parse::<RuleId>().is_err());
        assert!("cov006".parse::<RuleId>().is_err());
    }

    // frob:tests RuleId
    #[test]
    fn long_families_up_to_the_cap_are_accepted() {
        let id = "SYSDESIGN101".parse::<RuleId>().unwrap();
        assert_eq!(id.family(), "SYSDESIGN");
        assert!("ABCDEFGHIJKL001".parse::<RuleId>().is_ok());
        assert!("ABCDEFGHIJKLM001".parse::<RuleId>().is_err());
    }
}
