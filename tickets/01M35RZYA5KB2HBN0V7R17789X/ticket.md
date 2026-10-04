+++
id = "01M35RZYA5KB2HBN0V7R17789X"
title = "SQL103/SQL107 + TS/Prisma N+1 ORM rules"
type = "task"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:00Z"
aliases = ["T-5445"]
labels = ["v1-cluster:B2", "area:grimble"]
scope = ["src/frob/sql/_orm_rules.py"]
+++

found while working T-5337: filter-after-fetch (SQL103), server-cache-layer-for-repeated-expensive-queries (SQL107), and a TypeScript/Prisma N+1 walk (include/no-include mirrors Django's select_related) were cut from T-5337's scope to keep that leaf reviewable; SQL101/102/104/105/106 landed with real Python-first detection and migration_scan/pool-config helpers other leaves can reuse
