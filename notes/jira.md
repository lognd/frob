# Jira reference for frob v2: data model, pinch points, prior art, agentic use

Date: 2026-10-01. Sources were fetched on that date; Atlassian renamed
"issue" -> "work item" (2025) and "project" -> "space" (2026-02) in the UI
only; REST, JQL field names and webhooks still say issue/project, so this
note uses the API vocabulary. UNCERTAIN marks claims not confirmed against a
primary 2026 source. The goal is a precise reference for superseting Jira
conceptually in an in-repo, git-native, CLI-first, agent-first tracker.

Sections:

1. Jira data model (exhaustive)
2. Jira pinch points, structural causes, git-native counter-moves
3. Competitor models worth stealing from
4. Agentic usage vs human Jira usage
5. Consolidated design implications for frob v2

Legend for "frob" columns: a one-line idea, not a commitment.

---------------------------------------------------------------------------
## 1. Jira data model
---------------------------------------------------------------------------

### 1.0 Platform changes 2025-2026 that reshape the model

| Change | Detail | Source |
|---|---|---|
| issue -> work item | UI/docs only, from 2025-03; API, JQL, webhooks unchanged | https://community.developer.atlassian.com/t/work-is-the-new-collective-term-for-items-tracked-in-jira/88552 |
| project -> space | From 2026-02-21; "space owner/role/admin"; JQL funcs aliased (spacesLeadByUser, workItemHistory, linkedWorkItems); old names still work | https://jirareleases.atlassian.com/announcements/jira-spaces-a-new-name-that-matches-how-you-really-work |
| /rest/api/{2,3}/search removed | Deprecated 2025-05-01, shut off 2025-08..10, now 410; replaced by /rest/api/3/search/jql (nextPageToken, no total) | https://confluence.atlassian.com/jirakb/run-jql-search-query-using-jira-cloud-rest-api-1289424308.html |
| Points-based rate limits | Enforced from 2026-03-02 (sec 1.18) | https://developer.atlassian.com/cloud/jira/platform/rate-limiting/ |
| Automation billed in "steps" | Org-pooled steps replace rule-runs; overage billing from 2026-12-03 (sec 1.11) | https://support.atlassian.com/cloud-automation/docs/how-is-my-usage-calculated/ |
| Summer 2026 release | Rovo Delivery Agent, rebuilt team-managed boards, Capacity view, formula fields, agents assignable to work items; Claude/Copilot/Cursor as automation actions | https://www.atlassian.com/blog/development/jira-summer-release |
| Attachments | Default 1 GB/file, max 2 GB (not 10 MB) | https://support.atlassian.com/jira-cloud-administration/docs/configure-file-attachments/ |
| Data Center EOL | No new DC sales after 2026-03-30; read-only 2029-03-28 | https://www.atlassian.com/licensing/data-center-end-of-life |

### 1.1 Issue types and hierarchy

| Level | Default types | Notes |
|---|---|---|
| 2+ | Initiative, custom | Premium/Enterprise, company-managed only, global; parent only between adjacent levels; reordering levels breaks existing parent links; max count undocumented (UNCERTAIN) |
| 1 | Epic | `hierarchyLevel: 1` in REST issuetype |
| 0 | Story, Task, Bug, custom | "Standard Issue Type (Level 0)" |
| -1 | Subtask | always lowest; same project as parent; re-parent = Move |

Parent field: `parent` replaced Epic Link (`customfield_10014`) and Parent Link
(`customfield_10018`, Advanced Roadmaps) in REST/webhooks; announced 2021-11,
grace to 2022-11, Parent Link field finally removed 2025-06-13. Shape:
`{"id","key","self","fields":{"summary","status","issuetype"}}`. JQL:
`parent = K`, `parentEpic = K`, `key in portfolioChildIssuesOf("K")`,
`childIssuesOf` (Plans JQL, UNCERTAIN scope).
https://community.developer.atlassian.com/t/deprecation-of-the-epic-link-parent-link-and-other-related-fields-in-rest-apis-and-webhooks/54048
https://confluence.atlassian.com/jirakb/create-a-custom-work-type-hierarchy-in-jira-cloud-1387599403.html

### 1.2 Fields

System field ids (from `/rest/api/3/field`): summary, description,
issuetype, project, status, resolution, priority, assignee, reporter,
creator, created, updated, resolutiondate, duedate, labels, components,
fixVersions, versions (Affects), environment, parent, subtasks, issuelinks,
attachment, comment, worklog, timetracking, timeoriginalestimate,
timeestimate, timespent, aggregatetimeoriginalestimate,
aggregatetimeestimate, aggregatetimespent, aggregateprogress, progress,
workratio, watches, votes, security, statuscategorychangedate, lastViewed,
thumbnail, issuerestriction (team-managed). JQL-only: statusCategory,
issuekey, text. (Membership assembled from the field endpoint; UNCERTAIN for
a single 2026 page.)

Custom field types (prefix `com.atlassian.jira.plugin.system.customfieldtypes:`):

| Key | Kind | Searcher |
|---|---|---|
| textfield / textarea / readonlyfield / url | text | textsearcher, exacttextsearcher |
| float | number | exactnumber |
| datepicker / datetime | date | daterange / datetimerange |
| select / multiselect / radiobuttons / multicheckboxes | option | multiselectsearcher |
| cascadingselect | option pair | cascadingselectsearcher |
| userpicker / multiuserpicker | account | userpickergroupsearcher |
| grouppicker / multigrouppicker | group | grouppickersearcher |
| project / version / multiversion | ref | projectsearcher, versionsearcher |
| labels | labels | labelsearcher |
| atlassian-team | Team UUID | - |

Software-locked types: Rank `com.pyxis.greenhopper.jira:gh-lexo-rank`,
Sprint `gh-sprint`, Epic Name/Status/Colour/Link `gh-epic-*` (UNCERTAIN
keys), Story Points = float. Typical ids on a fresh site (per-site, must be
discovered): Sprint 10020, Rank 10019, Epic Name 10011, Epic Link 10014,
Parent Link 10018, Story Points (company-managed) 10028 or 10026/10036,
"Story point estimate" (team-managed) 10016, Team 10001.
https://support.atlassian.com/jira/kb/jira-software-rest-api-essential-parameters-for-custom-field-creation/
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-fields/

### 1.3 Workflows

Status categories are hard-coded: id 1 `undefined` "No Category", id 2 `new`
"To Do" (grey), id 4 `indeterminate` "In Progress" (yellow), id 3 `done`
"Done" (green). Statuses are global objects mapped into workflows; workflow
schemes map issue types -> workflows per company-managed project;
team-managed projects have one workflow per issue type and no schemes.
https://community.developer.atlassian.com/t/bad-documentation-for-rest-api-3-statuscategory/78565

| Element | Vocabulary (company-managed Cloud) |
|---|---|
| Transition kinds | initial (Create), standard, global (any -> X), looped/self |
| Conditions | Always False; Block until approval; Compare Number Custom Field; Hide From User; Only Assignee; Only Reporter; Permission; Previous Status; Separation of Duties; Sub-Task Blocking; User Is In Any Group / Any Space Role / Custom Field / Group / Group Custom Field / Space Role; Value Field; grouped All/Any |
| Validators | Date Compare; Date Window; Field Required; Field has single value; Field has been modified; Parent Status; Permission; User Permission; Previous State; Regular Expression Check |
| Post-functions, fixed order, non-removable | 1 Set status; 2 Add comment if entered; 3 Update change history and store; 4 Re-index; 5 Fire Generic Event |
| Post-functions, optional | Assign to Current User / Lead Developer / Reporter; Clear Field Value; Copy Value From Other Field; Set security level by role; Trigger a Webhook; Update custom field; Update field (Assignee, Description, Environment, Priority, Resolution, Summary, estimates) |
| Properties | `jira.permission.<perm>.<type>[=v]` (e.g. edit.denied), `jira.issue.editable=false`, `opsbar-sequence`, `jira.i18n.title/submit` |

