# Config path defaults gate

### CONFIGPATH001 (T-4114)

<!-- frob:describes src/frob/gates/_config_path_defaults.py::config_path_default_gate -->

`frob.gates._config_path_defaults` -- `config_path_default_gate` (gate
name `config_path_defaults`, WARN severity, waivable). F-307 H3-5: no
gate compared an `AppConfig` default filesystem path against the target
deployment's filesystem, because there is no deployment manifest on
`main` to compare against. This rule is deliberately cheaper than a real
deployment-manifest comparison: it flags a pydantic `Field(default=...)`
on a `*_path`-named or `Path`-annotated field whose default value is a
relative path -- a relative default silently resolves against whatever
the process's cwd happens to be at start time, a real deployment footgun
independent of any manifest.

`config_path_default_gate` enumerates every pydantic `Field(...)` call
assigned to a class attribute (this repo's own `App`/`AppConfig`
pattern) whose:

  - name ends in `_path`, OR whose annotation is `Path`/`pathlib.Path`
    (both signals are checked, since a `*_path`-named field need not be
    `Path`-annotated in this repo's convention, and a `Path`-annotated
    field need not be named `*_path`)
  - `default=` keyword value is a string or `Path(...)`-literal that is
    not absolute (POSIX or Windows-style) and is not `None`

A `*_path` field with `default=None`, an absolute default, or no
`default=` at all (a required field) stays quiet -- there is nothing to
flag. Waivable with the standard file-scoped `frob:waive CONFIGPATH001
reason="..."` directive, for a default that is deliberately relative to
a package root.

## Rule table entry

| Rule | Gate name | Meaning |
| --- | --- | --- |
| CONFIGPATH001 | config_path_defaults | (warn) a pydantic `Field(default=...)` on a `*_path`-named or `Path`-annotated field has a relative default value -- see "CONFIGPATH001 (T-4114)" above |
