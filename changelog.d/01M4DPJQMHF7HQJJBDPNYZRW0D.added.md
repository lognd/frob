A rule can declare an optional release_severity in #[rule], applied only by the release gate (crunk check --gate release, read by frob release status) and falling back to its family's value.
