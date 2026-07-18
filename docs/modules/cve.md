# frob.cve -- CVE Record Format v5 parser

One sentence: pydantic v2 models plus a parser/mirror-walker for CVE
Record Format v5 JSON as published at github.com/CVEProject/cvelistV5 --
parser and models only; matching a project's dependencies against a local
mirror and linking CWEs into the strata threat catalog is `frob vet`'s job
(T-0147, not yet built).

## Scope

- `cveMetadata`: id, lifecycle state (`PUBLISHED`/`REJECTED`), reservation/
  publication/update/rejection dates.
- `containers.cna` (mandatory) and `containers.adp[]` (zero or more,
  supplemental publishers like CISA-ADP): `affected[]` products
  (vendor/product/`versions[]` with `version`/`lessThan`/
  `lessThanOrEqual`/`versionType`/`status`, plus `defaultStatus`),
  `problemTypes[].descriptions[].cweId`, `metrics[]` (`cvssV3_1` and
  `cvssV4_0`: score/severity/vectorString), `references[]`,
  `descriptions[]`.
- `REJECTED` records parse into the same `CveRecord` shape -- state is a
  field, not a parse outcome, so callers decide whether to skip them.

## Error semantics (vacuous-pass doctrine)

Every model tolerates unknown extra fields (`extra="ignore"`): the real
cvelistV5 corpus grows optional fields on every schema revision, and a
strict model would break on every upstream release for fields this module
does not consume. What is NOT tolerated is a missing REQUIRED field --
`cveMetadata.cveId`/`state`, `containers.cna`, an `affected[].versions[]`
entry missing `version`/`status` -- which raises a pydantic
`ValidationError` that `parse_record` turns into `Err(CveError
.MalformedRecord)`.

`parse_record` never raises for a bad input file; every failure mode
(missing path, unreadable, not JSON, structurally invalid) is a distinct
`CveError` value. `iter_mirror` never silently drops a broken record: a
parse failure is yielded as `(path, Err(...))` alongside every successful
`(path, Ok(record))`, so a caller that only inspects `Ok` results cannot
mistake "silently skipped" for "clean" -- it has to look at every yielded
pair. An invalid mirror root itself is a single `Err(CveError
.MirrorPathInvalid)` entry, not an empty iterator (an empty iterator is
indistinguishable from "mirror exists and has zero records").

No network anywhere in this module, including tests -- `parse_record` and
`iter_mirror` operate purely on local paths, and `tests/unit/cve/fixtures`
commits real, publicly-published CVE records (Log4Shell CVE-2021-44228,
the curl CVE-2023-38545, the xz backdoor CVE-2024-3094, a cvssV4_0-bearing
record CVE-2024-4681, and the REJECTED CVE-2024-7039) so the parser is
tested against real-world shape variety without ever touching the network.

## Mirror layout

```
<root>/cves/YYYY/NNNxxx/CVE-YYYY-NNNN.json
```

`NNNxxx` is the CVE sequence number's thousands-bucket directory (e.g.
CVE-2021-44228 lives under `cves/2021/44xxx/CVE-2021-44228.json`) -- the
same layout `git clone https://github.com/CVEProject/cvelistV5` produces.
`iter_mirror` globs `cves/*/*/CVE-*.json` under the given root and yields
every match in sorted path order.

## Public API

<!-- frob:describes src/frob/cve/_models.py::CveState -->
<!-- frob:describes src/frob/cve/_models.py::CveError -->
<!-- frob:describes src/frob/cve/_models.py::CveMetadata -->
<!-- frob:describes src/frob/cve/_models.py::Version -->
<!-- frob:describes src/frob/cve/_models.py::Affected -->
<!-- frob:describes src/frob/cve/_models.py::ProblemTypeDescription -->
<!-- frob:describes src/frob/cve/_models.py::ProblemType -->
<!-- frob:describes src/frob/cve/_models.py::Cvss -->
<!-- frob:describes src/frob/cve/_models.py::Metric -->
<!-- frob:describes src/frob/cve/_models.py::Reference -->
<!-- frob:describes src/frob/cve/_models.py::Description -->
<!-- frob:describes src/frob/cve/_models.py::CnaContainer -->
<!-- frob:describes src/frob/cve/_models.py::AdpContainer -->
<!-- frob:describes src/frob/cve/_models.py::CveContainers -->
<!-- frob:describes src/frob/cve/_models.py::CveRecord -->
<!-- frob:describes src/frob/cve/_parser.py::parse_record -->
<!-- frob:describes src/frob/cve/_parser.py::iter_mirror -->

```python
class CveState(StrEnum)           # PUBLISHED | REJECTED
class CveError(ErrorSet)          # NotFound/Unreadable/NotJson/MalformedRecord/MirrorPathInvalid
class CveMetadata(BaseModel)      # cveId, state, reservation/publication/update/rejection dates
class Version(BaseModel)          # one versions[] entry: version/status/lessThan/lessThanOrEqual/versionType
class Affected(BaseModel)         # vendor/product/defaultStatus/versions[]
class ProblemTypeDescription(BaseModel)  # lang/description/cweId/type
class ProblemType(BaseModel)      # descriptions[]
class Cvss(BaseModel)             # version/vectorString/baseScore/baseSeverity
class Metric(BaseModel)           # cvssV3_1, cvssV4_0
class Reference(BaseModel)        # url/name/tags
class Description(BaseModel)      # lang/value
class CnaContainer(BaseModel)     # affected/problemTypes/metrics/references/descriptions
class AdpContainer(BaseModel)     # same shape as CnaContainer, zero or more per record
class CveContainers(BaseModel)    # cna (mandatory) + adp[] (zero or more)
class CveRecord(BaseModel)        # dataType/dataVersion/cveMetadata/containers

def parse_record(path: Path) -> Result[CveRecord, CveError]
def iter_mirror(root: Path) -> Iterator[tuple[Path, Result[CveRecord, CveError]]]
```

## Implementation notes / out of scope

- Matching parsed records against a project's resolved dependencies
  (name + version against `affected[].versions[]` range semantics) and
  linking `problemTypes[].descriptions[].cweId` into the strata threat
  catalog (`CWE_CATALOG`, `CWE_TOP_25_CATALOG`) is T-0147 (`frob vet`
  integration), not this module.
- No fetch/clone/update-mirror command exists here; a mirror is assumed
  to already exist on disk (e.g. `git clone
  https://github.com/CVEProject/cvelistV5`), consistent with the
  no-network posture of this module and its tests.