Resolution is only set by a post-function or a transition screen, never by a
board column. https://support.atlassian.com/jira-cloud-administration/docs/configure-advanced-issue-workflows/
https://support.atlassian.com/jira-cloud-administration/docs/use-workflow-validators-for-company-managed-projects/

### 1.4 Resolutions, priorities, components, versions, labels

| Object | Fields / defaults | Source |
|---|---|---|
| Resolution | Done, Won't Do, Duplicate, Cannot Reproduce (+JSM Known error, Hardware/Software failure). Resolved == resolution non-null; key struck through | https://support.atlassian.com/jira-cloud-administration/docs/what-are-issue-statuses-priorities-and-resolutions/ |
| Priority | Highest, High, Medium, Low, Lowest; priority schemes per project | https://support.atlassian.com/jira-cloud-administration/docs/manage-priority-schemes/ |
| Component | per project: name, description, lead, assigneeType in {PROJECT_DEFAULT, COMPONENT_LEAD, PROJECT_LEAD, UNASSIGNED} | REST api-group-project-components |
| Version | name, description, startDate, releaseDate, released, archived, overdue, projectId; referenced by fixVersions and versions (affects) | REST api-group-project-versions |
| Label | global namespace, free text, no spaces, no governance; JQL match case-insensitive (UNCERTAIN nuance) | JRACLOUD-60543 |

### 1.5 Links and relations

Three unrelated mechanisms: `issuelinks` (typed, bidirectional, needs Link
permission in both projects), `parent`/`subtasks` (hierarchy), remote links
(globalId + application + object). Default link types (name: outward /
inward): Blocks: blocks / is blocked by; Cloners: clones / is cloned by;
Duplicate: duplicates / is duplicated by; Relates: relates to / relates to.
No topology constraints (cycles in Blocks are legal). JQL:
`linkedWorkItems(K, "is blocked by")`,
`workItemsWithRemoteLinksByGlobalId(...)` (<=100).
https://confluence.atlassian.com/adminjiraserver/configuring-issue-linking-938847862.html

### 1.6 Sprints

Fields: id, state in {future, active, closed}, name, goal, startDate,
endDate, completeDate, createdDate, originBoardId. Sprint custom field on an
issue is an ARRAY of every sprint it ever belonged to (history kept for
reports). Complete sprint: only right-most column counts as done; subtasks
must be done; incomplete items go to backlog, an existing future sprint, or
a new sprint; completion date is not stamped on items. Velocity: Commitment
= estimate at sprint start (later adds excluded), Completed = estimate done
at end (scope change included); items added after start flagged `*`.
Parallel sprints: board setting allowing several active sprints.
https://support.atlassian.com/jira-software-cloud/docs/complete-a-sprint/
https://support.atlassian.com/jira-software-cloud/docs/view-and-understand-the-velocity-chart/

### 1.7 Boards

| Facet | Jira behaviour |
|---|---|
| Kind | scrum (backlog + sprints) or kanban (optional kanban backlog, releases from Done column); each backed by a saved filter |
| Columns | map N statuses -> column; left-most grey, right-most green = complete; UNMAPPED statuses hide the issue |
| WIP limits | constraint type per board (issue count / original / remaining estimate), then min/max per column; visual only |
| Swimlanes | Stories (parent + subtasks), Assignees, Epics, Queries (JQL; default "Expedite" = priority Blocker), Projects, None |
| Quick filters | named JQL toggles |
| Card colours | by issue type, priority, assignee, query, none |
| Estimation statistic | Story points / Original time estimate / Issue count; optional remaining-time tracking |
| Done hiding | kanban hides Done after window (default 2 weeks, by Updated) |
| 2026 | team-managed boards rebuilt (no item caps); company-managed moving to same engine |

https://support.atlassian.com/jira-software-cloud/docs/configure-columns/
https://support.atlassian.com/jira-software-cloud/docs/configure-swimlanes/

### 1.8 Backlog ranking: LexoRank

Rank is one string per issue in the locked Rank field, format `b|rrrrr[:frac]`
where `b` in {0,1,2} is a bucket and `rrrrr` is base-36 compared
lexicographically, e.g. `0|i000v8:`. Moving an issue between A and B writes
the lexicographic midpoint of A and B into ONE row (appending digits when no
midpoint exists at current length), so a move is O(1) writes and never
renumbers neighbours: that is why Atlassian chose it over integer positions
on multi-node Data Center. Costs: repeated insertion between the same two
neighbours grows the string; marker rows hold min/max per bucket; a
background job rebalances by evenly redistributing all ranks into the next
bucket (0->1->2->0) while a per-op lock (1500 ms timeout) serialises moves.
Thresholds (DC doc): length 128 -> rebalance within 12 h; 160 -> immediate;
>200 ranking disabled during rebalance; 254 hard max. Cloud hides all of
this (no admin page; Atlassian runs rebalancing). Importers ignore Rank, so
imported issues sort by creation. API: `PUT /rest/agile/1.0/issue/rank
{issues[<=50], rankBeforeIssue|rankAfterIssue, rankCustomFieldId?}`.
https://confluence.atlassian.com/adminjiraserver/managing-lexorank-938847803.html
https://support.atlassian.com/jira/kb/troubleshooting-lexorank-system-issues/
https://developer.atlassian.com/cloud/jira/software/rest/api-group-issue/

### 1.9 Estimation and time tracking

Two story-point fields with no sync: "Story Points" (company-managed) and
"Story point estimate" (team-managed); `GET/PUT
/rest/agile/1.0/issue/{key}/estimation?boardId=` abstracts over them.
Time tracking: `timetracking{originalEstimate, remainingEstimate,
timeSpent, *Seconds}`; worklog `{id, author, updateAuthor, started,
timeSpentSeconds, comment(ADF), visibility{type: group|role, value,
identifier}}`; `adjustEstimate` in {new(newEstimate), leave, manual(reduceBy),
auto}. `aggregate*` = issue + subtasks.
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-worklogs/

### 1.10 Comments, watchers, votes, attachments, changelog, properties

| Object | Shape |
|---|---|
| Comment | v3 body = ADF doc; v2 wiki markup; `visibility{type: role|group, value, identifier}`; JSM `jsdPublic` (internal note vs customer); `jsdAuthorCanSeeRequest`; append-only, unthreaded |
| Watchers / votes | `watches{watchCount,isWatching}`, `votes{votes,hasVoted}`; auto-watch on create/comment is a user pref |
| Attachments | Atlassian Media; content/thumbnail URLs; default 1 GB, max 2 GB per file |
| Changelog | `expand=changelog` or `/issue/{key}/changelog`: `histories[{id, author, created, items[{field, fieldtype: jira|custom, fieldId, from, fromString, to, toString}]}]` |
| Entity properties | hidden JSON per issue: `/issue/{key}/properties/{k}`; JQL `issue.property[k].path`; webhooks issue_property_set/deleted |

https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-comments/
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/

### 1.11 Automation rules

| Part | Vocabulary |
|---|---|
| Triggers | Field value changed; Form attached/opened/submitted; Incoming webhook; Work item assigned / commented / comment edited / created / deleted / linked / link deleted / moved / transitioned / updated; Manual; Multiple events; Space created; Scheduled (JQL, max 999 items); Work logged; Sprint created/started/completed; Version created/updated/released; DevOps branch/commit/PR/build/deployment; JSM alert, approval, SLA breach; Assets object events |
| Conditions | Issue fields; smart-value compare; JQL; Related issues; User; If/else (2 nesting levels); attachments; affected services; AQL |
| Actions | Edit/Assign/Clone/Create/Delete/Transition; Create sub-tasks; Link; Comment; Email/Slack/Teams/Twilio/web request; Lookup issues (first 100); Create variable; Log work; Create/Release version; Create sprint; Manage watchers; Set entity property; Delete attachments/comment/links; Re-fetch; Create branch; Create Confluence page; Use Rovo agent; branch "For: related / JQL / most recent" (150 per branch) |
| Smart values | `{{issue.key}}`, `{{issue.fields.customfield_10020}}`, `{{fieldChange.fromString}}`, `{{webResponse.body}}` |
| Limits 2026 | steps/month pooled per org: Jira Free 150/site, Standard 400/user, Premium 750/user, Enterprise 1000/user; concurrent flows 5/10/20/30; 65 steps per flow (500 advanced); overage $0.50 per 1000 steps from 2026-12-03 |

