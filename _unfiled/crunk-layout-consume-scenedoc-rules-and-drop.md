+++
id = "01M7FDEF76XA17PYA0J7BME13T"
title = "crunk-layout: consume SceneDoc::rules and drop StylesheetNotApplied for supported selectors"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T10:53:30Z"
updated = "2026-11-15T11:49:07Z"
labels = ["no-story"]
scope = ["crates/crunk-layout/**"]

[[acceptance]]
text = "Given a scene with supported style rules, when layout styles are mapped, then matching elements receive the rule declarations and no StylesheetNotApplied finding is raised for those rules"
bound = true
+++

Follow-up of CDS3X1G. crunk-scene now exposes SceneDoc::rules (selector, supported, matches, at_rule). crunk-layout style/tree.rs and solve/mod.rs still raise StylesheetNotApplied; apply supported rules and drop the finding for them.
