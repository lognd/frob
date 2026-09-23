# frob.webapp._seo_substrate -- per-route `<head>` metadata extraction

One sentence: `extract_page_metadata` turns one `.html`/`.jsx` route file's
`<head>` (or JSX `<Head>` wrapper) into a single frozen `PageMetadata`, and
`build_duplicate_title_index` folds a route table's worth of those into
the cross-route duplicate-title index -- so every SEO/WEBPERF rule that
needs title/meta/link/JSON-LD facts reuses this ONE walk instead of
re-querying the DOM per rule.

This is a follow-up leaf of the WEBSEC/COMPLY/A11Y/SEO/WEBPERF epic's
shared `frob.webapp`/`frob.lang` scaffolding
(`docs/modules/webapp.md`, T-5302/T-5300); it depends on but does not
duplicate either: framework detection stays in `frob.webapp._detect.
detect_frameworks`, and parsing stays behind `frob.lang.raw_tree` (the
same single parse dispatch every grammar in the repo goes through).

## Public API

```python
class SeoError(ErrorSet):
    UnsupportedLanguage  # extension is not .html or .jsx
    ParseFailed          # frob.lang could not produce a usable tree
    NoHeadElement         # no <head>/<Head> element found in the document

class MetaTag(BaseModel):   # frozen
    name: str | None
    property: str | None
    content: str | None

class LinkTag(BaseModel):   # frozen
    rel: str | None
    href: str | None

class PageMetadata(BaseModel):   # frozen
    route: str
    source_path: str
    title: str | None
    meta: tuple[MetaTag, ...]
    links: tuple[LinkTag, ...]
    json_ld: tuple[str, ...]

def extract_page_metadata(path: Path, *, route: str | None = None) -> Result[PageMetadata, SeoError]
def build_duplicate_title_index(pages: tuple[PageMetadata, ...]) -> dict[str, tuple[str, ...]]
```

`src/frob/webapp/_seo_substrate.py`.

### extract_page_metadata

Reads no file itself -- `frob.lang.raw_tree(path)` does the parse (T-5300's
`.html`/`.jsx` grammar wiring), and this function only walks the resulting
`Node` tree. Two shapes are recognized:

- **HTML** (`.html`, grammar label `html`): the document's own `<head>`
  element. Direct children `<title>`, `<meta>`, `<link>`, and
  `<script type="application/ld+json">` are collected; anything else
  under `<head>` (a stray `<style>`, a comment) is ignored.
- **JSX** (`.jsx`, grammar label `javascript`): a `<Head>` or `<head>`
  wrapper element anywhere in the tree (the Next.js/React convention --
  `import Head from "next/head"`), walked the same way over JSX's own
  `jsx_element`/`jsx_attribute` node shapes.

`.vue` Single File Components are out of scope: a `.vue` file's grammar
top level is `template_element`/`script_element`/`style_element` only
(`src/frob/lang/_walk_vue.py`'s SFC-shell-only docstring) -- there is no
`<head>` block to find.

`route` defaults to `str(path)`; a caller building a full route table
(a later leaf -- route discovery itself is not this ticket's scope) passes
the logical route path instead, so `PageMetadata.route`/`source_path` can
differ (one route, one backing file).

Returns `Err(SeoError.NoHeadElement)` when no `<head>`/`<Head>` element is
found at all -- this is a normal, expected outcome for a route file with no
head metadata, not a parse failure.

### build_duplicate_title_index

`{title: (route, route, ...)}` for every title shared by two or more
routes in `pages`; a unique title is omitted entirely. Every SEO rule that
flags duplicate `<title>` tags across a route table calls this once and
reuses the result, rather than each re-scanning the full page list.

## Fixtures

`tests/fixtures/webapp/seo1xx/routes/` (own fixture tree, not shared with
any other WEBSEC/COMPLY/A11Y/SEO/WEBPERF family):

- `home.html`, `about.html` -- positive-control HTML routes with distinct
  titles, meta, link, and (on `home.html`) one JSON-LD block.
- `duplicate.html` -- shares `home.html`'s title ("Acme Storefront"), the
  planted duplicate-title pair `build_duplicate_title_index` must report.
- `no_head.html` -- negative control: no `<head>` element at all.
- `product.jsx` -- positive-control JSX route using the Next.js
  `<Head>` wrapper convention.
- `no_head.jsx` -- negative control: a JSX file with no `Head`/`head`
  wrapper element.

`tests/unit/test_webapp_seo_substrate.py` covers both positive and
negative controls for `extract_page_metadata` and
`build_duplicate_title_index`.

## Relationship to `docs/modules/webapp.md`

This module is one of seven concurrent WEBSEC/COMPLY/A11Y/SEO/WEBPERF
substrate leaves fanning out from T-5302; each owns its own doc page
rather than all seven editing `docs/modules/webapp.md` at once. A
follow-up ticket links all seven doc pages from `docs/modules/webapp.md`
once the fan-out lands.