https://support.atlassian.com/cloud-automation/docs/jira-automation-triggers/
https://support.atlassian.com/cloud-automation/docs/jira-automation-actions/
https://support.atlassian.com/cloud-automation/docs/automation-service-limits/

### 1.12 JQL

Grammar: `query := clause ((AND|OR) clause)* [ORDER BY field [ASC|DESC] (, ...)*]`;
`clause := [NOT] field op (value | function | (list)) [predicate]* | ( query )`.
Operators: `= != > >= < <= IN NOT IN ~ !~ IS IS NOT WAS WAS IN WAS NOT WAS NOT IN CHANGED`;
`!=` excludes EMPTY; keywords `EMPTY`/`NULL`; history predicates `AFTER BEFORE
BY DURING ON FROM TO` (with WAS/CHANGED).

Functions (2026 names, legacy aliases accepted): currentUser, membersOf,
now, currentLogin, lastLogin, startOf/endOf{Day,Week,Month,Year}("+/-n[yMwdhm]"),
openSprints, closedSprints, futureSprints, releasedVersions,
unreleasedVersions, earliestUnreleasedVersion, latestReleasedVersion,
linkedWorkItems (=linkedIssues), workItemHistory (=issueHistory, 50),
updatedBy, votedWorkItems, watchedWorkItems, workItemsWithRemoteLinksByGlobalId,
componentsLeadByUser, spacesLeadByUser, spacesWhereUserHasPermission/Role,
standardWorkTypes, subtaskWorkTypes, cascadeOption, choiceOption,
parentEpic, portfolioChildIssuesOf; JSM: approved, approver, myApproval,
pending, breached, everBreached, completed, paused, running, remaining,
withinCalendarHours, organizationMembers. `issueFunction()` is ScriptRunner.

Saved filters: owner, sharing (private / user / group / project+role / org /
public), favourites, board/plan/dashboard sources, subscriptions (cron
email). REST: `GET/POST /rest/api/3/search/jql {jql, nextPageToken,
maxResults (default 50, cap 5000 for id-only, ~100 with fields), fields,
expand, reconcileIssues[<=50 ids] for read-your-writes}` ->
`{issues, isLast, nextPageToken}`; `POST /search/approximate-count`;
`POST /issue/bulkfetch`. Index is eventually consistent.
https://support.atlassian.com/jira-software-cloud/docs/jql-operators/
https://support.atlassian.com/jira-software-cloud/docs/jql-functions/
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/

### 1.13 Dashboards and gadgets

Dashboards share like filters. Built-in gadgets: Activity Stream, Assigned
To Me, Average Age, Average Time in Status, Bubble Chart, Created vs
Resolved, Days Remaining in Sprint, Filter Results, Work item Calendar /
Statistics, Pie Chart, Recently Created, Resolution Time, Road Map, Sprint
Health, Sprint Burndown, Time Since, Two Dimensional Filter Statistics,
Voted / Watched, Workload Pie Chart, Wallboard Spacer.
https://support.atlassian.com/jira-cloud-administration/docs/use-dashboard-gadgets/

### 1.14 Permissions

Project permissions: Administer, Browse, Manage sprints, Service project
agent, View development tools, View read-only workflow, View aggregated
data; work item: Archive, Assign, Assignable user, Close, Create, Delete,
Edit, Link, Modify reporters, Move, Resolve, Restore archived, Schedule
(due date + ranking), Set security, Transition; View voters and watchers,
Manage watchers; Add / Edit own|all / Delete own|all comments; Create /
Delete own|all attachments; Work on, Edit own|all worklogs, Delete own|all
worklogs. REST keys like `BROWSE_PROJECTS`, `TRANSITION_ISSUES`,
`MANAGE_SPRINTS_PERMISSION`. Grantees: user, group, project role, project
lead, reporter, current assignee, application access, user/group custom
field, portal customer, anyone on the web. Global: Administer Jira, Browse
users, Share dashboards/filters, Manage group subscriptions, Make bulk
changes, Create team-managed projects. Schemes unavailable on Free.
https://support.atlassian.com/jira-cloud-administration/docs/permissions-for-company-managed-projects/

### 1.15 Notification and security schemes

Events: created, updated, assigned, resolved, closed, commented, comment
edited, reopened, deleted, moved, work logged / started / stopped, worklog
updated / deleted, Generic event, custom events. Recipients: current
assignee, reporter, current user, project lead, component lead, single
user, group, project role, all watchers, user/group custom field value,
single email (UNCERTAIN in current UI). Issue security scheme = ordered
levels each granting to users/groups/roles/reporter/assignee/lead/custom
fields; `security` field on the issue.
https://support.atlassian.com/jira-cloud-administration/docs/configure-notification-schemes/

### 1.16 Project types and management styles

| Type key | What | Distinctives |
|---|---|---|
| software | Jira | scrum/kanban boards, sprints, releases, dev panel |
| business | ex Jira Work Management, merged 2024 | list/calendar/timeline views |
| service_desk | JSM | request types, portal, queues (JQL), SLAs (goals, calendars, start/pause/stop), approvals, customers/organizations, Assets |
| product_discovery | JPD | ideas with custom types, insights (evidence), impact/effort/confidence/formula fields, matrix/timeline views, delivery progress from linked work; creators paid ($10/$25 per creator/mo), contributors free |

Team-managed vs company-managed:

| Aspect | Team-managed | Company-managed |
|---|---|---|
| Config | self-contained per project, no schemes, project admin suffices | shared schemes (type, workflow, screen, field config, permission, notification, priority) |
| Resolution | none; Done category = done | set via post-function |
| Hierarchy | Epic/Story/Subtask only | custom levels (Premium) |
| Points | "Story point estimate" | "Story Points" |
| Boards | historically one per project (rebuilt 2026) | many boards over filters |
| Migration | sprints, estimates, versions, report history do not transfer | - |

https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-spaces/
https://support.atlassian.com/jira-product-discovery/docs/jira-product-discovery-fields-reference/

### 1.17 Plans (Advanced Roadmaps, Premium)

Plan = sources (boards, projects, filters) + sandbox staged until "Save
changes"; scenarios; extended hierarchy; cross-project releases;
dependencies via a configured link type (default Blocks) with dependency
report, red when off-track; capacity per team per iteration in points /
hours / days (default 30 pts) with velocity from history; auto-schedule;
Teams field (UUID). 2026 adds a Capacity view in core Jira.
https://support.atlassian.com/jira-software-cloud/docs/what-is-advanced-roadmaps/
https://support.atlassian.com/jira-software-cloud/docs/what-are-dependencies-in-advanced-roadmaps/

### 1.18 REST shape, Agile API, rate limits, auth, webhooks

Trimmed `GET /rest/api/3/issue/PROJ-123?expand=names,changelog,transitions`
(ids are site-specific):

