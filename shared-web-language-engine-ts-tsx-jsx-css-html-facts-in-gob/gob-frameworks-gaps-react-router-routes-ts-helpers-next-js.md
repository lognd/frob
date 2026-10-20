+++
id = "01M48EFBCF70PK5KGS0PDZD40N"
title = "gob-frameworks gaps: react-router routes.ts helpers, Next.js re-exported route methods, page default export through a binding"
type = "story"
category = "todo"
priority = "medium"
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T11:09:41Z"
updated = "2026-10-06T11:09:41Z"
scope = ["crates/gob-frameworks/**"]

[[acceptance]]
text = "a framework-mode routes.ts fixture produces the expected routes"
bound = false

[[acceptance]]
text = "a re-exported GET handler in a Next.js route.ts yields method GET at Must"
bound = false

[[acceptance]]
text = "a page whose default export comes through export { X as default } names X as its component"
bound = false
+++

Found by ~AVXTRHX: (1) react-router framework-mode routes.ts helpers (route(), index(), layout(), prefix()) are not read; (2) a Next.js route.ts that re-exports its HTTP method handlers reports method ANY at May instead of following the re-export through the module graph; (3) a page's default export is read only from export default syntax, not through export { X as default } or a re-export. Each case must resolve or stay explicitly Unknown/May, never be dropped (language-engines.md 4).