```
{"id":"10042","key":"PROJ-123","self":"https://x.atlassian.net/rest/api/3/issue/10042",
 "expand":"renderedFields,names,schema,transitions,editmeta,changelog",
 "fields":{
  "summary":"Fix login",
  "issuetype":{"id":"10001","name":"Bug","subtask":false,"hierarchyLevel":0},
  "project":{"id":"10000","key":"PROJ","projectTypeKey":"software","simplified":false},
  "status":{"id":"3","name":"In Progress",
            "statusCategory":{"id":4,"key":"indeterminate","name":"In Progress","colorName":"yellow"}},
  "resolution":null,"resolutiondate":null,
  "priority":{"id":"2","name":"High"},
  "assignee":{"accountId":"5b10a2...","displayName":"A. User","active":true},
  "reporter":{"accountId":"..."},"creator":{"accountId":"..."},
  "created":"2026-09-01T10:00:00.000+0000","updated":"2026-09-30T12:00:00.000+0000",
  "duedate":"2026-10-15","labels":["auth"],
  "components":[{"id":"10010","name":"Web"}],
  "fixVersions":[{"id":"10100","name":"2.1","released":false,"archived":false,"releaseDate":"2026-11-01"}],
  "versions":[],
  "parent":{"id":"10001","key":"PROJ-100",
            "fields":{"summary":"Auth epic","issuetype":{"name":"Epic","hierarchyLevel":1}}},
  "subtasks":[{"id":"10050","key":"PROJ-124","fields":{"summary":"...","issuetype":{"subtask":true}}}],
  "issuelinks":[{"id":"20001",
                 "type":{"id":"10000","name":"Blocks","inward":"is blocked by","outward":"blocks"},
                 "outwardIssue":{"id":"10060","key":"PROJ-130","fields":{"summary":"..."}}}],
  "description":{"type":"doc","version":1,
                 "content":[{"type":"paragraph","content":[{"type":"text","text":"Steps..."}]}]},
  "comment":{"comments":[{"id":"30001","author":{},"body":{"type":"doc","version":1,"content":[]},
                          "created":"...","jsdPublic":true,
                          "visibility":{"type":"role","value":"Developers"}}],
             "maxResults":1,"total":1,"startAt":0},
  "timetracking":{"originalEstimate":"1d","remainingEstimate":"4h","timeSpent":"4h",
                  "originalEstimateSeconds":28800,"remainingEstimateSeconds":14400,"timeSpentSeconds":14400},
  "aggregatetimespent":14400,"progress":{"progress":14400,"total":28800,"percent":50},"workratio":50,
  "watches":{"watchCount":2,"isWatching":true},"votes":{"votes":0,"hasVoted":false},
  "security":null,"statuscategorychangedate":"2026-09-20T09:00:00.000+0000",
  "customfield_10028":5.0,
  "customfield_10020":[{"id":42,"name":"PROJ Sprint 7","state":"active","boardId":3,"goal":"Ship auth",
                        "startDate":"2026-09-22T08:00:00.000Z","endDate":"2026-10-06T08:00:00.000Z"}],
  "customfield_10019":"0|i000v8:",
  "customfield_10001":{"id":"a1b2-...","name":"Team Vitafleet"}},
 "names":{"customfield_10020":"Sprint","customfield_10019":"Rank","customfield_10028":"Story Points"},
 "schema":{"customfield_10019":{"type":"any","custom":"com.pyxis.greenhopper.jira:gh-lexo-rank","customId":10019}},
 "transitions":[{"id":"31","name":"Done","hasScreen":false,"isGlobal":true,
                 "to":{"id":"10001","name":"Done","statusCategory":{"key":"done"}}}],
 "changelog":{"histories":[{"id":"50001","author":{},"created":"...",
   "items":[{"field":"status","fieldtype":"jira","fieldId":"status",
             "from":"10000","fromString":"To Do","to":"3","toString":"In Progress"}]}]}}
```

| Topic | Facts | Source |
|---|---|---|
| v2 vs v3 | same resources; v3 bodies are ADF JSON, v2 wiki markup; `renderedFields` = HTML; `editmeta` lists editable fields + allowedValues | https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/ |
| Agile API | `/rest/agile/1.0`: board (config, issues, backlog, sprints, versions), sprint CRUD + state machine future->active->closed, moveIssuesToSprint (<=50), backlog/issue, epic (legacy), issue/rank, issue/{key}/estimation | https://developer.atlassian.com/cloud/jira/software/rest/api-group-issue/ |
| Rate limits (from 2026-03-02) | hourly points: 1/request +1 per core object +2 per identity object, writes 1; global pool 65k pts/h; per-tenant Standard 100k + 10/user, Premium 130k + 20/user, Enterprise 150k + 30/user, cap 500k; burst per path GET/POST 100 rps, PUT/DELETE 50 rps; per-issue writes 20 per 2 s and 100 per 30 s; 429 + Retry-After, X-RateLimit-*, RateLimit-Reason | https://developer.atlassian.com/cloud/jira/platform/rate-limiting/ |
| Auth | OAuth 2.0 3LO granular scopes `read:issue:jira`, `write:issue:jira`, ... plus classic `read:jira-work`, `write:jira-work`, `manage:jira-project`; API tokens; Forge | https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/ |
| Webhooks | jira:issue_created/updated/deleted, comment_*, worklog_*, attachment_*, issuelink_*, issue_property_*, project_*, jira:version_*, sprint_*, board_*, user_*; JQL scoping for issue events; 5 retries 5-15 min on 408/409/425/429/5xx; `X-Atlassian-Webhook-Identifier` for dedupe; 20 concurrent per tenant+host | https://developer.atlassian.com/cloud/jira/platform/webhooks/ |
| Concurrency | simultaneous transitions on one issue now 409 (was 400) | https://developer.atlassian.com/cloud/jira/platform/change-notice-update-in-simultaneous-transitions-issue-api/ |

---------------------------------------------------------------------------
## 2. Jira pinch points
---------------------------------------------------------------------------

Each row: pain, structural cause, evidence, and a one-line git-native
counter-move for frob.

| # | Pinch | Why it happens structurally | Evidence | frob counter-move |
|---|---|---|---|---|
| 1 | Slowness: issue view 1-4 s, boards 4-20 s; 128-200 XHR / 5 MB per issue | React SPA fans out per field/panel/app iframe to a multi-tenant Java monolith plus a separate async index; Marketplace Connect/Forge iframes add round trips | https://news.ycombinator.com/item?id=25590846 ; https://www.radial.build/blog/why-is-jira-so-slow ; https://jira.atlassian.com/browse/JRACLOUD-73176 | local files + SQLite projection; every read is a <10 ms process, no network |
| 2 | Over-configuration: hundreds of duplicate custom fields; schemes copied per project drift; DC guardrail 1200 fields, Cloud cap 700 per field configuration and 150 types per scheme | one scheme per concern (type, workflow, screen, field config, permission, notification, security) independently associable per project; custom fields are global objects with contexts, so every global field is indexed for every issue | https://confluence.atlassian.com/spaces/ADMINJIRASERVER/pages/1141488685/Jira+Software+guardrails ; https://community.atlassian.com/forums/Enterprise-articles/Empowering-Jira-admins-to-optimize-usability-at-scale/ba-p/3098575 | one schema file in the repo (frob.toml), reviewed in PRs, no per-project scheme indirection |
| 3 | Workflow rigidity: cannot set a status, must fire a transition; API 400/409 "transition not found"; validators silently no-op bulk ops; admin-only edits with draft/publish; status rename breaks saved JQL text | status is a state-machine id reachable only via transition ids with conditions/validators/post-functions; workflows are global shared objects so edits need publish+migration; JQL stores status names as text | https://jira.atlassian.com/browse/JRACLOUD-73053 ; https://jira.atlassian.com/browse/JRACLOUD-73985 ; https://community.atlassian.com/forums/Jira-questions/Transition-issue-via-API-returning-a-400/qaq-p/2018879 | statuses are a small fixed category enum with free display names; gates are checks on `close`, not a transition graph; policy changes are a commit |
| 4 | Bulk edit: 1000-issue cap; mixed workflows must be transitioned per group; bulk move drops option fields whose ids differ; notification toggle only for admins | synchronous per-issue permission/validation in one request; option values stored by context-scoped id so names cannot be mapped; notification suppression is project config | https://support.atlassian.com/jira-software-cloud/docs/edit-multiple-issues-at-the-same-time/ ; https://jira.atlassian.com/browse/JRA-8248 | bulk = a query piped to a verb, applied as one commit; dry-run diff first |
| 5 | No first-party CLI for ~20 years; Atlassian ACLI only GA May 2025, Cloud only; no offline mode | every CLI is a thin HTTP wrapper; no sync protocol, no local replica, no offline queue | https://www.atlassian.com/blog/jira/atlassian-command-line-interface ; https://github.com/ankitpokhrel/jira-cli ; https://github.com/go-jira/jira/issues/314 | CLI is the product; git is the sync; works on a plane |
| 6 | LexoRank: ranking disabled during rebalance, stuck rebalances, duplicate ranks, imports land at bottom; 128/160/254-char thresholds; 1500 ms lock | global order encoded as per-row strings needing periodic renormalisation under a lock; importers ignore the field | https://support.atlassian.com/jira/kb/lexorank-rebalancing-gets-stuck-with-error-expected-the-row-last-migrated-to-be-in-the-new-bucket/ ; https://jira.atlassian.com/browse/MIG-332 | rank is an explicit ordered list per queue (or fractional index) in a text file; "rebalance" is a normal commit, conflicts resolve in review |
| 7 | Estimation theatre: points converted to hours, cross-team velocity comparisons, two unsynced point fields (Story Points vs Story point estimate) | points are a plain float custom field with no semantics; team- and company-managed projects grew separate fields; boards must be told which to read | https://www.atlassian.com/agile/project-management/estimation ; https://community.atlassian.com/forums/Jira-questions/Story-Point-field-not-available-on-team-managed-project/qaq-p/1840577 | one optional `size` enum; measured cost (tokens, wall-clock) replaces guessed points |
| 8 | Sprint carry-over: incomplete items re-count as full commitment; Sprint field accumulates every sprint; velocity and burndown distort | Sprint field is a multi-value array so old reports stay correct; commitment snapshot at start; velocity counts only right-most column | https://support.atlassian.com/jira/kb/the-sprint-field-contains-completed-sprint-valuesold/ ; https://jira.atlassian.com/browse/JSWSERVER-20777 | no sprints by default; optional cycles are time windows queried from the op log, never stored on the ticket |
| 9 | Status vs resolution: Done without resolution shows unresolved; a To Do item struck through; a resolution literally named "Unresolved" counts as resolved | resolution is a separate nullable field; "Unresolved" is the rendering of NULL; strikethrough, resolutiondate and charts key on it; team-managed projects derive it from status, company-managed need post-functions | https://confluence.atlassian.com/cloudkb/best-practices-on-using-the-resolution-field-968660796.html ; https://support.atlassian.com/jira/kb/clear-the-resolution-field-when-an-issue-is-reopened-in-jira-cloud/ | one terminal state carries a mandatory `outcome` (done, wontdo, duplicate, dropped) set atomically on close |
| 10 | Parent-link history: Epic Link, Parent Link, subtask parent, then unified `parent`; automations, JQL and SDKs broke; Epic Name made optional | epics were bolted on by the GreenHopper plugin as links + custom fields; Advanced Roadmaps added its own field; unification required deprecating fields in REST, webhooks and changelogs | https://community.developer.atlassian.com/t/deprecation-of-the-epic-link-parent-link-and-other-related-fields-in-rest-apis-and-webhooks/54048 ; https://community.atlassian.com/forums/Jira-Cloud-Admins-articles/The-fields-quot-Epic-Link-quot-and-quot-Parent-Link-quot-will-be/ba-p/2995787 | a single typed `parent` edge from day one; hierarchy depth is a config, not a field |
| 11 | Cross-project boards: sprint belongs to originBoard but appears on every overlapping board; estimation field must match; unmapped statuses vanish | boards are saved-filter views, not containers; sprints are entities attached to issues; columns map a union of statuses | https://support.atlassian.com/jira/kb/sprints-appearing-on-multiple-boards-in-jira-data-center-server-or-cloud/ ; https://jira.atlassian.com/browse/JSWSERVER-13265 | one repo = one project; views are saved queries over categories, so nothing can be unmapped |
| 12 | Permissions: >=5 independent layers (global, scheme, role/group, security level, board/filter share) produce "visible in search, invisible on board" | each layer is configured separately and evaluated at different points (index filter, board filter share, security field) | https://support.atlassian.com/jira/kb/board-does-not-exist-or-you-do-not-have-permission-to-view-error-in-jira/ ; https://confluence.atlassian.com/jirakb/jira-permissions-general-overview-625902332.html | repo access is the permission model; one owner; agents are identities with capability flags in config |
| 13 | Notification noise: every event mails assignee, reporter, watchers; auto-watch; no per-issue mute; batching bolted on | per-event-per-project recipient roles; auto-watch default on; batching is a buffer layer with urgent bypass | https://community.atlassian.com/forums/Jira-articles/Say-goodbye-to-inbox-overload-Updates-to-Jira-email-batching/ba-p/2376375 ; https://jira.atlassian.com/browse/JRACLOUD-84765 | no notifications; `frob ready`/`frob log --since` are polled; optional single webhook |
| 14 | Search index lag: JQL returns stale data right after an edit; automations miss fresh changes; Cloud dropped exact totals | writes go to the DB, JQL reads an async Lucene/OpenSearch index (JSIS); no read-after-write; `reconcileIssues` <=50 ids is the workaround | https://developer.atlassian.com/cloud/jira/platform/search-and-reconcile/ ; https://support.atlassian.com/jira/kb/find-the-total-number-of-work-items-in-jira-cloud-using-jql-or-issue-search/ | the file you just wrote is the index source; projection rebuilt synchronously per command, so reads are consistent |
| 15 | API rate limits and churn: opaque 429s, 2025 /search removal broke SDKs, 2026 points quotas | multi-tenant shared backend; limits historically unpublished (the "10 rps per user" figure is folklore, UNCERTAIN); replacement search is token-paginated and capped | https://developer.atlassian.com/cloud/jira/platform/rate-limiting/ ; https://github.com/atlassian-api/atlassian-python-api/issues/1500 ; https://community.atlassian.com/forums/App-Central-articles/The-429-Nightmare-How-You-Can-Stop-Jira-Cloud-Rate-Limits/ba-p/3232410 | no server, no quota; the only limit is disk and git |
| 16 | Markup: v2 wiki markup vs v3 ADF JSON; no Markdown; no official converter; hand-authoring ADF is painful | Cloud editor stores ProseMirror-derived JSON for macros/mentions/media; DC kept wiki; no canonical text form | https://developer.atlassian.com/platform/framework/adf-builder/technical/about-adf/ ; https://community.atlassian.com/forums/Jira-questions/API-endpoint-to-convert-ADF-Atlassian-Document-Format-to-wiki/qaq-p/3147290 | CommonMark only; ticket body is a Markdown file |
| 17 | Ticket-as-chat: decisions buried at comment 27; description never updated; "see Slack" | comments are append-only, unthreaded, unpinnable rows; no decision field; description edits unsurfaced | https://arielpartners.com/jira-anti-patterns/ ; https://techcrunch.com/2016/12/11/death-to-jira/ ; https://news.ycombinator.com/item?id=24145665 | body is the spec and is versioned by git; comments are typed events (decision, evidence, question) not chat |
| 18 | Done items vanish (kanban 2-week window, sprint completion); keys renumber on Move (old keys redirect, never reused); project key change hits URLs and JQL | key = project counter; Move re-issues; board hides by Updated date | https://support.atlassian.com/jira/kb/completed-issues-not-hidden-on-kanban-board/ ; https://support.atlassian.com/jira/kb/moved-issues-no-longer-redirect-from-previous-issue-key-or-url-in-jira/ | ids are repo-scoped and stable forever; archive is a query filter, not deletion |
| 19 | No multi-parent (JRACLOUD-87724 Won't Fix lineage); subtask cannot leave parent's project; labels are typo-prone free text | hierarchy is a single parent pointer; labels have no registry | https://jira.atlassian.com/browse/JRACLOUD-87724 ; https://jira.atlassian.com/browse/JRACLOUD-60543 | single parent kept (tree topology), but typed `related`/`discovered-from` edges cover the rest; labels declared in config |
| 20 | Team-managed <-> company-managed migration loses sprints, estimates, versions, history | two parallel implementations of the same concepts | https://support.atlassian.com/jira-software-cloud/docs/migrate-between-team-managed-and-company-managed-projects/ | one implementation |
| 21 | GDPR accountId switch (2019) broke `assignee = jsmith`, SDKs, automations | usernames removed from APIs; identity now opaque ids | https://developer.atlassian.com/cloud/jira/platform/deprecation-notice-user-privacy-api-migration-guide/ | identities are git author strings plus declared agent names in config |
| 22 | Pricing and platform drift: Server EOL 2024-02-15, DC read-only 2029-03-28; FY26 price rises 5-10%, Oct 2026 7-10%; Rovo bundled as credits (UNCERTAIN exact numbers) | SaaS lock-in | https://www.atlassian.com/licensing/data-center-end-of-life ; https://s206.q4cdn.com/270053503/files/doc_downloads/2025/09/Fiscal-2026-Cloud-Pricing-notice.pdf | MIT/Apache binary; data is plain files in your repo |

Canonical critique threads: https://news.ycombinator.com/item?id=17596293
("Why do you dislike Jira?"), https://news.ycombinator.com/item?id=21749794
("Why do engineers hate Jira?"), https://thenewstack.io/why-developers-hate-jira-and-what-atlassian-is-doing-about-it/ ,
https://www.seangoedecke.com/party-tricks/ . "Jira is where tickets go to
die" has no single canonical source (UNCERTAIN origin).

---------------------------------------------------------------------------
## 3. Competitor models worth stealing from
---------------------------------------------------------------------------

### 3.1 Per-tool notes

| Tool | Model in brief | Status 2026 | Sources |
|---|---|---|---|
| Linear | `TEAM-n` ids per team; fixed status categories Triage/Backlog/Unstarted/Started/Completed/Canceled (+Duplicate); cycles 1-8 w with cooldown, auto-rollover, capacity from last 3 cycles; triage inbox (Accept/Decline/Snooze/Duplicate, responders, ordered triage rules); relations blocks/related/duplicate (one-way); estimates exp/fib/linear/t-shirt with zero; SLA risk states; projects with milestones, updates, health; initiatives; auto-close stale and auto-archive; local-first sync engine with server-assigned integer sync ids; Agent Interaction SDK: `delegate` vs `assignee`, AgentSession states pending/active/error/awaitingInput/complete/stale, AgentActivity thought/action/elicitation/response/error, plan checklist, 10 s ack; June 2026 "coding sessions" run Claude Code/Codex in Linear sandboxes | alive, agent-first direction | https://linear.app/docs/configuring-workflows ; https://linear.app/docs/use-cycles ; https://linear.app/docs/triage ; https://linear.app/docs/archive-issues ; https://linear.app/developers/agent-interaction ; https://linear.app/docs/coding-sessions ; https://linear.app/method/introduction ; https://github.com/wzhudev/reverse-linear-sync-engine |
| Shortcut | Stories (feature/bug/chore) -> Epics -> Objectives; workspace-global `sc-NNNN`; workflow states grouped into 4 state types Backlog/Unstarted/Started/Done; epics have their own workflow; iterations with date-derived state; blocked graph rendered as Mermaid | alive | https://www.shortcut.com/help/stories/stories-overview/ ; https://www.shortcut.com/help/iterations/iterations-overview/ |
| GitHub Projects v2 | project = field graph over issues/PRs/drafts: <=50 fields (text, number, date, single select, iteration), <=50k items; table/board/roadmap views; built-in workflows (added->Todo, closed->Done, PR merged->Done, auto-add by search, auto-archive by filter); GraphQL ProjectV2 + `gh project`; issue types (org, <=25) and sub-issues GA 2025-04; dependencies blocked-by/blocking GA 2025-08 (<=50 each way); gh v2.94 (2026-06) exposes `--type --parent --blocked-by`; Copilot cloud agent: assign issue -> `copilot/*` branch + draft PR, 59 min cap, session logs | alive | https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects ; https://github.blog/changelog/2025-04-09-evolving-github-issues-and-projects/ ; https://github.blog/changelog/2025-08-21-dependencies-on-issues/ ; https://github.blog/changelog/2026-06-10-manage-sub-issues-types-and-dependencies-from-github-cli/ ; https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent |
| Azure Boards | process templates Basic/Agile/Scrum/CMMI with fixed hierarchies; state CATEGORIES Proposed/In Progress/Resolved/Completed/Removed (one Completed state per type; auto Activated/Resolved By+Date); link types with declared topology (Hierarchy=tree single parent acyclic, Dependency=acyclic, Related=network, Duplicate=tree, TestedBy, Remote); area and iteration path trees; WIQL with `ASOF`, `EVER`, `UNDER`, link queries `MODE(Recursive)`; `az boards`; closed items hidden after 183 d | alive | https://learn.microsoft.com/en-us/azure/devops/boards/work-items/workflow-and-state-categories?view=azure-devops ; https://learn.microsoft.com/en-us/azure/devops/boards/queries/link-type-reference?view=azure-devops ; https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax?view=azure-devops |
| Fossil tickets | tickets are repo artifacts, not files: `K` random 40-hex id, `J [+]field value` change cards, `D` timestamp, `U` user; state = replay changes in time order (LWW per field, `+` appends); local SQL projection `TICKET`/`TICKETCHNG` rebuilt from artifacts; schema/reports local TH1/SQL config | alive | https://fossil-scm.org/home/doc/trunk/www/tickets.wiki ; https://fossil-scm.org/home/doc/trunk/www/fileformat.wiki ; https://fossil-scm.org/home/help/ticket |
| git-bug | operation-based CRDT: each bug is a commit chain under `refs/bugs/<id>`; `ops` JSON blob per commit, Lamport `edit-clock-N` marker entries, `extra/` tree for media; ids SHA-256 of first op; replay in clock order, unknown ops skipped; divergent tips -> empty merge op; bridges GitHub/GitLab/Jira; v0.11.0 2026-09-22, formal spec repo | alive | https://github.com/git-bug/git-bug ; https://github.com/git-bug/spec/blob/main/dag-entity.md |
| Jujutsu | change id = 16 random bytes shown as 12 reverse-hex chars (z..k), distinct from commit hash; stored as `change-id` git commit header so it survives plain git remotes; `jj evolog` predecessor chain; operation log DAG enables undo and concurrent ops; divergent change = two visible commits with one id, addressed `id/n`, resolved explicitly (`abandon`, `squash`, `metaedit`, `converge`) | alive | https://docs.jj-vcs.dev/latest/glossary/ ; https://github.com/jj-vcs/jj/pull/6162 ; https://docs.jj-vcs.dev/latest/guides/divergence/ |
| Beads (bd) | Oct 2025 by Steve Yegge; v0.x = SQLite cache + `.beads/issues.jsonl` in git; Feb 2026 moved to Dolt (cell-merge SQL), backlash, "Beads Classic" embedded Dolt restored by v0.63 (Apr 2026); repo now github.com/gastownhall/beads, ~27k stars, ~940 open issues; ids `prefix-hash` with 4/5/6 hex chars scaled by count, hierarchical `bd-a3f8.1`; types bug/feature/task/epic/chore(+message); P0-P4; status open/in_progress/blocked/closed/deferred; deps blocks (only one affecting readiness)/related/parent-child/discovered-from (+tracks, until, caused-by); `bd ready --json`, `bd update --claim`, `bd close --reason`, `bd prime`, `bd remember`, `bd compact` (memory decay), `bd setup claude|codex|cursor`; "landing the plane" session ritual | alive, churny | https://github.com/steveyegge/beads ; https://github.com/gastownhall/beads/blob/main/docs/DEPENDENCIES.md ; https://www.dolthub.com/blog/2026-04-02-restoring-beads-classic/ ; https://steveyegge.spicytakes.org/post/2025-11-12-introducing-beads-a-coding-agent-memory-system ; Rust port of the pre-Dolt design https://github.com/Dicklesworthstone/beads_rust |
| Backlog.md | `backlog/{tasks,drafts,docs,decisions}/*.md` with YAML frontmatter (TASK-1, TASK-1.1, status, deps, parent), acceptance criteria + DoD checklists, TUI kanban, MCP server; ~7k stars | alive | https://github.com/MrLesk/Backlog.md |
| Radicle | issues/patches are COBs: signed append-only DAG under `refs/namespaces/<nid>/refs/cobs/<type>/<oid>`; custom COB types allowed; state = topological reduce; `rad issue open/state/label/assign`; 1.10.3 Sept 2026 | alive | https://radicle.dev/guides/protocol ; https://radicle.dev/2026/09/08/radicle-1.10.3 |
| git-issue (dspinellis) | `.issues/` nested repo, issue dir keyed by SHA prefix, fields as files, GitHub/GitLab import/export | slow | https://github.com/dspinellis/git-issue |
| ticket.sh, ticket (wedow), slips, seeds, trck, git-native-issue | one-person 2025-26 projects: markdown or JSONL in tree, or commit chains under `refs/issues/<uuid>`; trck derives readiness/topo order | young | https://github.com/masuidrive/ticket.sh ; https://github.com/wedow/ticket ; https://github.com/leonkacowicz/trck ; https://github.com/remenoscodes/git-native-issue ; survey https://nesbitt.io/2026/08/20/issues-in-the-repo.html |
| Dead | Bugs Everywhere (2013), ditz (2008), ticgit, sit (2018) | dead | https://matej.ceplovi.cz/blog/current-state-of-the-distributed-issue-tracking.html |
| Claude Code Tasks | TodoWrite replaced by persistent TaskCreate/Update/List/Get (v2.1.16, 2026-01), blockers, on-disk `~/.claude/tasks/<id>/`, shared list ids across terminals; Anthropic credits Beads as inspiration | alive | https://code.claude.com/docs/en/changelog ; https://paddo.dev/blog/from-beads-to-tasks/ |
| Codex / Cursor / Devin | Codex cloud: one sandbox per task, PR as output; Cursor cloud agents <=8 parallel, `agent/<slug>` branches (UNCERTAIN); Devin `POST /v1/sessions {prompt, playbook_id, idempotent, tags}` | alive | https://learn.chatgpt.com/docs/cloud ; https://cursor.com/help/ai-features/cloud-agents ; https://docs.devin.ai/api-reference/v1/sessions/create-a-new-devin-session |

### 3.2 Concept table

| Concept | Who | How | Applicability to agent-first git-native CLI |
|---|---|---|---|
| Stable random id, content-addressed versions | jj, Fossil, git-bug | random 128-bit id; versions hashed; `id/n` for divergence | HIGH: ids must survive rebase/squash and concurrent edits |
| Short collision-resistant ids, length grows with count | Beads | `proj-a1b2`, 4->6 hex by issue count | HIGH: humans and agents type ids; no counters |
| Hierarchical ids | Beads, Backlog.md | `id.1.1` | MED: breaks on re-parent; store parent edge too |
| Append-only field-change log, replay for state | Fossil, git-bug, Radicle | ops with timestamp/Lamport clock, LWW per field, `+` append | HIGH: merge-free sync and free audit trail |
| Custom refs instead of working tree | git-bug, Radicle | `refs/bugs/<id>` chains | MED: no diff noise but needs refspecs; working-tree files are simpler for agents and reviewable in PRs |
| Local SQL projection, authoritative log in git | Fossil, Beads v0.x | rebuildable cache, never synced | HIGH: fast `ready`/graph queries |
| Status categories separate from names | Linear, Azure, Shortcut | fixed enum, custom names map onto it | HIGH: tooling keys on category |
| One Completed state, auto timestamps per category change | Azure | Activated/Resolved By+Date | MED: cheap derived metrics |
| Triage inbox + accept/decline/snooze/duplicate + rules | Linear | separate Triage category, ordered rules | HIGH: agent-created tickets land in triage |
| Duplicate as one-way relation + reserved status | Linear, Azure (tree topology) | dup -> canonical | HIGH: dedupe is the main agent-noise problem |
| Typed relations with topology constraints | Azure | tree / dependency(acyclic) / network | HIGH: `blocks` acyclic, `parent` single-target |
| `discovered-from` provenance edge | Beads | dep type from spawned to origin | HIGH: agents spawn follow-ups constantly |
| `ready` query + atomic claim | Beads, trck | readiness from blocks graph; `--claim` | HIGH: the core agent loop primitive |
| Cycles with auto-rollover and cooldown | Linear | fixed cadence, exceptions in cooldown | MED: human cadence only |
| Auto-close stale, auto-archive closed | Linear, GH Projects, Azure (183 d) | thresholds, notify, restore | HIGH: backlog decay limits context bloat |
| Compaction / memory decay | Beads | summarise old closed issues | MED: shrink `prime`, keep raw log |
| `prime` context dump | Beads, Backlog.md | one command prints workflow + open state | HIGH: session-start hook |
| JSON everywhere | Beads, gh, az | every verb `--json` | HIGH: non-negotiable |
| Agent session as first-class object | Linear, Copilot | states incl. awaitingInput/stale; activities; plan checklist | HIGH: "who works on what, blocked on which question" |
| delegate vs assignee | Linear | agent is delegate, human stays accountable | HIGH |
| One branch + one PR per task, hard timeout | Copilot | 59 min, draft PR | MED: good autonomous-run constraints |
| Historical and link-graph queries | Azure WIQL `ASOF`, `EVER`, `MODE(Recursive)` | query over revision history | MED: free with an op log |
| Signed ops, identity entity | git-bug, Radicle | signed commits, versioned identities | MED: agent vs human attribution via git signing |
| Fresh-context loop driven by task file | Ralph loop, Claude Code Tasks | one task per iteration, state in files | HIGH: tracker is the durable plan |
| Fields-on-a-graph views | GH Projects | typed fields per project item, views are saved filters | MED: views = saved queries over repo tickets |
| Local-first sync with central order | Linear | integer sync id | LOW: git is the transport |

---------------------------------------------------------------------------
## 4. Agentic usage vs human Jira usage
---------------------------------------------------------------------------

| Dimension | Human Jira usage | Agent usage (evidence) | Implication for frob |
|---|---|---|---|
| Output | rendered UI, email | `claude -p --output-format json` returns `result, session_id, is_error, num_turns, usage, total_cost_usd`; `--json-schema` structured output; `--bare` for deterministic scripted runs; MCP `outputSchema`/`structuredContent`; `bd ready --json`; GitHub Agent Tasks REST (`/agents/tasks/{id}`) | every verb has `--json` with a versioned envelope; exit codes distinguish "nothing ready" from failure |
| Retries | user clicks once | harness retries API calls (`system/api_retry` events), turns may be replayed with `--resume`; MCP `idempotentHint`; Beads hash ids exist because sequential ids collided across agents/branches; Devin sessions have an `idempotent` flag | `create` accepts client key or content hash; `claim/close/attach` are idempotent; ids are hash/ULID |
| Concurrency | one person per ticket, implicit | Claude Code `--worktree` + `git worktree lock` per agent, `isolation: worktree` subagents; Codex one sandbox per task; Cursor <=8 parallel; Devin 10+ sessions; Jules 3/15/60; Copilot `copilot/*` only; Beads `bd update --claim`; multi-agent runs use ~15x tokens | atomic claim with owner + lease/heartbeat, per-ticket branch and worktree pointers, stale-claim expiry |
| Scope and acceptance | prose description, implicit DoD | SWE-bench instance = `problem_statement, FAIL_TO_PASS, PASS_TO_PASS, base_commit, hints_text`; Copilot guidance: issue is the prompt, list acceptance criteria and files; study of 3,180 Copilot PRs: well-scoped +16.4% merge rate, file pointers +6-7%, env-setup emphasis -9.4%; Devin: split into verifiable sub-tasks | first-class fields: problem, in-scope paths, acceptance checks (ideally executable), out-of-scope |
| Closure | status drag | Copilot/Codex attach logs and test results to PRs; Actions on agent PRs need human approval; SWE-bench "done" is purely test outcome; Anthropic: give agents a way to verify | `close` requires evidence (test run, CI URL, PR, transcript); frob can re-run acceptance checks itself |
| Cost | hours logged by hand | Claude Code `total_cost_usd`, OTel `claude_code.cost.usage`, `claude_code.token.usage`, `--max-budget-usd`; Devin ACU (~15 min active, $2.00-2.25); Codex credits (cloud ~5x local); Copilot premium requests | tag every run with ticket id; roll up tokens/USD/wall-clock per ticket; cost replaces story points |
| Feedback loop | minutes per page | agents issue hundreds of tool calls per task; Beads `ready` ~10 ms (UNCERTAIN); Claude Code `--bare` to cut startup; hooks pre-filter test output from tens of thousands of tokens to hundreds | sub-100 ms local reads, terse default output, pagination |
| Notification | email, badges | none; agents poll `bd ready`; Claude Code `/loop` (cron, 1 min to 3 d), Ralph Wiggum stop-hook loop; Linear AgentSession webhooks (5 s ack, 10 s first activity); GitHub Agent Tasks "poll task status" | `ready`/`next` cheap and idempotent; events on stdout; optional webhook; no inbox |
| Workspace | one checkout | Claude Code `.claude/worktrees/<name>` branch `worktree-<name>`; Copilot `copilot/<slug>` (since 2025-10-16); Cursor `agent/<slug>` (UNCERTAIN) | deterministic `<prefix>/<ticket-id>-<slug>` branch and worktree recorded on the ticket |
| Ticket text | long prose, attachments | ticket body is injected verbatim into a context window; AGENTS.md in >60k repos, Linux Foundation AAIF 2025-12; AGENTS.md cut runtime 28.6% and output tokens 16.6% (arXiv 2601.20404); CLAUDE.md advised <200 lines; `bd prime` prints workflow + memories | keep bodies small, link rather than inline, `show --prompt` renders a prompt-ready view |
| Memory | humans remember | each session starts with a fresh context; Yegge: "Memento in real life", conflicting markdown gives agents "dementia"; Claude Code auto-memory; Managed Agents store sessions server-side | tracker is the durable memory; compaction summaries for closed tickets; decisions recorded as typed events |
| Human checkpoints | approvals via comments | explicit waiting states everywhere: Linear `awaitingInput`, A2A `input-required`, MCP Tasks `input_required`, GitHub `waiting_for_user`; Copilot needs human PR approval; Jules `requirePlanApproval`; Claude Code `--permission-prompts none`, `permission_denials` | first-class `blocked-on-human` with reason and resume hook, distinct from `blocked-on-dependency` |
| State machines | per-project custom workflows | A2A: submitted/working/input-required/completed/failed/canceled/rejected; MCP Tasks: working/input_required/completed/failed/cancelled; Linear: pending/active/error/awaitingInput/complete/stale; GitHub: queued/in_progress/completed/failed/idle/waiting_for_user/timed_out/cancelled | small fixed enum with terminal vs non-terminal, failed distinct from cancelled, stale/timed-out explicit |

Sources for this section:
https://code.claude.com/docs/en/headless ; https://code.claude.com/docs/en/worktrees ;
https://code.claude.com/docs/en/costs ; https://code.claude.com/docs/en/scheduled-tasks ;
https://modelcontextprotocol.io/specification/2025-06-18/server/tools ;
https://modelcontextprotocol.io/extensions/tasks/overview ;
https://docs.github.com/en/rest/agent-tasks/agent-tasks ;
https://docs.github.com/copilot/how-tos/agents/copilot-coding-agent/best-practices-for-using-copilot-to-work-on-tasks ;
https://docs.github.com/en/copilot/responsible-use/agents ;
https://github.blog/changelog/2025-10-16-copilot-coding-agent-uses-better-branch-names-and-pull-request-titles/ ;
https://arxiv.org/html/2512.21426v1 ; https://arxiv.org/abs/2601.20404 ;
https://huggingface.co/datasets/SWE-bench/SWE-bench ; https://www.swebench.com/SWE-bench/guides/datasets/ ;
https://docs.devin.ai/essential-guidelines/instructing-devin-effectively ; https://docs.devin.ai/admin/billing ;
https://developers.openai.com/codex/pricing ; https://openai.com/index/introducing-codex/ ;
https://linear.app/developers/agent-interaction ; https://a2a-protocol.org/v0.2.5/specification/ ;
https://agents.md ; https://www.anthropic.com/engineering/writing-tools-for-agents ;
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ;
https://simonwillison.net/2025/Jun/14/multi-agent-research-system/ ;
https://ghuntley.com/ralph/ ; https://github.com/anthropics/claude-code/blob/main/plugins/ralph-wiggum/README.md ;
https://ianbull.com/posts/beads/ ; https://arxiv.org/html/2606.17799v1 (position paper: harnesses treat the issue tracker as the coordination primitive) ;
https://linear.app/now/our-approach-to-building-the-agent-interaction-sdk .

Caveats: Anthropic's tool-writing guide has no explicit idempotency
language; Beads latency and Cursor branch naming come from secondary
sources; Yegge's Medium posts 403 to fetchers, quotes are from mirrors.

---------------------------------------------------------------------------
## 5. Consolidated design implications for frob v2
---------------------------------------------------------------------------

What to superset from Jira (keep the concept, change the mechanism):

| Jira concept | frob v2 shape |
|---|---|
| Issue types + hierarchy levels | small type enum (bug, feature, task, epic, chore) + configurable depth; one `parent` edge, tree topology |
| System + custom fields | fixed core schema; typed extra fields declared in frob.toml with validation; no per-site field ids |
| Workflow statuses / categories / transitions | fixed categories (triage, backlog, ready, active, blocked-on-dep, blocked-on-human, done, cancelled); display names free; gates checked on close, not on a transition graph |
| Resolution | mandatory `outcome` written atomically with terminal state |
| Priority / components / versions / labels | priority P0-P4; components = path globs; versions = git tags/milestones; labels declared |
| Links | typed edges with topology: blocks (acyclic), parent (single target), duplicate-of (one-way), related, discovered-from, supersedes |
| Sprints / cycles | optional time windows computed from the op log; no sprint field on tickets |
| Boards / swimlanes / quick filters | saved queries; board = query + group-by rendered in the terminal |
| LexoRank | explicit ordered list per queue in a text file; moves are commits |
| Estimation / worklogs | optional size; measured tokens/USD/wall-clock per run attached as evidence |
| Comments | typed events: note, decision, question, answer, evidence; body is the spec |
| Watchers / notifications | none; poll `ready`, `log --since`; optional webhook |
| Changelog | git history + op log; `ASOF`-style queries |
| Automation | hooks and policy rules in frob.toml, run locally, versioned |
| JQL | a small query language over the SQLite projection with history predicates (`was`, `changed after`) and graph functions (`blockedBy`, `childrenOf`, `ready`) |
| Dashboards | `frob stats` JSON + text tables |
| Permissions / security | repo ACL; agent identities with capability flags |
| Project types | one repo = one project; JSM/JPD concepts (SLA, insights) as optional fields and queries |
| Plans: dependencies, capacity | dependency graph is native; capacity = concurrent claims per agent identity |
| REST | the CLI JSON envelope is the API; MCP server wraps it |

Open questions to settle in design (not answered by this research):
storage of the op log (working-tree JSONL vs `refs/frob/*`), id length and
prefix policy, how evidence blobs are stored (git LFS, notes, or hashes
plus external paths), and whether to adopt a Lamport clock or rely on git
commit order plus explicit divergence detection as jj does.
