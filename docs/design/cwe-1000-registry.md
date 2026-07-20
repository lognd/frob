# CWE-1000 (Research Concepts) -- Full Per-Entry Disposition Registry

<!-- frob:ticket T-0109 -->

One sentence: every one of MITRE's 944 CWE-1000 Research-Concepts-view
entries gets an individual, reasoned disposition here -- `checkable`,
`duplicate-of <parent>`, or `out-of-scope(<named missing kernel concept>)` --
so `docs/strata/threat.md`'s prior 'cwe-1000 stays unstubbed, ~900 entries
would be repo spam' call is corrected: the entries are not spam, they are
catalogued and named, even though the vast majority resolve to the SAME
small set of missing kernel concepts.

## Source and honesty section

- **Dataset**: MITRE's own machine-readable CWE List export, fetched
  directly from `https://cwe.mitre.org/data/xml/cwec_latest.xml.zip`.
- **Version resolved**: `cwec_v4.20.xml` (CWE release **4.20**), the file
  MITRE's "latest" redirect served on the date of this pass.
- **View used**: View **1000**, "Research Concepts" (a graph view). MITRE
  ships View 1000 as 10 Pillar-level seed members
  (CWE-284/435/664/682/691/693/697/703/707/710); the full membership is
  the transitive closure of `ChildOf`/`MemberOf` edges tagged `View_ID=1000`
  reachable from those 10 seeds. That closure was computed programmatically
  (BFS to fixpoint, 5 rounds) directly from the XML, not hand-listed.
- **Denominator: 944** distinct CWE ids (all `Weakness`-kind entries;
  no `Category`/`Compound_Element` nodes are members of this particular
  view). This is MITRE's actual count for the pinned release, not the
  "~900" estimate the prior pass used -- 944 is the falsifiable number.
- **Unclassifiable ids**: **zero**. Every one of the 944 ids received a
  disposition below; none were dropped or skipped.
- **Deprecated entries**: zero of the 944 included ids carry MITRE's
  `Status=Deprecated`; deprecated CWEs are excluded from View 1000 by
  MITRE itself, not by this pass.
- **Method**: this is a systematic, rule-based pass over MITRE's own
  name/abstraction/relationship fields, not a hand-transcription and not a
  per-id web search (T-0109 constraint). The ruleset (documented in full
  in the companion `classify.py` methodology below) is:
  1. If the id is already a `WeaknessEntry` in `frob`'s live `CWE_CATALOG`
     (`src/frob/strata/_threat.py`) -- **checkable**, citing that entry.
  2. Else, walk the `ChildOf` chain (within View 1000) toward the root; if
     the nearest checkable ancestor's weakness family matches the node's
     own name (or the node's MITRE `Abstraction` is `Variant`, MITRE's own
     narrowest/most-technology-specific tier, which by definition adds no
     new fire-path shape over its Base) -- **duplicate-of** that ancestor.
  3. Else -- **out-of-scope**, bucketed by keyword match against the node's
     MITRE name into one of 18 named missing-kernel-concept groups (below),
     falling back to the existing `generic-precondition-model` bucket (the
     same class the repo already uses for CWE-840) only when no more
     specific concept keyword matches.
  Every row in the manifest is independently re-derivable by re-running
  the script against the same pinned XML; nothing here is a one-off manual
  judgment call not captured in the rule.

## Coverage by abstraction tier

| Abstraction | checkable | duplicate-of | out-of-scope | Total |
|---|---:|---:|---:|---:|
| Pillar | 0 | 0 | 10 | 10 |
| Class | 9 | 2 | 101 | 112 |
| Base | 16 | 45 | 462 | 523 |
| Variant | 1 | 94 | 197 | 292 |
| Compound | 1 | 2 | 4 | 7 |
| **Total** | **27** | **143** | **774** | **944** |

## Disposition split

- **checkable**: 27 ids -- already have a live
  `WeaknessEntry` in `frob`'s `std.cwe` `CWE_CATALOG`
  (`src/frob/strata/_threat.py`), reused as-is (no new entries needed;
  every CWE-1000 id whose fire path is directly modeled already had one).
- **duplicate-of**: 143 ids -- children/variants of a checkable
  id whose fire path is identical to their ancestor's (MITRE `Variant`-tier
  narrowing, or same-family Base/Class specialization), so cataloging them
  separately would duplicate coverage rather than add it -- the same
  discipline `docs/strata/threat.md` already applies to CWE-77 vs CWE-78.
- **out-of-scope**: 774 ids -- grouped into 18
  named missing-kernel-concept buckets below. This is the majority of the
  corpus, confirming (with an exact number this time, not a wave-off) the
  prior doc's claim that most of CWE-1000 sits outside a design-level
  closure engine's current vocabulary -- but every one of those ids is now
  individually named and grouped, not silently skipped as "repo spam."

## Out-of-scope buckets (named missing kernel concept -> member CWE ids)

### `generic-precondition-model` -- 360 ids

Generic/business-logic precondition (no structural flow pattern of its own -- the CWE-840 class named in the existing catalog).

CWE-64, CWE-73, CWE-98, CWE-112, CWE-114, CWE-115, CWE-118, CWE-128, CWE-130, CWE-135, CWE-170, CWE-174, CWE-178, CWE-179, CWE-182, CWE-183, CWE-184, CWE-187, CWE-196, CWE-197, CWE-198, CWE-203, CWE-204, CWE-205, CWE-206, CWE-207, CWE-208, CWE-221, CWE-222, CWE-224, CWE-228, CWE-229, CWE-230, CWE-231, CWE-232, CWE-233, CWE-234, CWE-235, CWE-236, CWE-237, CWE-238, CWE-239, CWE-240, CWE-241, CWE-242, CWE-243, CWE-252, CWE-253, CWE-256, CWE-257, CWE-262, CWE-263, CWE-282, CWE-283, CWE-286, CWE-296, CWE-299, CWE-300, CWE-324, CWE-329, CWE-339, CWE-340, CWE-341, CWE-344, CWE-345, CWE-348, CWE-349, CWE-351, CWE-353, CWE-354, CWE-356, CWE-357, CWE-358, CWE-360, CWE-369, CWE-372, CWE-374, CWE-375, CWE-377, CWE-385, CWE-386, CWE-390, CWE-391, CWE-392, CWE-393, CWE-394, CWE-402, CWE-404, CWE-407, CWE-410, CWE-412, CWE-414, CWE-419, CWE-420, CWE-422, CWE-424, CWE-426, CWE-427, CWE-428, CWE-431, CWE-433, CWE-435, CWE-436, CWE-437, CWE-439, CWE-440, CWE-441, CWE-446, CWE-447, CWE-448, CWE-449, CWE-450, CWE-453, CWE-454, CWE-455, CWE-456, CWE-459, CWE-473, CWE-474, CWE-478, CWE-488, CWE-494, CWE-495, CWE-496, CWE-515, CWE-522, CWE-523, CWE-544, CWE-547, CWE-552, CWE-553, CWE-565, CWE-573, CWE-581, CWE-582, CWE-584, CWE-601, CWE-602, CWE-606, CWE-607, CWE-610, CWE-617, CWE-618, CWE-621, CWE-626, CWE-627, CWE-628, CWE-642, CWE-665, CWE-668, CWE-669, CWE-670, CWE-671, CWE-672, CWE-673, CWE-674, CWE-675, CWE-676, CWE-681, CWE-682, CWE-683, CWE-684, CWE-685, CWE-686, CWE-687, CWE-688, CWE-691, CWE-692, CWE-693, CWE-694, CWE-695, CWE-696, CWE-697, CWE-698, CWE-704, CWE-705, CWE-706, CWE-708, CWE-710, CWE-733, CWE-749, CWE-756, CWE-757, CWE-758, CWE-766, CWE-767, CWE-768, CWE-776, CWE-780, CWE-784, CWE-799, CWE-804, CWE-807, CWE-827, CWE-829, CWE-830, CWE-835, CWE-837, CWE-839, CWE-841, CWE-842, CWE-909, CWE-911, CWE-912, CWE-913, CWE-914, CWE-915, CWE-916, CWE-920, CWE-923, CWE-924, CWE-925, CWE-926, CWE-927, CWE-940, CWE-941, CWE-1021, CWE-1023, CWE-1024, CWE-1025, CWE-1037, CWE-1038, CWE-1039, CWE-1041, CWE-1042, CWE-1043, CWE-1044, CWE-1045, CWE-1047, CWE-1048, CWE-1049, CWE-1050, CWE-1052, CWE-1053, CWE-1054, CWE-1055, CWE-1056, CWE-1057, CWE-1059, CWE-1060, CWE-1061, CWE-1062, CWE-1063, CWE-1064, CWE-1065, CWE-1067, CWE-1068, CWE-1071, CWE-1072, CWE-1073, CWE-1074, CWE-1076, CWE-1079, CWE-1082, CWE-1083, CWE-1084, CWE-1086, CWE-1087, CWE-1088, CWE-1089, CWE-1090, CWE-1091, CWE-1092, CWE-1093, CWE-1094, CWE-1095, CWE-1097, CWE-1099, CWE-1100, CWE-1101, CWE-1102, CWE-1103, CWE-1104, CWE-1105, CWE-1106, CWE-1107, CWE-1108, CWE-1109, CWE-1110, CWE-1111, CWE-1112, CWE-1114, CWE-1117, CWE-1118, CWE-1119, CWE-1120, CWE-1121, CWE-1122, CWE-1123, CWE-1124, CWE-1125, CWE-1127, CWE-1164, CWE-1173, CWE-1176, CWE-1177, CWE-1188, CWE-1190, CWE-1209, CWE-1224, CWE-1229, CWE-1231, CWE-1232, CWE-1235, CWE-1242, CWE-1243, CWE-1244, CWE-1246, CWE-1249, CWE-1250, CWE-1251, CWE-1253, CWE-1254, CWE-1258, CWE-1259, CWE-1261, CWE-1265, CWE-1270, CWE-1273, CWE-1281, CWE-1283, CWE-1284, CWE-1285, CWE-1286, CWE-1287, CWE-1288, CWE-1289, CWE-1290, CWE-1291, CWE-1292, CWE-1293, CWE-1294, CWE-1295, CWE-1296, CWE-1297, CWE-1303, CWE-1310, CWE-1311, CWE-1314, CWE-1316, CWE-1321, CWE-1323, CWE-1327, CWE-1328, CWE-1329, CWE-1332, CWE-1339, CWE-1341, CWE-1342, CWE-1357, CWE-1386, CWE-1389, CWE-1391, CWE-1392, CWE-1393, CWE-1395, CWE-1419, CWE-1426, CWE-1428, CWE-1434

### `sink-classification-model` -- 74 ids

Generic downstream-component sink classification (delimiter/escaping/encoding-specific neutralization; no single kernel sink shape spans LDAP/XPath/XQuery/CRLF/regex/format-string variants the way html_render/sql/exec already do).

CWE-74, CWE-75, CWE-76, CWE-90, CWE-91, CWE-93, CWE-99, CWE-113, CWE-116, CWE-117, CWE-134, CWE-138, CWE-140, CWE-141, CWE-142, CWE-143, CWE-144, CWE-145, CWE-146, CWE-147, CWE-148, CWE-149, CWE-150, CWE-151, CWE-152, CWE-153, CWE-154, CWE-155, CWE-156, CWE-157, CWE-158, CWE-159, CWE-160, CWE-161, CWE-162, CWE-163, CWE-164, CWE-165, CWE-166, CWE-167, CWE-168, CWE-172, CWE-173, CWE-175, CWE-176, CWE-177, CWE-185, CWE-186, CWE-261, CWE-444, CWE-598, CWE-624, CWE-625, CWE-643, CWE-644, CWE-652, CWE-707, CWE-777, CWE-790, CWE-791, CWE-792, CWE-793, CWE-794, CWE-795, CWE-796, CWE-797, CWE-838, CWE-917, CWE-943, CWE-1236, CWE-1267, CWE-1333, CWE-1336, CWE-1427

### `language-runtime-semantics-model` -- 58 ids

Language/runtime/framework semantics (finalize/clone/serialization/reflection/operator-misuse/dead-code/EJB-J2EE-Struts-JNI idioms; language-specific footguns with no generalizable flow precondition).

CWE-103, CWE-104, CWE-107, CWE-110, CWE-111, CWE-245, CWE-248, CWE-382, CWE-396, CWE-397, CWE-460, CWE-462, CWE-463, CWE-464, CWE-470, CWE-471, CWE-472, CWE-475, CWE-477, CWE-480, CWE-481, CWE-482, CWE-483, CWE-484, CWE-486, CWE-487, CWE-491, CWE-493, CWE-500, CWE-561, CWE-563, CWE-568, CWE-570, CWE-571, CWE-575, CWE-576, CWE-578, CWE-579, CWE-580, CWE-583, CWE-586, CWE-589, CWE-594, CWE-595, CWE-597, CWE-600, CWE-608, CWE-703, CWE-754, CWE-755, CWE-783, CWE-1046, CWE-1066, CWE-1069, CWE-1070, CWE-1075, CWE-1077, CWE-1126

### `sensitive-data-exposure-sink-model` -- 49 ids

Sensitive-data exposure sink catalog (error messages, comments, cache, WSDL, source/include files; the clearance lattice exists but these specific low-clearance sinks are not individually wired).

CWE-201, CWE-202, CWE-209, CWE-210, CWE-211, CWE-212, CWE-213, CWE-214, CWE-215, CWE-219, CWE-220, CWE-226, CWE-312, CWE-319, CWE-492, CWE-498, CWE-499, CWE-524, CWE-525, CWE-531, CWE-535, CWE-536, CWE-537, CWE-538, CWE-539, CWE-540, CWE-541, CWE-546, CWE-548, CWE-550, CWE-614, CWE-615, CWE-651, CWE-1004, CWE-1078, CWE-1080, CWE-1085, CWE-1113, CWE-1115, CWE-1116, CWE-1230, CWE-1266, CWE-1272, CWE-1275, CWE-1320, CWE-1420, CWE-1421, CWE-1422, CWE-1423

### `memory-model` -- 44 ids

Memory model (no pointer/buffer/allocator/arithmetic-width representation).

CWE-14, CWE-131, CWE-188, CWE-191, CWE-192, CWE-193, CWE-195, CWE-244, CWE-395, CWE-401, CWE-457, CWE-466, CWE-467, CWE-468, CWE-469, CWE-562, CWE-587, CWE-588, CWE-590, CWE-591, CWE-619, CWE-690, CWE-761, CWE-762, CWE-763, CWE-770, CWE-771, CWE-774, CWE-789, CWE-822, CWE-823, CWE-824, CWE-825, CWE-843, CWE-908, CWE-1098, CWE-1257, CWE-1260, CWE-1271, CWE-1274, CWE-1282, CWE-1325, CWE-1330, CWE-1335

### `authn-authz-boundary-predicate` -- 40 ids

Authn/authz boundary predicate (no endpoint/route + auth-decision concept beyond the existing CWE-862/863/306/287/269/276 join).

CWE-200, CWE-277, CWE-278, CWE-279, CWE-280, CWE-281, CWE-284, CWE-285, CWE-346, CWE-359, CWE-378, CWE-379, CWE-384, CWE-425, CWE-497, CWE-501, CWE-521, CWE-527, CWE-528, CWE-529, CWE-530, CWE-612, CWE-613, CWE-620, CWE-640, CWE-645, CWE-650, CWE-654, CWE-732, CWE-782, CWE-921, CWE-1191, CWE-1193, CWE-1220, CWE-1262, CWE-1263, CWE-1280, CWE-1317, CWE-1334, CWE-1385

### `hardware-firmware-model` -- 33 ids

Hardware/firmware model (no physical/electrical/silicon representation).

CWE-489, CWE-1189, CWE-1192, CWE-1221, CWE-1222, CWE-1233, CWE-1234, CWE-1239, CWE-1245, CWE-1247, CWE-1248, CWE-1252, CWE-1255, CWE-1256, CWE-1276, CWE-1277, CWE-1278, CWE-1299, CWE-1300, CWE-1301, CWE-1302, CWE-1304, CWE-1312, CWE-1313, CWE-1315, CWE-1318, CWE-1319, CWE-1326, CWE-1331, CWE-1338, CWE-1351, CWE-1384, CWE-1429

### `crypto-primitive-model` -- 29 ids

Cryptographic-primitive model (no cipher/key/RNG/certificate-chain representation).

CWE-5, CWE-295, CWE-311, CWE-323, CWE-325, CWE-326, CWE-327, CWE-328, CWE-330, CWE-331, CWE-332, CWE-333, CWE-334, CWE-335, CWE-336, CWE-337, CWE-338, CWE-342, CWE-343, CWE-347, CWE-649, CWE-759, CWE-760, CWE-1204, CWE-1240, CWE-1241, CWE-1279, CWE-1394, CWE-1431

### `concurrency-scheduling-model` -- 22 ids

Concurrency/scheduling model (no synchronization/thread/signal-ordering representation).

CWE-383, CWE-413, CWE-432, CWE-543, CWE-558, CWE-567, CWE-572, CWE-574, CWE-585, CWE-609, CWE-662, CWE-663, CWE-667, CWE-764, CWE-765, CWE-820, CWE-821, CWE-833, CWE-1058, CWE-1096, CWE-1264, CWE-1322

### `resource-exhaustion-model` -- 14 ids

Resource-lifetime/exhaustion model (no allocation-vs-limit or lifecycle-phase representation).

CWE-400, CWE-403, CWE-405, CWE-408, CWE-409, CWE-664, CWE-666, CWE-772, CWE-773, CWE-775, CWE-826, CWE-832, CWE-834, CWE-910

### `environment-config-model` -- 11 ids

Environment/configuration model (no deployment-config or environment-variable representation).

CWE-6, CWE-7, CWE-8, CWE-11, CWE-12, CWE-15, CWE-260, CWE-430, CWE-560, CWE-1051, CWE-1269

### `filesystem-semantics-model` -- 10 ids

Filesystem link/equivalence semantics (symlink/hardlink/ADS/device-name resolution; distinct mechanism from the already-checkable CWE-22 path-traversal join).

CWE-41, CWE-59, CWE-61, CWE-62, CWE-65, CWE-66, CWE-67, CWE-69, CWE-72, CWE-641

### `malicious-code-taxonomy` -- 8 ids

Malicious-code taxonomy (Trojan/virus/worm/spyware/logic-bomb/covert-channel; a malware classification, not a coding-pattern weakness).

CWE-506, CWE-507, CWE-508, CWE-509, CWE-510, CWE-511, CWE-512, CWE-514

### `secure-design-principle-model` -- 7 ids

Secure-design meta-principle (economy of mechanism, complete mediation, psychological acceptability; a design heuristic, not a detectable flow pattern).

CWE-636, CWE-637, CWE-638, CWE-653, CWE-655, CWE-656, CWE-657

### `content-type-sink` -- 4 ids

Content-type validation sink (beyond the existing CWE-434 join).

CWE-194, CWE-611, CWE-616, CWE-646

### `logging-audit-model` -- 4 ids

Logging/audit-trail model (no log-sink or audit-completeness representation).

CWE-223, CWE-532, CWE-778, CWE-779

### `network-protocol-model` -- 4 ids

Network/protocol model (no packet/handshake/routing representation).

CWE-246, CWE-406, CWE-577, CWE-605

### `ui-presentation-model` -- 3 ids

UI/presentation model (no rendered-surface or user-perception representation).

CWE-451, CWE-549, CWE-1007

## Duplicate-of index (child id -> checkable parent it duplicates)

| Checkable parent | Duplicate children (count) |
|---|---|
| CWE-20 | (12) CWE-102, CWE-105, CWE-106, CWE-108, CWE-109, CWE-129, CWE-180, CWE-181, CWE-554, CWE-622, CWE-781, CWE-1174 |
| CWE-22 | (18) CWE-23, CWE-24, CWE-25, CWE-26, CWE-27, CWE-28, CWE-29, CWE-30, CWE-31, CWE-32, CWE-33, CWE-34, CWE-35, CWE-36, CWE-37, CWE-38, CWE-39, CWE-40 |
| CWE-77 | (1) CWE-88 |
| CWE-79 | (8) CWE-80, CWE-81, CWE-82, CWE-83, CWE-84, CWE-85, CWE-86, CWE-87 |
| CWE-89 | (1) CWE-564 |
| CWE-94 | (3) CWE-95, CWE-96, CWE-97 |
| CWE-119 | (8) CWE-121, CWE-122, CWE-124, CWE-415, CWE-786, CWE-788, CWE-805, CWE-806 |
| CWE-125 | (2) CWE-126, CWE-127 |
| CWE-190 | (1) CWE-680 |
| CWE-269 | (16) CWE-9, CWE-250, CWE-266, CWE-267, CWE-268, CWE-270, CWE-271, CWE-272, CWE-273, CWE-274, CWE-520, CWE-556, CWE-623, CWE-648, CWE-1022, CWE-1268 |
| CWE-287 | (25) CWE-13, CWE-258, CWE-289, CWE-290, CWE-291, CWE-293, CWE-294, CWE-297, CWE-298, CWE-301, CWE-302, CWE-303, CWE-304, CWE-305, CWE-307, CWE-308, CWE-309, CWE-350, CWE-370, CWE-555, CWE-593, CWE-599, CWE-603, CWE-836, CWE-1390 |
| CWE-306 | (2) CWE-288, CWE-322 |
| CWE-362 | (12) CWE-363, CWE-364, CWE-366, CWE-367, CWE-368, CWE-421, CWE-479, CWE-689, CWE-828, CWE-831, CWE-1223, CWE-1298 |
| CWE-639 | (1) CWE-566 |
| CWE-787 | (3) CWE-120, CWE-123, CWE-785 |
| CWE-798 | (2) CWE-259, CWE-321 |
| CWE-862 | (1) CWE-939 |
| CWE-863 | (20) CWE-42, CWE-43, CWE-44, CWE-45, CWE-46, CWE-47, CWE-48, CWE-49, CWE-50, CWE-51, CWE-52, CWE-53, CWE-54, CWE-55, CWE-56, CWE-57, CWE-58, CWE-551, CWE-647, CWE-942 |
| CWE-922 | (7) CWE-313, CWE-314, CWE-315, CWE-316, CWE-317, CWE-318, CWE-526 |

## Checkable index (already in `std.cwe` CWE_CATALOG)

| CWE id | Name | Existing catalog join |
|---|---|---|
| CWE-20 | Improper Input Validation | generic precondition (improper input validation) |
| CWE-22 | Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal') | filesystem-path sink |
| CWE-77 | Improper Neutralization of Special Elements used in a Command ('Command Injection') | duplicate parent of CWE-78 (generic command injection) |
| CWE-78 | Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection') | exec (OS command sink) |
| CWE-79 | Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting') | output_encoding (XSS sink) |
| CWE-89 | Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection') | sql (query sink) |
| CWE-94 | Improper Control of Generation of Code ('Code Injection') | exec (code injection, reuses CWE-78 join) |
| CWE-119 | Improper Restriction of Operations within the Bounds of a Memory Buffer | memory/buffer bounds (improper restriction of buffer ops) |
| CWE-125 | Out-of-bounds Read | memory/buffer read (out-of-bounds read) |
| CWE-190 | Integer Overflow or Wraparound | arithmetic-width model (integer overflow) |
| CWE-269 | Improper Privilege Management | endpoint/authz predicate (improper privilege management) |
| CWE-276 | Incorrect Default Permissions | default permissions predicate |
| CWE-287 | Improper Authentication | authn-boundary predicate (improper authentication) |
| CWE-306 | Missing Authentication for Critical Function | endpoint/authn-boundary (missing authentication) |
| CWE-352 | Cross-Site Request Forgery (CSRF) | state-changing endpoint + ambient authority (CSRF) |
| CWE-362 | Concurrent Execution using Shared Resource with Improper Synchronization ('Race Condition') | synchronization/scheduling model (race condition) |
| CWE-416 | Use After Free | memory/allocator (use after free) |
| CWE-434 | Unrestricted Upload of File with Dangerous Type | content-type-validation sink (unrestricted upload) |
| CWE-476 | NULL Pointer Dereference | memory/pointer (NULL dereference) |
| CWE-502 | Deserialization of Untrusted Data | deserializer sink |
| CWE-639 | Authorization Bypass Through User-Controlled Key | sql (authorization bypass via user-controlled key, reuses CWE-89 join) |
| CWE-787 | Out-of-bounds Write | memory/buffer write (out-of-bounds write) |
| CWE-798 | Use of Hard-coded Credentials | Secret-labeled value at low-clearance node (hardcoded creds) |
| CWE-862 | Missing Authorization | endpoint/authz predicate (missing authorization) |
| CWE-863 | Incorrect Authorization | authz-boundary predicate (incorrect authorization) |
| CWE-918 | Server-Side Request Forgery (SSRF) | network-request target (SSRF) |
| CWE-922 | Insecure Storage of Sensitive Information | clearance/storage lattice (insecure storage) |

## DENOMINATOR MANIFEST

Machine-readable: one line per CWE id, `CWE-<id>|<abstraction>|<disposition>`.
Parents (within View 1000) follow as `|parents:<id,id,...>` (empty for the
10 Pillar roots). Disposition tags: `checkable:<detail>`,
`duplicate-of:CWE-<id>`, `out-of-scope:<bucket>`.

```
CWE-5|Variant|out-of-scope:crypto-primitive-model|parents:319|name:J2EE Misconfiguration: Data Transmission Without Encryption
CWE-6|Variant|out-of-scope:environment-config-model|parents:334|name:J2EE Misconfiguration: Insufficient Session-ID Length
CWE-7|Variant|out-of-scope:environment-config-model|parents:756|name:J2EE Misconfiguration: Missing Custom Error Page
CWE-8|Variant|out-of-scope:environment-config-model|parents:668|name:J2EE Misconfiguration: Entity Bean Declared Remote
CWE-9|Variant|duplicate-of:CWE-269|parents:266|name:J2EE Misconfiguration: Weak Access Permissions for EJB Methods
CWE-11|Variant|out-of-scope:environment-config-model|parents:489|name:ASP.NET Misconfiguration: Creating Debug Binary
CWE-12|Variant|out-of-scope:environment-config-model|parents:756|name:ASP.NET Misconfiguration: Missing Custom Error Page
CWE-13|Variant|duplicate-of:CWE-287|parents:260|name:ASP.NET Misconfiguration: Password in Configuration File
CWE-14|Variant|out-of-scope:memory-model|parents:733|name:Compiler Removal of Code to Clear Buffers
CWE-15|Base|out-of-scope:environment-config-model|parents:642,610|name:External Control of System or Configuration Setting
CWE-20|Class|checkable:generic precondition (improper input validation)|parents:707|name:Improper Input Validation
CWE-22|Base|checkable:filesystem-path sink|parents:706|name:Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')
CWE-23|Base|duplicate-of:CWE-22|parents:22|name:Relative Path Traversal
CWE-24|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '../filedir'
CWE-25|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '/../filedir'
CWE-26|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '/dir/../filename'
CWE-27|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: 'dir/../../filename'
CWE-28|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '..\filedir'
CWE-29|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '\..\filename'
CWE-30|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '\dir\..\filename'
CWE-31|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: 'dir\..\..\filename'
CWE-32|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '...' (Triple Dot)
CWE-33|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '....' (Multiple Dot)
CWE-34|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '....//'
CWE-35|Variant|duplicate-of:CWE-22|parents:23|name:Path Traversal: '.../...//'
CWE-36|Base|duplicate-of:CWE-22|parents:22|name:Absolute Path Traversal
CWE-37|Variant|duplicate-of:CWE-22|parents:36,160|name:Path Traversal: '/absolute/pathname/here'
CWE-38|Variant|duplicate-of:CWE-22|parents:36|name:Path Traversal: '\absolute\pathname\here'
CWE-39|Variant|duplicate-of:CWE-22|parents:36|name:Path Traversal: 'C:dirname'
CWE-40|Variant|duplicate-of:CWE-22|parents:36|name:Path Traversal: '\\UNC\share\name\' (Windows UNC Share)
CWE-41|Base|out-of-scope:filesystem-semantics-model|parents:706,863,1390|name:Improper Resolution of Path Equivalence
CWE-42|Variant|duplicate-of:CWE-863|parents:41,162|name:Path Equivalence: 'filename.' (Trailing Dot)
CWE-43|Variant|duplicate-of:CWE-863|parents:42,163|name:Path Equivalence: 'filename....' (Multiple Trailing Dot)
CWE-44|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: 'file.name' (Internal Dot)
CWE-45|Variant|duplicate-of:CWE-863|parents:44,165|name:Path Equivalence: 'file...name' (Multiple Internal Dot)
CWE-46|Variant|duplicate-of:CWE-863|parents:41,162|name:Path Equivalence: 'filename ' (Trailing Space)
CWE-47|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: ' filename' (Leading Space)
CWE-48|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: 'file name' (Internal Whitespace)
CWE-49|Variant|duplicate-of:CWE-863|parents:41,162|name:Path Equivalence: 'filename/' (Trailing Slash)
CWE-50|Variant|duplicate-of:CWE-863|parents:41,161|name:Path Equivalence: '//multiple/leading/slash'
CWE-51|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: '/multiple//internal/slash'
CWE-52|Variant|duplicate-of:CWE-863|parents:41,163|name:Path Equivalence: '/multiple/trailing/slash//'
CWE-53|Variant|duplicate-of:CWE-863|parents:41,165|name:Path Equivalence: '\multiple\\internal\backslash'
CWE-54|Variant|duplicate-of:CWE-863|parents:41,162|name:Path Equivalence: 'filedir\' (Trailing Backslash)
CWE-55|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: '/./' (Single Dot Directory)
CWE-56|Variant|duplicate-of:CWE-863|parents:41,155|name:Path Equivalence: 'filedir*' (Wildcard)
CWE-57|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: 'fakedir/../realdir/filename'
CWE-58|Variant|duplicate-of:CWE-863|parents:41|name:Path Equivalence: Windows 8.3 Filename
CWE-59|Base|out-of-scope:filesystem-semantics-model|parents:706|name:Improper Link Resolution Before File Access ('Link Following')
CWE-61|Compound|out-of-scope:filesystem-semantics-model|parents:59|name:UNIX Symbolic Link (Symlink) Following
CWE-62|Variant|out-of-scope:filesystem-semantics-model|parents:59|name:UNIX Hard Link
CWE-64|Variant|out-of-scope:generic-precondition-model|parents:59|name:Windows Shortcut Following (.LNK)
CWE-65|Variant|out-of-scope:filesystem-semantics-model|parents:59|name:Windows Hard Link
CWE-66|Base|out-of-scope:filesystem-semantics-model|parents:706|name:Improper Handling of File Names that Identify Virtual Resources
CWE-67|Variant|out-of-scope:filesystem-semantics-model|parents:66|name:Improper Handling of Windows Device Names
CWE-69|Variant|out-of-scope:filesystem-semantics-model|parents:66|name:Improper Handling of Windows ::DATA Alternate Data Stream
CWE-72|Variant|out-of-scope:filesystem-semantics-model|parents:66|name:Improper Handling of Apple HFS+ Alternate Data Stream Path
CWE-73|Base|out-of-scope:generic-precondition-model|parents:642,610|name:External Control of File Name or Path
CWE-74|Class|out-of-scope:sink-classification-model|parents:707|name:Improper Neutralization of Special Elements in Output Used by a Downstream Component ('Injection')
CWE-75|Class|out-of-scope:sink-classification-model|parents:74|name:Failure to Sanitize Special Elements into a Different Plane (Special Element Injection)
CWE-76|Base|out-of-scope:sink-classification-model|parents:75|name:Improper Neutralization of Equivalent Special Elements
CWE-77|Class|checkable:duplicate parent of CWE-78 (generic command injection)|parents:74|name:Improper Neutralization of Special Elements used in a Command ('Command Injection')
CWE-78|Base|checkable:exec (OS command sink)|parents:77|name:Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
CWE-79|Base|checkable:output_encoding (XSS sink)|parents:74|name:Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')
CWE-80|Variant|duplicate-of:CWE-79|parents:79|name:Improper Neutralization of Script-Related HTML Tags in a Web Page (Basic XSS)
CWE-81|Variant|duplicate-of:CWE-79|parents:79|name:Improper Neutralization of Script in an Error Message Web Page
CWE-82|Variant|duplicate-of:CWE-79|parents:83|name:Improper Neutralization of Script in Attributes of IMG Tags in a Web Page
CWE-83|Variant|duplicate-of:CWE-79|parents:79|name:Improper Neutralization of Script in Attributes in a Web Page
CWE-84|Variant|duplicate-of:CWE-79|parents:79|name:Improper Neutralization of Encoded URI Schemes in a Web Page
CWE-85|Variant|duplicate-of:CWE-79|parents:79|name:Doubled Character XSS Manipulations
CWE-86|Variant|duplicate-of:CWE-79|parents:79,436|name:Improper Neutralization of Invalid Characters in Identifiers in Web Pages
CWE-87|Variant|duplicate-of:CWE-79|parents:79|name:Improper Neutralization of Alternate XSS Syntax
CWE-88|Base|duplicate-of:CWE-77|parents:77|name:Improper Neutralization of Argument Delimiters in a Command ('Argument Injection')
CWE-89|Base|checkable:sql (query sink)|parents:943|name:Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')
CWE-90|Base|out-of-scope:sink-classification-model|parents:943|name:Improper Neutralization of Special Elements used in an LDAP Query ('LDAP Injection')
CWE-91|Base|out-of-scope:sink-classification-model|parents:74|name:XML Injection (aka Blind XPath Injection)
CWE-93|Base|out-of-scope:sink-classification-model|parents:74|name:Improper Neutralization of CRLF Sequences ('CRLF Injection')
CWE-94|Base|checkable:exec (code injection, reuses CWE-78 join)|parents:74,913|name:Improper Control of Generation of Code ('Code Injection')
CWE-95|Variant|duplicate-of:CWE-94|parents:94|name:Improper Neutralization of Directives in Dynamically Evaluated Code ('Eval Injection')
CWE-96|Base|duplicate-of:CWE-94|parents:94|name:Improper Neutralization of Directives in Statically Saved Code ('Static Code Injection')
CWE-97|Variant|duplicate-of:CWE-94|parents:96|name:Improper Neutralization of Server-Side Includes (SSI) Within a Web Page
CWE-98|Variant|out-of-scope:generic-precondition-model|parents:706,829|name:Improper Control of Filename for Include/Require Statement in PHP Program ('PHP Remote File Inclusion')
CWE-99|Class|out-of-scope:sink-classification-model|parents:74|name:Improper Control of Resource Identifiers ('Resource Injection')
CWE-102|Variant|duplicate-of:CWE-20|parents:694,1173|name:Struts: Duplicate Validation Forms
CWE-103|Variant|out-of-scope:language-runtime-semantics-model|parents:573|name:Struts: Incomplete validate() Method Definition
CWE-104|Variant|out-of-scope:language-runtime-semantics-model|parents:573|name:Struts: Form Bean Does Not Extend Validation Class
CWE-105|Variant|duplicate-of:CWE-20|parents:1173|name:Struts: Form Field Without Validator
CWE-106|Variant|duplicate-of:CWE-20|parents:1173|name:Struts: Plug-in Framework not in Use
CWE-107|Variant|out-of-scope:language-runtime-semantics-model|parents:1164|name:Struts: Unused Validation Form
CWE-108|Variant|duplicate-of:CWE-20|parents:1173|name:Struts: Unvalidated Action Form
CWE-109|Variant|duplicate-of:CWE-20|parents:1173|name:Struts: Validator Turned Off
CWE-110|Variant|out-of-scope:language-runtime-semantics-model|parents:1164|name:Struts: Validator Without Form Field
CWE-111|Variant|out-of-scope:language-runtime-semantics-model|parents:695|name:Direct Use of Unsafe JNI
CWE-112|Base|out-of-scope:generic-precondition-model|parents:1286|name:Missing XML Validation
CWE-113|Variant|out-of-scope:sink-classification-model|parents:93,436|name:Improper Neutralization of CRLF Sequences in HTTP Headers ('HTTP Request/Response Splitting')
CWE-114|Class|out-of-scope:generic-precondition-model|parents:73|name:Process Control
CWE-115|Base|out-of-scope:generic-precondition-model|parents:436|name:Misinterpretation of Input
CWE-116|Class|out-of-scope:sink-classification-model|parents:707|name:Improper Encoding or Escaping of Output
CWE-117|Base|out-of-scope:sink-classification-model|parents:116|name:Improper Output Neutralization for Logs
CWE-118|Class|out-of-scope:generic-precondition-model|parents:664|name:Incorrect Access of Indexable Resource ('Range Error')
CWE-119|Class|checkable:memory/buffer bounds (improper restriction of buffer ops)|parents:118|name:Improper Restriction of Operations within the Bounds of a Memory Buffer
CWE-120|Base|duplicate-of:CWE-787|parents:787|name:Buffer Copy without Checking Size of Input ('Classic Buffer Overflow')
CWE-121|Variant|duplicate-of:CWE-119|parents:788,787|name:Stack-based Buffer Overflow
CWE-122|Variant|duplicate-of:CWE-119|parents:788,787|name:Heap-based Buffer Overflow
CWE-123|Base|duplicate-of:CWE-787|parents:787|name:Write-what-where Condition
CWE-124|Base|duplicate-of:CWE-119|parents:786,787|name:Buffer Underwrite ('Buffer Underflow')
CWE-125|Base|checkable:memory/buffer read (out-of-bounds read)|parents:119|name:Out-of-bounds Read
CWE-126|Variant|duplicate-of:CWE-125|parents:125,788|name:Buffer Over-read
CWE-127|Variant|duplicate-of:CWE-125|parents:125,786|name:Buffer Under-read
CWE-128|Base|out-of-scope:generic-precondition-model|parents:682|name:Wrap-around Error
CWE-129|Variant|duplicate-of:CWE-20|parents:1285|name:Improper Validation of Array Index
CWE-130|Base|out-of-scope:generic-precondition-model|parents:240|name:Improper Handling of Length Parameter Inconsistency
CWE-131|Base|out-of-scope:memory-model|parents:682|name:Incorrect Calculation of Buffer Size
CWE-134|Base|out-of-scope:sink-classification-model|parents:668|name:Use of Externally-Controlled Format String
CWE-135|Base|out-of-scope:generic-precondition-model|parents:682|name:Incorrect Calculation of Multi-Byte String Length
CWE-138|Class|out-of-scope:sink-classification-model|parents:707|name:Improper Neutralization of Special Elements
CWE-140|Base|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Delimiters
CWE-141|Variant|out-of-scope:sink-classification-model|parents:140|name:Improper Neutralization of Parameter/Argument Delimiters
CWE-142|Variant|out-of-scope:sink-classification-model|parents:140|name:Improper Neutralization of Value Delimiters
CWE-143|Variant|out-of-scope:sink-classification-model|parents:140|name:Improper Neutralization of Record Delimiters
CWE-144|Variant|out-of-scope:sink-classification-model|parents:140|name:Improper Neutralization of Line Delimiters
CWE-145|Variant|out-of-scope:sink-classification-model|parents:140|name:Improper Neutralization of Section Delimiters
CWE-146|Variant|out-of-scope:sink-classification-model|parents:140|name:Improper Neutralization of Expression/Command Delimiters
CWE-147|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Input Terminators
CWE-148|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Input Leaders
CWE-149|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Quoting Syntax
CWE-150|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Escape, Meta, or Control Sequences
CWE-151|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Comment Delimiters
CWE-152|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Macro Symbols
CWE-153|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Substitution Characters
CWE-154|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Variable Name Delimiters
CWE-155|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Wildcards or Matching Symbols
CWE-156|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Whitespace
CWE-157|Variant|out-of-scope:sink-classification-model|parents:138|name:Failure to Sanitize Paired Delimiters
CWE-158|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Null Byte or NUL Character
CWE-159|Class|out-of-scope:sink-classification-model|parents:138|name:Improper Handling of Invalid Use of Special Elements
CWE-160|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Leading Special Elements
CWE-161|Variant|out-of-scope:sink-classification-model|parents:160|name:Improper Neutralization of Multiple Leading Special Elements
CWE-162|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Trailing Special Elements
CWE-163|Variant|out-of-scope:sink-classification-model|parents:162|name:Improper Neutralization of Multiple Trailing Special Elements
CWE-164|Variant|out-of-scope:sink-classification-model|parents:138|name:Improper Neutralization of Internal Special Elements
CWE-165|Variant|out-of-scope:sink-classification-model|parents:164|name:Improper Neutralization of Multiple Internal Special Elements
CWE-166|Base|out-of-scope:sink-classification-model|parents:159,228|name:Improper Handling of Missing Special Element
CWE-167|Base|out-of-scope:sink-classification-model|parents:159,228|name:Improper Handling of Additional Special Element
CWE-168|Base|out-of-scope:sink-classification-model|parents:159,228|name:Improper Handling of Inconsistent Special Elements
CWE-170|Base|out-of-scope:generic-precondition-model|parents:707|name:Improper Null Termination
CWE-172|Class|out-of-scope:sink-classification-model|parents:707|name:Encoding Error
CWE-173|Variant|out-of-scope:sink-classification-model|parents:172|name:Improper Handling of Alternate Encoding
CWE-174|Variant|out-of-scope:generic-precondition-model|parents:172,675|name:Double Decoding of the Same Data
CWE-175|Variant|out-of-scope:sink-classification-model|parents:172|name:Improper Handling of Mixed Encoding
CWE-176|Variant|out-of-scope:sink-classification-model|parents:172|name:Improper Handling of Unicode Encoding
CWE-177|Variant|out-of-scope:sink-classification-model|parents:172|name:Improper Handling of URL Encoding (Hex Encoding)
CWE-178|Base|out-of-scope:generic-precondition-model|parents:706|name:Improper Handling of Case Sensitivity
CWE-179|Base|out-of-scope:generic-precondition-model|parents:20,696|name:Incorrect Behavior Order: Early Validation
CWE-180|Variant|duplicate-of:CWE-20|parents:179|name:Incorrect Behavior Order: Validate Before Canonicalize
CWE-181|Variant|duplicate-of:CWE-20|parents:179|name:Incorrect Behavior Order: Validate Before Filter
CWE-182|Base|out-of-scope:generic-precondition-model|parents:707|name:Collapse of Data into Unsafe Value
CWE-183|Base|out-of-scope:generic-precondition-model|parents:697|name:Permissive List of Allowed Inputs
CWE-184|Base|out-of-scope:generic-precondition-model|parents:693,1023|name:Incomplete List of Disallowed Inputs
CWE-185|Class|out-of-scope:sink-classification-model|parents:697|name:Incorrect Regular Expression
CWE-186|Base|out-of-scope:sink-classification-model|parents:185|name:Overly Restrictive Regular Expression
CWE-187|Variant|out-of-scope:generic-precondition-model|parents:1023|name:Partial String Comparison
CWE-188|Base|out-of-scope:memory-model|parents:1105,435|name:Reliance on Data/Memory Layout
CWE-190|Base|checkable:arithmetic-width model (integer overflow)|parents:682|name:Integer Overflow or Wraparound
CWE-191|Base|out-of-scope:memory-model|parents:682|name:Integer Underflow (Wrap or Wraparound)
CWE-192|Variant|out-of-scope:memory-model|parents:681|name:Integer Coercion Error
CWE-193|Base|out-of-scope:memory-model|parents:682|name:Off-by-one Error
CWE-194|Variant|out-of-scope:content-type-sink|parents:681|name:Unexpected Sign Extension
CWE-195|Variant|out-of-scope:memory-model|parents:681|name:Signed to Unsigned Conversion Error
CWE-196|Variant|out-of-scope:generic-precondition-model|parents:681|name:Unsigned to Signed Conversion Error
CWE-197|Base|out-of-scope:generic-precondition-model|parents:681|name:Numeric Truncation Error
CWE-198|Variant|out-of-scope:generic-precondition-model|parents:188|name:Use of Incorrect Byte Ordering
CWE-200|Class|out-of-scope:authn-authz-boundary-predicate|parents:668|name:Exposure of Sensitive Information to an Unauthorized Actor
CWE-201|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:200|name:Insertion of Sensitive Information Into Sent Data
CWE-202|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1230|name:Exposure of Sensitive Information Through Data Queries
CWE-203|Base|out-of-scope:generic-precondition-model|parents:200|name:Observable Discrepancy
CWE-204|Base|out-of-scope:generic-precondition-model|parents:203|name:Observable Response Discrepancy
CWE-205|Base|out-of-scope:generic-precondition-model|parents:203|name:Observable Behavioral Discrepancy
CWE-206|Variant|out-of-scope:generic-precondition-model|parents:205|name:Observable Internal Behavioral Discrepancy
CWE-207|Variant|out-of-scope:generic-precondition-model|parents:205|name:Observable Behavioral Discrepancy With Equivalent Products
CWE-208|Base|out-of-scope:generic-precondition-model|parents:203|name:Observable Timing Discrepancy
CWE-209|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:200,755|name:Generation of Error Message Containing Sensitive Information
CWE-210|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:209|name:Self-generated Error Message Containing Sensitive Information
CWE-211|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:209|name:Externally-Generated Error Message Containing Sensitive Information
CWE-212|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:669|name:Improper Removal of Sensitive Information Before Storage or Transfer
CWE-213|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:200|name:Exposure of Sensitive Information Due to Incompatible Policies
CWE-214|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:497|name:Invocation of Process Using Visible Sensitive Information
CWE-215|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:200|name:Insertion of Sensitive Information Into Debugging Code
CWE-219|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:552|name:Storage of File with Sensitive Data Under Web Root
CWE-220|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:552|name:Storage of File With Sensitive Data Under FTP Root
CWE-221|Class|out-of-scope:generic-precondition-model|parents:664|name:Information Loss or Omission
CWE-222|Base|out-of-scope:generic-precondition-model|parents:221|name:Truncation of Security-relevant Information
CWE-223|Base|out-of-scope:logging-audit-model|parents:221|name:Omission of Security-relevant Information
CWE-224|Base|out-of-scope:generic-precondition-model|parents:221|name:Obscured Security-relevant Information by Alternate Name
CWE-226|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:459,212|name:Sensitive Information in Resource Not Removed Before Reuse
CWE-228|Class|out-of-scope:generic-precondition-model|parents:703,707|name:Improper Handling of Syntactically Invalid Structure
CWE-229|Base|out-of-scope:generic-precondition-model|parents:228|name:Improper Handling of Values
CWE-230|Variant|out-of-scope:generic-precondition-model|parents:229|name:Improper Handling of Missing Values
CWE-231|Variant|out-of-scope:generic-precondition-model|parents:229|name:Improper Handling of Extra Values
CWE-232|Variant|out-of-scope:generic-precondition-model|parents:229|name:Improper Handling of Undefined Values
CWE-233|Base|out-of-scope:generic-precondition-model|parents:228|name:Improper Handling of Parameters
CWE-234|Variant|out-of-scope:generic-precondition-model|parents:233|name:Failure to Handle Missing Parameter
CWE-235|Variant|out-of-scope:generic-precondition-model|parents:233|name:Improper Handling of Extra Parameters
CWE-236|Variant|out-of-scope:generic-precondition-model|parents:233|name:Improper Handling of Undefined Parameters
CWE-237|Base|out-of-scope:generic-precondition-model|parents:228|name:Improper Handling of Structural Elements
CWE-238|Variant|out-of-scope:generic-precondition-model|parents:237|name:Improper Handling of Incomplete Structural Elements
CWE-239|Variant|out-of-scope:generic-precondition-model|parents:237|name:Failure to Handle Incomplete Element
CWE-240|Base|out-of-scope:generic-precondition-model|parents:237,707|name:Improper Handling of Inconsistent Structural Elements
CWE-241|Base|out-of-scope:generic-precondition-model|parents:228|name:Improper Handling of Unexpected Data Type
CWE-242|Base|out-of-scope:generic-precondition-model|parents:1177|name:Use of Inherently Dangerous Function
CWE-243|Variant|out-of-scope:generic-precondition-model|parents:573,669|name:Creation of chroot Jail Without Changing Working Directory
CWE-244|Variant|out-of-scope:memory-model|parents:226|name:Improper Clearing of Heap Memory Before Release ('Heap Inspection')
CWE-245|Variant|out-of-scope:language-runtime-semantics-model|parents:695|name:J2EE Bad Practices: Direct Management of Connections
CWE-246|Variant|out-of-scope:network-protocol-model|parents:695|name:J2EE Bad Practices: Direct Use of Sockets
CWE-248|Base|out-of-scope:language-runtime-semantics-model|parents:705,755|name:Uncaught Exception
CWE-250|Base|duplicate-of:CWE-269|parents:269,657|name:Execution with Unnecessary Privileges
CWE-252|Base|out-of-scope:generic-precondition-model|parents:754|name:Unchecked Return Value
CWE-253|Base|out-of-scope:generic-precondition-model|parents:573,754|name:Incorrect Check of Function Return Value
CWE-256|Base|out-of-scope:generic-precondition-model|parents:522|name:Plaintext Storage of a Password
CWE-257|Base|out-of-scope:generic-precondition-model|parents:522|name:Storing Passwords in a Recoverable Format
CWE-258|Variant|duplicate-of:CWE-287|parents:260,521|name:Empty Password in Configuration File
CWE-259|Variant|duplicate-of:CWE-798|parents:798|name:Use of Hard-coded Password
CWE-260|Base|out-of-scope:environment-config-model|parents:522|name:Password in Configuration File
CWE-261|Base|out-of-scope:sink-classification-model|parents:522|name:Weak Encoding for Password
CWE-262|Base|out-of-scope:generic-precondition-model|parents:1390|name:Not Using Password Aging
CWE-263|Base|out-of-scope:generic-precondition-model|parents:1390|name:Password Aging with Long Expiration
CWE-266|Base|duplicate-of:CWE-269|parents:269|name:Incorrect Privilege Assignment
CWE-267|Base|duplicate-of:CWE-269|parents:269|name:Privilege Defined With Unsafe Actions
CWE-268|Base|duplicate-of:CWE-269|parents:269|name:Privilege Chaining
CWE-269|Class|checkable:endpoint/authz predicate (improper privilege management)|parents:284|name:Improper Privilege Management
CWE-270|Base|duplicate-of:CWE-269|parents:269|name:Privilege Context Switching Error
CWE-271|Class|duplicate-of:CWE-269|parents:269|name:Privilege Dropping / Lowering Errors
CWE-272|Base|duplicate-of:CWE-269|parents:271|name:Least Privilege Violation
CWE-273|Base|duplicate-of:CWE-269|parents:754,271|name:Improper Check for Dropped Privileges
CWE-274|Base|duplicate-of:CWE-269|parents:755,269|name:Improper Handling of Insufficient Privileges
CWE-276|Base|checkable:default permissions predicate|parents:732|name:Incorrect Default Permissions
CWE-277|Variant|out-of-scope:authn-authz-boundary-predicate|parents:732|name:Insecure Inherited Permissions
CWE-278|Variant|out-of-scope:authn-authz-boundary-predicate|parents:732|name:Insecure Preserved Inherited Permissions
CWE-279|Variant|out-of-scope:authn-authz-boundary-predicate|parents:732|name:Incorrect Execution-Assigned Permissions
CWE-280|Base|out-of-scope:authn-authz-boundary-predicate|parents:755|name:Improper Handling of Insufficient Permissions or Privileges
CWE-281|Base|out-of-scope:authn-authz-boundary-predicate|parents:732|name:Improper Preservation of Permissions
CWE-282|Class|out-of-scope:generic-precondition-model|parents:284|name:Improper Ownership Management
CWE-283|Base|out-of-scope:generic-precondition-model|parents:282|name:Unverified Ownership
CWE-284|Pillar|out-of-scope:authn-authz-boundary-predicate|parents:-|name:Improper Access Control
CWE-285|Class|out-of-scope:authn-authz-boundary-predicate|parents:284|name:Improper Authorization
CWE-286|Class|out-of-scope:generic-precondition-model|parents:284|name:Incorrect User Management
CWE-287|Class|checkable:authn-boundary predicate (improper authentication)|parents:284|name:Improper Authentication
CWE-288|Base|duplicate-of:CWE-306|parents:306|name:Authentication Bypass Using an Alternate Path or Channel
CWE-289|Base|duplicate-of:CWE-287|parents:1390|name:Authentication Bypass by Alternate Name
CWE-290|Base|duplicate-of:CWE-287|parents:1390|name:Authentication Bypass by Spoofing
CWE-291|Variant|duplicate-of:CWE-287|parents:290,923|name:Reliance on IP Address for Authentication
CWE-293|Variant|duplicate-of:CWE-287|parents:290|name:Using Referer Field for Authentication
CWE-294|Base|duplicate-of:CWE-287|parents:1390|name:Authentication Bypass by Capture-replay
CWE-295|Base|out-of-scope:crypto-primitive-model|parents:287|name:Improper Certificate Validation
CWE-296|Base|out-of-scope:generic-precondition-model|parents:295,573|name:Improper Following of a Certificate's Chain of Trust
CWE-297|Variant|duplicate-of:CWE-287|parents:923,295|name:Improper Validation of Certificate with Host Mismatch
CWE-298|Variant|duplicate-of:CWE-287|parents:295,672|name:Improper Validation of Certificate Expiration
CWE-299|Base|out-of-scope:generic-precondition-model|parents:295,404|name:Improper Check for Certificate Revocation
CWE-300|Class|out-of-scope:generic-precondition-model|parents:923|name:Channel Accessible by Non-Endpoint
CWE-301|Base|duplicate-of:CWE-287|parents:1390|name:Reflection Attack in an Authentication Protocol
CWE-302|Base|duplicate-of:CWE-287|parents:1390,807|name:Authentication Bypass by Assumed-Immutable Data
CWE-303|Base|duplicate-of:CWE-287|parents:1390|name:Incorrect Implementation of Authentication Algorithm
CWE-304|Base|duplicate-of:CWE-287|parents:303,573|name:Missing Critical Step in Authentication
CWE-305|Base|duplicate-of:CWE-287|parents:1390|name:Authentication Bypass by Primary Weakness
CWE-306|Base|checkable:endpoint/authn-boundary (missing authentication)|parents:287|name:Missing Authentication for Critical Function
CWE-307|Base|duplicate-of:CWE-287|parents:1390,799|name:Improper Restriction of Excessive Authentication Attempts
CWE-308|Base|duplicate-of:CWE-287|parents:1390,654|name:Use of Single-factor Authentication
CWE-309|Base|duplicate-of:CWE-287|parents:1390,654|name:Use of Password System for Primary Authentication
CWE-311|Class|out-of-scope:crypto-primitive-model|parents:693|name:Missing Encryption of Sensitive Data
CWE-312|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:311,922|name:Cleartext Storage of Sensitive Information
CWE-313|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage in a File or on Disk
CWE-314|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage in the Registry
CWE-315|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage of Sensitive Information in a Cookie
CWE-316|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage of Sensitive Information in Memory
CWE-317|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage of Sensitive Information in GUI
CWE-318|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage of Sensitive Information in Executable
CWE-319|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:311|name:Cleartext Transmission of Sensitive Information
CWE-321|Variant|duplicate-of:CWE-798|parents:798|name:Use of Hard-coded Cryptographic Key
CWE-322|Base|duplicate-of:CWE-306|parents:306|name:Key Exchange without Entity Authentication
CWE-323|Base|out-of-scope:crypto-primitive-model|parents:344|name:Reusing a Nonce, Key Pair in Encryption
CWE-324|Base|out-of-scope:generic-precondition-model|parents:672|name:Use of a Key Past its Expiration Date
CWE-325|Base|out-of-scope:crypto-primitive-model|parents:1240,573|name:Missing Cryptographic Step
CWE-326|Class|out-of-scope:crypto-primitive-model|parents:693|name:Inadequate Encryption Strength
CWE-327|Class|out-of-scope:crypto-primitive-model|parents:693|name:Use of a Broken or Risky Cryptographic Algorithm
CWE-328|Base|out-of-scope:crypto-primitive-model|parents:326,327|name:Use of Weak Hash
CWE-329|Variant|out-of-scope:generic-precondition-model|parents:1204,573|name:Generation of Predictable IV with CBC Mode
CWE-330|Class|out-of-scope:crypto-primitive-model|parents:693|name:Use of Insufficiently Random Values
CWE-331|Base|out-of-scope:crypto-primitive-model|parents:330|name:Insufficient Entropy
CWE-332|Variant|out-of-scope:crypto-primitive-model|parents:331|name:Insufficient Entropy in PRNG
CWE-333|Variant|out-of-scope:crypto-primitive-model|parents:331,755|name:Improper Handling of Insufficient Entropy in TRNG
CWE-334|Base|out-of-scope:crypto-primitive-model|parents:330|name:Small Space of Random Values
CWE-335|Base|out-of-scope:crypto-primitive-model|parents:330|name:Incorrect Usage of Seeds in Pseudo-Random Number Generator (PRNG)
CWE-336|Variant|out-of-scope:crypto-primitive-model|parents:335|name:Same Seed in Pseudo-Random Number Generator (PRNG)
CWE-337|Variant|out-of-scope:crypto-primitive-model|parents:335|name:Predictable Seed in Pseudo-Random Number Generator (PRNG)
CWE-338|Base|out-of-scope:crypto-primitive-model|parents:330|name:Use of Cryptographically Weak Pseudo-Random Number Generator (PRNG)
CWE-339|Variant|out-of-scope:generic-precondition-model|parents:335|name:Small Seed Space in PRNG
CWE-340|Class|out-of-scope:generic-precondition-model|parents:330|name:Generation of Predictable Numbers or Identifiers
CWE-341|Base|out-of-scope:generic-precondition-model|parents:340|name:Predictable from Observable State
CWE-342|Base|out-of-scope:crypto-primitive-model|parents:340|name:Predictable Exact Value from Previous Values
CWE-343|Base|out-of-scope:crypto-primitive-model|parents:340|name:Predictable Value Range from Previous Values
CWE-344|Base|out-of-scope:generic-precondition-model|parents:330|name:Use of Invariant Value in Dynamically Changing Context
CWE-345|Class|out-of-scope:generic-precondition-model|parents:693|name:Insufficient Verification of Data Authenticity
CWE-346|Class|out-of-scope:authn-authz-boundary-predicate|parents:345,284|name:Origin Validation Error
CWE-347|Base|out-of-scope:crypto-primitive-model|parents:345|name:Improper Verification of Cryptographic Signature
CWE-348|Base|out-of-scope:generic-precondition-model|parents:345|name:Use of Less Trusted Source
CWE-349|Base|out-of-scope:generic-precondition-model|parents:345|name:Acceptance of Extraneous Untrusted Data With Trusted Data
CWE-350|Variant|duplicate-of:CWE-287|parents:290,807|name:Reliance on Reverse DNS Resolution for a Security-Critical Action
CWE-351|Base|out-of-scope:generic-precondition-model|parents:345|name:Insufficient Type Distinction
CWE-352|Compound|checkable:state-changing endpoint + ambient authority (CSRF)|parents:345|name:Cross-Site Request Forgery (CSRF)
CWE-353|Base|out-of-scope:generic-precondition-model|parents:345|name:Missing Support for Integrity Check
CWE-354|Base|out-of-scope:generic-precondition-model|parents:345,754|name:Improper Validation of Integrity Check Value
CWE-356|Base|out-of-scope:generic-precondition-model|parents:221|name:Product UI does not Warn User of Unsafe Actions
CWE-357|Base|out-of-scope:generic-precondition-model|parents:693|name:Insufficient UI Warning of Dangerous Operations
CWE-358|Base|out-of-scope:generic-precondition-model|parents:573,693|name:Improperly Implemented Security Check for Standard
CWE-359|Base|out-of-scope:authn-authz-boundary-predicate|parents:200|name:Exposure of Private Personal Information to an Unauthorized Actor
CWE-360|Base|out-of-scope:generic-precondition-model|parents:345|name:Trust of System Event Data
CWE-362|Class|checkable:synchronization/scheduling model (race condition)|parents:662|name:Concurrent Execution using Shared Resource with Improper Synchronization ('Race Condition')
CWE-363|Base|duplicate-of:CWE-362|parents:367|name:Race Condition Enabling Link Following
CWE-364|Base|duplicate-of:CWE-362|parents:362|name:Signal Handler Race Condition
CWE-366|Base|duplicate-of:CWE-362|parents:362|name:Race Condition within a Thread
CWE-367|Base|duplicate-of:CWE-362|parents:362|name:Time-of-check Time-of-use (TOCTOU) Race Condition
CWE-368|Base|duplicate-of:CWE-362|parents:362|name:Context Switching Race Condition
CWE-369|Base|out-of-scope:generic-precondition-model|parents:682|name:Divide By Zero
CWE-370|Variant|duplicate-of:CWE-287|parents:299|name:Missing Check for Certificate Revocation after Initial Check
CWE-372|Base|out-of-scope:generic-precondition-model|parents:664|name:Incomplete Internal State Distinction
CWE-374|Base|out-of-scope:generic-precondition-model|parents:668|name:Passing Mutable Objects to an Untrusted Method
CWE-375|Base|out-of-scope:generic-precondition-model|parents:668|name:Returning a Mutable Object to an Untrusted Caller
CWE-377|Class|out-of-scope:generic-precondition-model|parents:668|name:Insecure Temporary File
CWE-378|Base|out-of-scope:authn-authz-boundary-predicate|parents:377|name:Creation of Temporary File With Insecure Permissions
CWE-379|Base|out-of-scope:authn-authz-boundary-predicate|parents:377|name:Creation of Temporary File in Directory with Insecure Permissions
CWE-382|Variant|out-of-scope:language-runtime-semantics-model|parents:705|name:J2EE Bad Practices: Use of System.exit()
CWE-383|Variant|out-of-scope:concurrency-scheduling-model|parents:695|name:J2EE Bad Practices: Direct Use of Threads
CWE-384|Compound|out-of-scope:authn-authz-boundary-predicate|parents:610|name:Session Fixation
CWE-385|Base|out-of-scope:generic-precondition-model|parents:514|name:Covert Timing Channel
CWE-386|Base|out-of-scope:generic-precondition-model|parents:706|name:Symbolic Name not Mapping to Correct Object
CWE-390|Base|out-of-scope:generic-precondition-model|parents:755|name:Detection of Error Condition Without Action
CWE-391|Base|out-of-scope:generic-precondition-model|parents:754|name:Unchecked Error Condition
CWE-392|Base|out-of-scope:generic-precondition-model|parents:755,684|name:Missing Report of Error Condition
CWE-393|Base|out-of-scope:generic-precondition-model|parents:684,703|name:Return of Wrong Status Code
CWE-394|Base|out-of-scope:generic-precondition-model|parents:754|name:Unexpected Status Code or Return Value
CWE-395|Base|out-of-scope:memory-model|parents:705,755|name:Use of NullPointerException Catch to Detect NULL Pointer Dereference
CWE-396|Base|out-of-scope:language-runtime-semantics-model|parents:705,755,221|name:Declaration of Catch for Generic Exception
CWE-397|Base|out-of-scope:language-runtime-semantics-model|parents:705,221,703|name:Declaration of Throws for Generic Exception
CWE-400|Class|out-of-scope:resource-exhaustion-model|parents:664|name:Uncontrolled Resource Consumption
CWE-401|Variant|out-of-scope:memory-model|parents:772|name:Missing Release of Memory after Effective Lifetime
CWE-402|Class|out-of-scope:generic-precondition-model|parents:668|name:Transmission of Private Resources into a New Sphere ('Resource Leak')
CWE-403|Base|out-of-scope:resource-exhaustion-model|parents:402|name:Exposure of File Descriptor to Unintended Control Sphere ('File Descriptor Leak')
CWE-404|Class|out-of-scope:generic-precondition-model|parents:664|name:Improper Resource Shutdown or Release
CWE-405|Class|out-of-scope:resource-exhaustion-model|parents:400|name:Asymmetric Resource Consumption (Amplification)
CWE-406|Class|out-of-scope:network-protocol-model|parents:405|name:Insufficient Control of Network Message Volume (Network Amplification)
CWE-407|Class|out-of-scope:generic-precondition-model|parents:405|name:Inefficient Algorithmic Complexity
CWE-408|Base|out-of-scope:resource-exhaustion-model|parents:405,696|name:Incorrect Behavior Order: Early Amplification
CWE-409|Base|out-of-scope:resource-exhaustion-model|parents:405|name:Improper Handling of Highly Compressed Data (Data Amplification)
CWE-410|Class|out-of-scope:generic-precondition-model|parents:664|name:Insufficient Resource Pool
CWE-412|Base|out-of-scope:generic-precondition-model|parents:667|name:Unrestricted Externally Accessible Lock
CWE-413|Base|out-of-scope:concurrency-scheduling-model|parents:667|name:Improper Resource Locking
CWE-414|Base|out-of-scope:generic-precondition-model|parents:667|name:Missing Lock Check
CWE-415|Variant|duplicate-of:CWE-119|parents:825,1341,666|name:Double Free
CWE-416|Variant|checkable:memory/allocator (use after free)|parents:825|name:Use After Free
CWE-419|Base|out-of-scope:generic-precondition-model|parents:923|name:Unprotected Primary Channel
CWE-420|Base|out-of-scope:generic-precondition-model|parents:923|name:Unprotected Alternate Channel
CWE-421|Base|duplicate-of:CWE-362|parents:420,362|name:Race Condition During Access to Alternate Channel
CWE-422|Variant|out-of-scope:generic-precondition-model|parents:420,360|name:Unprotected Windows Messaging Channel ('Shatter')
CWE-424|Class|out-of-scope:generic-precondition-model|parents:693,638|name:Improper Protection of Alternate Path
CWE-425|Base|out-of-scope:authn-authz-boundary-predicate|parents:862,288,424|name:Direct Request ('Forced Browsing')
CWE-426|Base|out-of-scope:generic-precondition-model|parents:642,673|name:Untrusted Search Path
CWE-427|Base|out-of-scope:generic-precondition-model|parents:668|name:Uncontrolled Search Path Element
CWE-428|Base|out-of-scope:generic-precondition-model|parents:668|name:Unquoted Search Path or Element
CWE-430|Base|out-of-scope:environment-config-model|parents:691|name:Deployment of Wrong Handler
CWE-431|Base|out-of-scope:generic-precondition-model|parents:691|name:Missing Handler
CWE-432|Base|out-of-scope:concurrency-scheduling-model|parents:364|name:Dangerous Signal Handler not Disabled During Sensitive Operations
CWE-433|Variant|out-of-scope:generic-precondition-model|parents:219|name:Unparsed Raw Web Content Delivery
CWE-434|Base|checkable:content-type-validation sink (unrestricted upload)|parents:669|name:Unrestricted Upload of File with Dangerous Type
CWE-435|Pillar|out-of-scope:generic-precondition-model|parents:-|name:Improper Interaction Between Multiple Correctly-Behaving Entities
CWE-436|Class|out-of-scope:generic-precondition-model|parents:435|name:Interpretation Conflict
CWE-437|Base|out-of-scope:generic-precondition-model|parents:436|name:Incomplete Model of Endpoint Features
CWE-439|Base|out-of-scope:generic-precondition-model|parents:435|name:Behavioral Change in New Version or Environment
CWE-440|Base|out-of-scope:generic-precondition-model|parents:684|name:Expected Behavior Violation
CWE-441|Class|out-of-scope:generic-precondition-model|parents:610|name:Unintended Proxy or Intermediary ('Confused Deputy')
CWE-444|Base|out-of-scope:sink-classification-model|parents:436|name:Inconsistent Interpretation of HTTP Requests ('HTTP Request/Response Smuggling')
CWE-446|Class|out-of-scope:generic-precondition-model|parents:684|name:UI Discrepancy for Security Feature
CWE-447|Base|out-of-scope:generic-precondition-model|parents:446,671|name:Unimplemented or Unsupported Feature in UI
CWE-448|Base|out-of-scope:generic-precondition-model|parents:446|name:Obsolete Feature in UI
CWE-449|Base|out-of-scope:generic-precondition-model|parents:446|name:The UI Performs the Wrong Action
CWE-450|Base|out-of-scope:generic-precondition-model|parents:357|name:Multiple Interpretations of UI Input
CWE-451|Class|out-of-scope:ui-presentation-model|parents:684,221|name:User Interface (UI) Misrepresentation of Critical Information
CWE-453|Variant|out-of-scope:generic-precondition-model|parents:1188|name:Insecure Default Variable Initialization
CWE-454|Base|out-of-scope:generic-precondition-model|parents:1419|name:External Initialization of Trusted Variables or Data Stores
CWE-455|Base|out-of-scope:generic-precondition-model|parents:665,705,636|name:Non-exit on Failed Initialization
CWE-456|Variant|out-of-scope:generic-precondition-model|parents:909|name:Missing Initialization of a Variable
CWE-457|Variant|out-of-scope:memory-model|parents:908|name:Use of Uninitialized Variable
CWE-459|Base|out-of-scope:generic-precondition-model|parents:404|name:Incomplete Cleanup
CWE-460|Base|out-of-scope:language-runtime-semantics-model|parents:459,755|name:Improper Cleanup on Thrown Exception
CWE-462|Variant|out-of-scope:language-runtime-semantics-model|parents:694|name:Duplicate Key in Associative List (Alist)
CWE-463|Base|out-of-scope:language-runtime-semantics-model|parents:707|name:Deletion of Data Structure Sentinel
CWE-464|Base|out-of-scope:language-runtime-semantics-model|parents:138|name:Addition of Data Structure Sentinel
CWE-466|Base|out-of-scope:memory-model|parents:119|name:Return of Pointer Value Outside of Expected Range
CWE-467|Variant|out-of-scope:memory-model|parents:131|name:Use of sizeof() on a Pointer Type
CWE-468|Base|out-of-scope:memory-model|parents:682|name:Incorrect Pointer Scaling
CWE-469|Base|out-of-scope:memory-model|parents:682|name:Use of Pointer Subtraction to Determine Size
CWE-470|Base|out-of-scope:language-runtime-semantics-model|parents:913,610|name:Use of Externally-Controlled Input to Select Classes or Code ('Unsafe Reflection')
CWE-471|Base|out-of-scope:language-runtime-semantics-model|parents:664|name:Modification of Assumed-Immutable Data (MAID)
CWE-472|Base|out-of-scope:language-runtime-semantics-model|parents:642,471|name:External Control of Assumed-Immutable Web Parameter
CWE-473|Variant|out-of-scope:generic-precondition-model|parents:471|name:PHP External Variable Modification
CWE-474|Base|out-of-scope:generic-precondition-model|parents:758|name:Use of Function with Inconsistent Implementations
CWE-475|Base|out-of-scope:language-runtime-semantics-model|parents:573|name:Undefined Behavior for Input to API
CWE-476|Base|checkable:memory/pointer (NULL dereference)|parents:710,754|name:NULL Pointer Dereference
CWE-477|Base|out-of-scope:language-runtime-semantics-model|parents:710|name:Use of Obsolete Function
CWE-478|Base|out-of-scope:generic-precondition-model|parents:1023|name:Missing Default Case in Multiple Condition Expression
CWE-479|Variant|duplicate-of:CWE-362|parents:828,663|name:Signal Handler Use of a Non-reentrant Function
CWE-480|Base|out-of-scope:language-runtime-semantics-model|parents:670|name:Use of Incorrect Operator
CWE-481|Variant|out-of-scope:language-runtime-semantics-model|parents:480|name:Assigning instead of Comparing
CWE-482|Variant|out-of-scope:language-runtime-semantics-model|parents:480|name:Comparing instead of Assigning
CWE-483|Base|out-of-scope:language-runtime-semantics-model|parents:670|name:Incorrect Block Delimitation
CWE-484|Base|out-of-scope:language-runtime-semantics-model|parents:710,670|name:Omitted Break Statement in Switch
CWE-486|Variant|out-of-scope:language-runtime-semantics-model|parents:1025|name:Comparison of Classes by Name
CWE-487|Base|out-of-scope:language-runtime-semantics-model|parents:664|name:Reliance on Package-level Scope
CWE-488|Base|out-of-scope:generic-precondition-model|parents:668|name:Exposure of Data Element to Wrong Session
CWE-489|Base|out-of-scope:hardware-firmware-model|parents:710|name:Active Debug Code
CWE-491|Variant|out-of-scope:language-runtime-semantics-model|parents:668|name:Public cloneable() Method Without Final ('Object Hijack')
CWE-492|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:668|name:Use of Inner Class Containing Sensitive Data
CWE-493|Variant|out-of-scope:language-runtime-semantics-model|parents:668|name:Critical Public Variable Without Final Modifier
CWE-494|Base|out-of-scope:generic-precondition-model|parents:345,669|name:Download of Code Without Integrity Check
CWE-495|Variant|out-of-scope:generic-precondition-model|parents:664|name:Private Data Structure Returned From A Public Method
CWE-496|Variant|out-of-scope:generic-precondition-model|parents:664|name:Public Data Assigned to Private Array-Typed Field
CWE-497|Base|out-of-scope:authn-authz-boundary-predicate|parents:200|name:Exposure of Sensitive System Information to an Unauthorized Control Sphere
CWE-498|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:668|name:Cloneable Class Containing Sensitive Information
CWE-499|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:668|name:Serializable Class Containing Sensitive Data
CWE-500|Variant|out-of-scope:language-runtime-semantics-model|parents:493|name:Public Static Field Not Marked Final
CWE-501|Base|out-of-scope:authn-authz-boundary-predicate|parents:664|name:Trust Boundary Violation
CWE-502|Base|checkable:deserializer sink|parents:913|name:Deserialization of Untrusted Data
CWE-506|Class|out-of-scope:malicious-code-taxonomy|parents:912|name:Embedded Malicious Code
CWE-507|Base|out-of-scope:malicious-code-taxonomy|parents:506|name:Trojan Horse
CWE-508|Base|out-of-scope:malicious-code-taxonomy|parents:507|name:Non-Replicating Malicious Code
CWE-509|Base|out-of-scope:malicious-code-taxonomy|parents:507|name:Replicating Malicious Code (Virus or Worm)
CWE-510|Base|out-of-scope:malicious-code-taxonomy|parents:506|name:Trapdoor
CWE-511|Base|out-of-scope:malicious-code-taxonomy|parents:506|name:Logic/Time Bomb
CWE-512|Base|out-of-scope:malicious-code-taxonomy|parents:506|name:Spyware
CWE-514|Class|out-of-scope:malicious-code-taxonomy|parents:1229|name:Covert Channel
CWE-515|Base|out-of-scope:generic-precondition-model|parents:514|name:Covert Storage Channel
CWE-520|Variant|duplicate-of:CWE-269|parents:266|name:.NET Misconfiguration: Use of Impersonation
CWE-521|Base|out-of-scope:authn-authz-boundary-predicate|parents:1391|name:Weak Password Requirements
CWE-522|Class|out-of-scope:generic-precondition-model|parents:1390,668|name:Insufficiently Protected Credentials
CWE-523|Base|out-of-scope:generic-precondition-model|parents:522|name:Unprotected Transport of Credentials
CWE-524|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:668|name:Use of Cache Containing Sensitive Information
CWE-525|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:524|name:Use of Web Browser Cache Containing Sensitive Information
CWE-526|Variant|duplicate-of:CWE-922|parents:312|name:Cleartext Storage of Sensitive Information in an Environment Variable
CWE-527|Variant|out-of-scope:authn-authz-boundary-predicate|parents:552|name:Exposure of Version-Control Repository to an Unauthorized Control Sphere
CWE-528|Variant|out-of-scope:authn-authz-boundary-predicate|parents:552|name:Exposure of Core Dump File to an Unauthorized Control Sphere
CWE-529|Variant|out-of-scope:authn-authz-boundary-predicate|parents:552|name:Exposure of Access Control List Files to an Unauthorized Control Sphere
CWE-530|Variant|out-of-scope:authn-authz-boundary-predicate|parents:552|name:Exposure of Backup File to an Unauthorized Control Sphere
CWE-531|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:540|name:Inclusion of Sensitive Information in Test Code
CWE-532|Base|out-of-scope:logging-audit-model|parents:538|name:Insertion of Sensitive Information into Log File
CWE-535|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:211|name:Exposure of Information Through Shell Error Message
CWE-536|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:211|name:Servlet Runtime Error Message Containing Sensitive Information
CWE-537|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:211|name:Java Runtime Error Message Containing Sensitive Information
CWE-538|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:200|name:Insertion of Sensitive Information into Externally-Accessible File or Directory
CWE-539|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:552|name:Use of Persistent Cookies Containing Sensitive Information
CWE-540|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:538|name:Inclusion of Sensitive Information in Source Code
CWE-541|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:540|name:Inclusion of Sensitive Information in an Include File
CWE-543|Variant|out-of-scope:concurrency-scheduling-model|parents:820|name:Use of Singleton Pattern Without Synchronization in a Multithreaded Context
CWE-544|Base|out-of-scope:generic-precondition-model|parents:755|name:Missing Standardized Error Handling Mechanism
CWE-546|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:1078|name:Suspicious Comment
CWE-547|Base|out-of-scope:generic-precondition-model|parents:1078|name:Use of Hard-coded, Security-relevant Constants
CWE-548|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:497|name:Exposure of Information Through Directory Listing
CWE-549|Base|out-of-scope:ui-presentation-model|parents:522|name:Missing Password Field Masking
CWE-550|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:209|name:Server-generated Error Message Containing Sensitive Information
CWE-551|Base|duplicate-of:CWE-863|parents:863,696|name:Incorrect Behavior Order: Authorization Before Parsing and Canonicalization
CWE-552|Base|out-of-scope:generic-precondition-model|parents:668,285|name:Files or Directories Accessible to External Parties
CWE-553|Variant|out-of-scope:generic-precondition-model|parents:552|name:Command Shell in Externally Accessible Directory
CWE-554|Variant|duplicate-of:CWE-20|parents:1173|name:ASP.NET Misconfiguration: Not Using Input Validation Framework
CWE-555|Variant|duplicate-of:CWE-287|parents:260|name:J2EE Misconfiguration: Plaintext Password in Configuration File
CWE-556|Variant|duplicate-of:CWE-269|parents:266|name:ASP.NET Misconfiguration: Use of Identity Impersonation
CWE-558|Variant|out-of-scope:concurrency-scheduling-model|parents:663|name:Use of getlogin() in Multithreaded Application
CWE-560|Variant|out-of-scope:environment-config-model|parents:687|name:Use of umask() with chmod-style Argument
CWE-561|Base|out-of-scope:language-runtime-semantics-model|parents:1164|name:Dead Code
CWE-562|Base|out-of-scope:memory-model|parents:758|name:Return of Stack Variable Address
CWE-563|Base|out-of-scope:language-runtime-semantics-model|parents:1164|name:Assignment to Variable without Use
CWE-564|Variant|duplicate-of:CWE-89|parents:89|name:SQL Injection: Hibernate
CWE-565|Base|out-of-scope:generic-precondition-model|parents:642,602|name:Reliance on Cookies without Validation and Integrity Checking
CWE-566|Variant|duplicate-of:CWE-639|parents:639|name:Authorization Bypass Through User-Controlled SQL Primary Key
CWE-567|Base|out-of-scope:concurrency-scheduling-model|parents:820|name:Unsynchronized Access to Shared Data in a Multithreaded Context
CWE-568|Variant|out-of-scope:language-runtime-semantics-model|parents:573,459|name:finalize() Method Without super.finalize()
CWE-570|Base|out-of-scope:language-runtime-semantics-model|parents:710|name:Expression is Always False
CWE-571|Base|out-of-scope:language-runtime-semantics-model|parents:710|name:Expression is Always True
CWE-572|Variant|out-of-scope:concurrency-scheduling-model|parents:821|name:Call to Thread run() instead of start()
CWE-573|Class|out-of-scope:generic-precondition-model|parents:710|name:Improper Following of Specification by Caller
CWE-574|Variant|out-of-scope:concurrency-scheduling-model|parents:695,821|name:EJB Bad Practices: Use of Synchronization Primitives
CWE-575|Variant|out-of-scope:language-runtime-semantics-model|parents:695|name:EJB Bad Practices: Use of AWT Swing
CWE-576|Variant|out-of-scope:language-runtime-semantics-model|parents:695|name:EJB Bad Practices: Use of Java I/O
CWE-577|Variant|out-of-scope:network-protocol-model|parents:573|name:EJB Bad Practices: Use of Sockets
CWE-578|Variant|out-of-scope:language-runtime-semantics-model|parents:573|name:EJB Bad Practices: Use of Class Loader
CWE-579|Variant|out-of-scope:language-runtime-semantics-model|parents:573|name:J2EE Bad Practices: Non-serializable Object Stored in Session
CWE-580|Variant|out-of-scope:language-runtime-semantics-model|parents:664,573|name:clone() Method Without super.clone()
CWE-581|Variant|out-of-scope:generic-precondition-model|parents:573,697|name:Object Model Violation: Just One of Equals and Hashcode Defined
CWE-582|Variant|out-of-scope:generic-precondition-model|parents:668|name:Array Declared Public, Final, and Static
CWE-583|Variant|out-of-scope:language-runtime-semantics-model|parents:668|name:finalize() Method Declared Public
CWE-584|Base|out-of-scope:generic-precondition-model|parents:705|name:Return Inside Finally Block
CWE-585|Variant|out-of-scope:concurrency-scheduling-model|parents:1071|name:Empty Synchronized Block
CWE-586|Base|out-of-scope:language-runtime-semantics-model|parents:1076|name:Explicit Call to Finalize()
CWE-587|Variant|out-of-scope:memory-model|parents:344,758|name:Assignment of a Fixed Address to a Pointer
CWE-588|Variant|out-of-scope:memory-model|parents:704,758|name:Attempt to Access Child of a Non-structure Pointer
CWE-589|Variant|out-of-scope:language-runtime-semantics-model|parents:474|name:Call to Non-ubiquitous API
CWE-590|Variant|out-of-scope:memory-model|parents:762|name:Free of Memory not on the Heap
CWE-591|Variant|out-of-scope:memory-model|parents:413|name:Sensitive Data Storage in Improperly Locked Memory
CWE-593|Variant|duplicate-of:CWE-287|parents:666,1390|name:Authentication Bypass: OpenSSL CTX Object Modified after SSL Objects are Created
CWE-594|Variant|out-of-scope:language-runtime-semantics-model|parents:1076|name:J2EE Framework: Saving Unserializable Objects to Disk
CWE-595|Variant|out-of-scope:language-runtime-semantics-model|parents:1025|name:Comparison of Object References Instead of Object Contents
CWE-597|Variant|out-of-scope:language-runtime-semantics-model|parents:595,480|name:Use of Wrong Operator in String Comparison
CWE-598|Variant|out-of-scope:sink-classification-model|parents:201|name:Use of HTTP Request With Sensitive Query String
CWE-599|Variant|duplicate-of:CWE-287|parents:295|name:Missing Validation of OpenSSL Certificate
CWE-600|Variant|out-of-scope:language-runtime-semantics-model|parents:248|name:Uncaught Exception in Servlet
CWE-601|Base|out-of-scope:generic-precondition-model|parents:610|name:URL Redirection to Untrusted Site ('Open Redirect')
CWE-602|Class|out-of-scope:generic-precondition-model|parents:693|name:Client-Side Enforcement of Server-Side Security
CWE-603|Base|duplicate-of:CWE-287|parents:1390,602|name:Use of Client-Side Authentication
CWE-605|Variant|out-of-scope:network-protocol-model|parents:675,666|name:Multiple Binds to the Same Port
CWE-606|Base|out-of-scope:generic-precondition-model|parents:1284|name:Unchecked Input for Loop Condition
CWE-607|Variant|out-of-scope:generic-precondition-model|parents:471|name:Public Static Final Field References Mutable Object
CWE-608|Variant|out-of-scope:language-runtime-semantics-model|parents:668|name:Struts: Non-private Field in ActionForm Class
CWE-609|Base|out-of-scope:concurrency-scheduling-model|parents:667|name:Double-Checked Locking
CWE-610|Class|out-of-scope:generic-precondition-model|parents:664|name:Externally Controlled Reference to a Resource in Another Sphere
CWE-611|Base|out-of-scope:content-type-sink|parents:610|name:Improper Restriction of XML External Entity Reference
CWE-612|Base|out-of-scope:authn-authz-boundary-predicate|parents:1230|name:Improper Authorization of Index Containing Sensitive Information
CWE-613|Base|out-of-scope:authn-authz-boundary-predicate|parents:672|name:Insufficient Session Expiration
CWE-614|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:319|name:Sensitive Cookie in HTTPS Session Without 'Secure' Attribute
CWE-615|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:540|name:Inclusion of Sensitive Information in Source Code Comments
CWE-616|Variant|out-of-scope:content-type-sink|parents:345|name:Incomplete Identification of Uploaded File Variables (PHP)
CWE-617|Base|out-of-scope:generic-precondition-model|parents:705|name:Reachable Assertion
CWE-618|Variant|out-of-scope:generic-precondition-model|parents:749|name:Exposed Unsafe ActiveX Method
CWE-619|Base|out-of-scope:memory-model|parents:402|name:Dangling Database Cursor ('Cursor Injection')
CWE-620|Base|out-of-scope:authn-authz-boundary-predicate|parents:1390|name:Unverified Password Change
CWE-621|Variant|out-of-scope:generic-precondition-model|parents:914|name:Variable Extraction Error
CWE-622|Variant|duplicate-of:CWE-20|parents:20|name:Improper Validation of Function Hook Arguments
CWE-623|Variant|duplicate-of:CWE-269|parents:267|name:Unsafe ActiveX Control Marked Safe For Scripting
CWE-624|Base|out-of-scope:sink-classification-model|parents:77|name:Executable Regular Expression Error
CWE-625|Base|out-of-scope:sink-classification-model|parents:185|name:Permissive Regular Expression
CWE-626|Variant|out-of-scope:generic-precondition-model|parents:147,436|name:Null Byte Interaction Error (Poison Null Byte)
CWE-627|Variant|out-of-scope:generic-precondition-model|parents:914|name:Dynamic Variable Evaluation
CWE-628|Base|out-of-scope:generic-precondition-model|parents:573|name:Function Call with Incorrectly Specified Arguments
CWE-636|Class|out-of-scope:secure-design-principle-model|parents:657,755|name:Not Failing Securely ('Failing Open')
CWE-637|Class|out-of-scope:secure-design-principle-model|parents:657|name:Unnecessary Complexity in Protection Mechanism (Not Using 'Economy of Mechanism')
CWE-638|Class|out-of-scope:secure-design-principle-model|parents:657,862|name:Not Using Complete Mediation
CWE-639|Base|checkable:sql (authorization bypass via user-controlled key, reuses CWE-89 join)|parents:863|name:Authorization Bypass Through User-Controlled Key
CWE-640|Base|out-of-scope:authn-authz-boundary-predicate|parents:1390|name:Weak Password Recovery Mechanism for Forgotten Password
CWE-641|Base|out-of-scope:filesystem-semantics-model|parents:99|name:Improper Restriction of Names for Files and Other Resources
CWE-642|Class|out-of-scope:generic-precondition-model|parents:668|name:External Control of Critical State Data
CWE-643|Base|out-of-scope:sink-classification-model|parents:943,91|name:Improper Neutralization of Data within XPath Expressions ('XPath Injection')
CWE-644|Variant|out-of-scope:sink-classification-model|parents:116|name:Improper Neutralization of HTTP Headers for Scripting Syntax
CWE-645|Base|out-of-scope:authn-authz-boundary-predicate|parents:287|name:Overly Restrictive Account Lockout Mechanism
CWE-646|Variant|out-of-scope:content-type-sink|parents:345|name:Reliance on File Name or Extension of Externally-Supplied File
CWE-647|Variant|duplicate-of:CWE-863|parents:863,180|name:Use of Non-Canonical URL Paths for Authorization Decisions
CWE-648|Base|duplicate-of:CWE-269|parents:269|name:Incorrect Use of Privileged APIs
CWE-649|Base|out-of-scope:crypto-primitive-model|parents:345|name:Reliance on Obfuscation or Encryption of Security-Relevant Inputs without Integrity Checking
CWE-650|Variant|out-of-scope:authn-authz-boundary-predicate|parents:436|name:Trusting HTTP Permission Methods on the Server Side
CWE-651|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:538|name:Exposure of WSDL File Containing Sensitive Information
CWE-652|Base|out-of-scope:sink-classification-model|parents:943,91|name:Improper Neutralization of Data within XQuery Expressions ('XQuery Injection')
CWE-653|Class|out-of-scope:secure-design-principle-model|parents:657,693|name:Improper Isolation or Compartmentalization
CWE-654|Base|out-of-scope:authn-authz-boundary-predicate|parents:657,693|name:Reliance on a Single Factor in a Security Decision
CWE-655|Class|out-of-scope:secure-design-principle-model|parents:657,693|name:Insufficient Psychological Acceptability
CWE-656|Class|out-of-scope:secure-design-principle-model|parents:657,693|name:Reliance on Security Through Obscurity
CWE-657|Class|out-of-scope:secure-design-principle-model|parents:710|name:Violation of Secure Design Principles
CWE-662|Class|out-of-scope:concurrency-scheduling-model|parents:664,691|name:Improper Synchronization
CWE-663|Base|out-of-scope:concurrency-scheduling-model|parents:662|name:Use of a Non-reentrant Function in a Concurrent Context
CWE-664|Pillar|out-of-scope:resource-exhaustion-model|parents:-|name:Improper Control of a Resource Through its Lifetime
CWE-665|Class|out-of-scope:generic-precondition-model|parents:664|name:Improper Initialization
CWE-666|Class|out-of-scope:resource-exhaustion-model|parents:664|name:Operation on Resource in Wrong Phase of Lifetime
CWE-667|Class|out-of-scope:concurrency-scheduling-model|parents:662|name:Improper Locking
CWE-668|Class|out-of-scope:generic-precondition-model|parents:664|name:Exposure of Resource to Wrong Sphere
CWE-669|Class|out-of-scope:generic-precondition-model|parents:664|name:Incorrect Resource Transfer Between Spheres
CWE-670|Class|out-of-scope:generic-precondition-model|parents:691|name:Always-Incorrect Control Flow Implementation
CWE-671|Class|out-of-scope:generic-precondition-model|parents:657|name:Lack of Administrator Control over Security
CWE-672|Class|out-of-scope:generic-precondition-model|parents:666|name:Operation on a Resource after Expiration or Release
CWE-673|Class|out-of-scope:generic-precondition-model|parents:664|name:External Influence of Sphere Definition
CWE-674|Class|out-of-scope:generic-precondition-model|parents:834|name:Uncontrolled Recursion
CWE-675|Class|out-of-scope:generic-precondition-model|parents:573|name:Multiple Operations on Resource in Single-Operation Context
CWE-676|Base|out-of-scope:generic-precondition-model|parents:1177|name:Use of Potentially Dangerous Function
CWE-680|Compound|duplicate-of:CWE-190|parents:190|name:Integer Overflow to Buffer Overflow
CWE-681|Base|out-of-scope:generic-precondition-model|parents:704|name:Incorrect Conversion between Numeric Types
CWE-682|Pillar|out-of-scope:generic-precondition-model|parents:-|name:Incorrect Calculation
CWE-683|Variant|out-of-scope:generic-precondition-model|parents:628|name:Function Call With Incorrect Order of Arguments
CWE-684|Class|out-of-scope:generic-precondition-model|parents:710|name:Incorrect Provision of Specified Functionality
CWE-685|Variant|out-of-scope:generic-precondition-model|parents:628|name:Function Call With Incorrect Number of Arguments
CWE-686|Variant|out-of-scope:generic-precondition-model|parents:628|name:Function Call With Incorrect Argument Type
CWE-687|Variant|out-of-scope:generic-precondition-model|parents:628|name:Function Call With Incorrectly Specified Argument Value
CWE-688|Variant|out-of-scope:generic-precondition-model|parents:628|name:Function Call With Incorrect Variable or Reference as Argument
CWE-689|Compound|duplicate-of:CWE-362|parents:362|name:Permission Race Condition During Resource Copy
CWE-690|Compound|out-of-scope:memory-model|parents:252|name:Unchecked Return Value to NULL Pointer Dereference
CWE-691|Pillar|out-of-scope:generic-precondition-model|parents:-|name:Insufficient Control Flow Management
CWE-692|Compound|out-of-scope:generic-precondition-model|parents:184|name:Incomplete Denylist to Cross-Site Scripting
CWE-693|Pillar|out-of-scope:generic-precondition-model|parents:-|name:Protection Mechanism Failure
CWE-694|Base|out-of-scope:generic-precondition-model|parents:99,573|name:Use of Multiple Resources with Duplicate Identifier
CWE-695|Base|out-of-scope:generic-precondition-model|parents:573|name:Use of Low-Level Functionality
CWE-696|Class|out-of-scope:generic-precondition-model|parents:691|name:Incorrect Behavior Order
CWE-697|Pillar|out-of-scope:generic-precondition-model|parents:-|name:Incorrect Comparison
CWE-698|Base|out-of-scope:generic-precondition-model|parents:705,670|name:Execution After Redirect (EAR)
CWE-703|Pillar|out-of-scope:language-runtime-semantics-model|parents:-|name:Improper Check or Handling of Exceptional Conditions
CWE-704|Class|out-of-scope:generic-precondition-model|parents:664|name:Incorrect Type Conversion or Cast
CWE-705|Class|out-of-scope:generic-precondition-model|parents:691|name:Incorrect Control Flow Scoping
CWE-706|Class|out-of-scope:generic-precondition-model|parents:664|name:Use of Incorrectly-Resolved Name or Reference
CWE-707|Pillar|out-of-scope:sink-classification-model|parents:-|name:Improper Neutralization
CWE-708|Base|out-of-scope:generic-precondition-model|parents:282|name:Incorrect Ownership Assignment
CWE-710|Pillar|out-of-scope:generic-precondition-model|parents:-|name:Improper Adherence to Coding Standards
CWE-732|Class|out-of-scope:authn-authz-boundary-predicate|parents:285,668|name:Incorrect Permission Assignment for Critical Resource
CWE-733|Base|out-of-scope:generic-precondition-model|parents:1038|name:Compiler Optimization Removal or Modification of Security-critical Code
CWE-749|Base|out-of-scope:generic-precondition-model|parents:284|name:Exposed Dangerous Method or Function
CWE-754|Class|out-of-scope:language-runtime-semantics-model|parents:703|name:Improper Check for Unusual or Exceptional Conditions
CWE-755|Class|out-of-scope:language-runtime-semantics-model|parents:703|name:Improper Handling of Exceptional Conditions
CWE-756|Base|out-of-scope:generic-precondition-model|parents:755|name:Missing Custom Error Page
CWE-757|Base|out-of-scope:generic-precondition-model|parents:693|name:Selection of Less-Secure Algorithm During Negotiation ('Algorithm Downgrade')
CWE-758|Class|out-of-scope:generic-precondition-model|parents:710|name:Reliance on Undefined, Unspecified, or Implementation-Defined Behavior
CWE-759|Variant|out-of-scope:crypto-primitive-model|parents:916|name:Use of a One-Way Hash without a Salt
CWE-760|Variant|out-of-scope:crypto-primitive-model|parents:916|name:Use of a One-Way Hash with a Predictable Salt
CWE-761|Variant|out-of-scope:memory-model|parents:763|name:Free of Pointer not at Start of Buffer
CWE-762|Variant|out-of-scope:memory-model|parents:763|name:Mismatched Memory Management Routines
CWE-763|Base|out-of-scope:memory-model|parents:404|name:Release of Invalid Pointer or Reference
CWE-764|Base|out-of-scope:concurrency-scheduling-model|parents:667,675|name:Multiple Locks of a Critical Resource
CWE-765|Base|out-of-scope:concurrency-scheduling-model|parents:667,675|name:Multiple Unlocks of a Critical Resource
CWE-766|Base|out-of-scope:generic-precondition-model|parents:732,1061|name:Critical Data Element Declared Public
CWE-767|Base|out-of-scope:generic-precondition-model|parents:668|name:Access to Critical Private Variable via Public Method
CWE-768|Variant|out-of-scope:generic-precondition-model|parents:691|name:Incorrect Short Circuit Evaluation
CWE-770|Base|out-of-scope:memory-model|parents:400,665|name:Allocation of Resources Without Limits or Throttling
CWE-771|Base|out-of-scope:memory-model|parents:400|name:Missing Reference to Active Allocated Resource
CWE-772|Base|out-of-scope:resource-exhaustion-model|parents:404|name:Missing Release of Resource after Effective Lifetime
CWE-773|Variant|out-of-scope:resource-exhaustion-model|parents:771|name:Missing Reference to Active File Descriptor or Handle
CWE-774|Variant|out-of-scope:memory-model|parents:770|name:Allocation of File Descriptors or Handles Without Limits or Throttling
CWE-775|Variant|out-of-scope:resource-exhaustion-model|parents:772|name:Missing Release of File Descriptor or Handle after Effective Lifetime
CWE-776|Base|out-of-scope:generic-precondition-model|parents:674,405|name:Improper Restriction of Recursive Entity References in DTDs ('XML Entity Expansion')
CWE-777|Variant|out-of-scope:sink-classification-model|parents:625|name:Regular Expression without Anchors
CWE-778|Base|out-of-scope:logging-audit-model|parents:223|name:Insufficient Logging
CWE-779|Base|out-of-scope:logging-audit-model|parents:400|name:Logging of Excessive Data
CWE-780|Variant|out-of-scope:generic-precondition-model|parents:327|name:Use of RSA Algorithm without OAEP
CWE-781|Variant|duplicate-of:CWE-20|parents:1285|name:Improper Address Validation in IOCTL with METHOD_NEITHER I/O Control Code
CWE-782|Variant|out-of-scope:authn-authz-boundary-predicate|parents:749|name:Exposed IOCTL with Insufficient Access Control
CWE-783|Base|out-of-scope:language-runtime-semantics-model|parents:670|name:Operator Precedence Logic Error
CWE-784|Variant|out-of-scope:generic-precondition-model|parents:807,565|name:Reliance on Cookies without Validation and Integrity Checking in a Security Decision
CWE-785|Variant|duplicate-of:CWE-787|parents:676,120|name:Use of Path Manipulation Function without Maximum-sized Buffer
CWE-786|Base|duplicate-of:CWE-119|parents:119|name:Access of Memory Location Before Start of Buffer
CWE-787|Base|checkable:memory/buffer write (out-of-bounds write)|parents:119|name:Out-of-bounds Write
CWE-788|Base|duplicate-of:CWE-119|parents:119|name:Access of Memory Location After End of Buffer
CWE-789|Variant|out-of-scope:memory-model|parents:770|name:Memory Allocation with Excessive Size Value
CWE-790|Class|out-of-scope:sink-classification-model|parents:138|name:Improper Filtering of Special Elements
CWE-791|Base|out-of-scope:sink-classification-model|parents:790|name:Incomplete Filtering of Special Elements
CWE-792|Variant|out-of-scope:sink-classification-model|parents:791|name:Incomplete Filtering of One or More Instances of Special Elements
CWE-793|Variant|out-of-scope:sink-classification-model|parents:792|name:Only Filtering One Instance of a Special Element
CWE-794|Variant|out-of-scope:sink-classification-model|parents:792|name:Incomplete Filtering of Multiple Instances of Special Elements
CWE-795|Base|out-of-scope:sink-classification-model|parents:791|name:Only Filtering Special Elements at a Specified Location
CWE-796|Variant|out-of-scope:sink-classification-model|parents:795|name:Only Filtering Special Elements Relative to a Marker
CWE-797|Variant|out-of-scope:sink-classification-model|parents:795|name:Only Filtering Special Elements at an Absolute Position
CWE-798|Base|checkable:Secret-labeled value at low-clearance node (hardcoded creds)|parents:1391,344,671|name:Use of Hard-coded Credentials
CWE-799|Class|out-of-scope:generic-precondition-model|parents:691|name:Improper Control of Interaction Frequency
CWE-804|Base|out-of-scope:generic-precondition-model|parents:863,1390|name:Guessable CAPTCHA
CWE-805|Base|duplicate-of:CWE-119|parents:119|name:Buffer Access with Incorrect Length Value
CWE-806|Variant|duplicate-of:CWE-119|parents:805|name:Buffer Access Using Size of Source Buffer
CWE-807|Base|out-of-scope:generic-precondition-model|parents:693|name:Reliance on Untrusted Inputs in a Security Decision
CWE-820|Base|out-of-scope:concurrency-scheduling-model|parents:662|name:Missing Synchronization
CWE-821|Base|out-of-scope:concurrency-scheduling-model|parents:662|name:Incorrect Synchronization
CWE-822|Base|out-of-scope:memory-model|parents:119|name:Untrusted Pointer Dereference
CWE-823|Base|out-of-scope:memory-model|parents:119|name:Use of Out-of-range Pointer Offset
CWE-824|Base|out-of-scope:memory-model|parents:119|name:Access of Uninitialized Pointer
CWE-825|Base|out-of-scope:memory-model|parents:119,672|name:Expired Pointer Dereference
CWE-826|Base|out-of-scope:resource-exhaustion-model|parents:666|name:Premature Release of Resource During Expected Lifetime
CWE-827|Variant|out-of-scope:generic-precondition-model|parents:706,829|name:Improper Control of Document Type Definition
CWE-828|Variant|duplicate-of:CWE-362|parents:364|name:Signal Handler with Functionality that is not Asynchronous-Safe
CWE-829|Base|out-of-scope:generic-precondition-model|parents:669|name:Inclusion of Functionality from Untrusted Control Sphere
CWE-830|Variant|out-of-scope:generic-precondition-model|parents:829|name:Inclusion of Web Functionality from an Untrusted Source
CWE-831|Variant|duplicate-of:CWE-362|parents:364|name:Signal Handler Function Associated with Multiple Signals
CWE-832|Base|out-of-scope:resource-exhaustion-model|parents:667|name:Unlock of a Resource that is not Locked
CWE-833|Base|out-of-scope:concurrency-scheduling-model|parents:667|name:Deadlock
CWE-834|Class|out-of-scope:resource-exhaustion-model|parents:691|name:Excessive Iteration
CWE-835|Base|out-of-scope:generic-precondition-model|parents:834|name:Loop with Unreachable Exit Condition ('Infinite Loop')
CWE-836|Base|duplicate-of:CWE-287|parents:1390|name:Use of Password Hash Instead of Password for Authentication
CWE-837|Base|out-of-scope:generic-precondition-model|parents:799|name:Improper Enforcement of a Single, Unique Action
CWE-838|Base|out-of-scope:sink-classification-model|parents:116|name:Inappropriate Encoding for Output Context
CWE-839|Base|out-of-scope:generic-precondition-model|parents:1023|name:Numeric Range Comparison Without Minimum Check
CWE-841|Class|out-of-scope:generic-precondition-model|parents:691|name:Improper Enforcement of Behavioral Workflow
CWE-842|Base|out-of-scope:generic-precondition-model|parents:286|name:Placement of User into Incorrect Group
CWE-843|Base|out-of-scope:memory-model|parents:704|name:Access of Resource Using Incompatible Type ('Type Confusion')
CWE-862|Class|checkable:endpoint/authz predicate (missing authorization)|parents:285|name:Missing Authorization
CWE-863|Class|checkable:authz-boundary predicate (incorrect authorization)|parents:285|name:Incorrect Authorization
CWE-908|Base|out-of-scope:memory-model|parents:665|name:Use of Uninitialized Resource
CWE-909|Class|out-of-scope:generic-precondition-model|parents:665|name:Missing Initialization of Resource
CWE-910|Base|out-of-scope:resource-exhaustion-model|parents:672|name:Use of Expired File Descriptor
CWE-911|Base|out-of-scope:generic-precondition-model|parents:664|name:Improper Update of Reference Count
CWE-912|Class|out-of-scope:generic-precondition-model|parents:684|name:Hidden Functionality
CWE-913|Class|out-of-scope:generic-precondition-model|parents:664|name:Improper Control of Dynamically-Managed Code Resources
CWE-914|Base|out-of-scope:generic-precondition-model|parents:99,913|name:Improper Control of Dynamically-Identified Variables
CWE-915|Base|out-of-scope:generic-precondition-model|parents:913|name:Improperly Controlled Modification of Dynamically-Determined Object Attributes
CWE-916|Base|out-of-scope:generic-precondition-model|parents:328|name:Use of Password Hash With Insufficient Computational Effort
CWE-917|Base|out-of-scope:sink-classification-model|parents:77|name:Improper Neutralization of Special Elements used in an Expression Language Statement ('Expression Language Injection')
CWE-918|Base|checkable:network-request target (SSRF)|parents:441|name:Server-Side Request Forgery (SSRF)
CWE-920|Base|out-of-scope:generic-precondition-model|parents:400|name:Improper Restriction of Power Consumption
CWE-921|Base|out-of-scope:authn-authz-boundary-predicate|parents:922|name:Storage of Sensitive Data in a Mechanism without Access Control
CWE-922|Class|checkable:clearance/storage lattice (insecure storage)|parents:664|name:Insecure Storage of Sensitive Information
CWE-923|Class|out-of-scope:generic-precondition-model|parents:284|name:Improper Restriction of Communication Channel to Intended Endpoints
CWE-924|Base|out-of-scope:generic-precondition-model|parents:345|name:Improper Enforcement of Message Integrity During Transmission in a Communication Channel
CWE-925|Variant|out-of-scope:generic-precondition-model|parents:940|name:Improper Verification of Intent by Broadcast Receiver
CWE-926|Variant|out-of-scope:generic-precondition-model|parents:285|name:Improper Export of Android Application Components
CWE-927|Variant|out-of-scope:generic-precondition-model|parents:285,668|name:Use of Implicit Intent for Sensitive Communication
CWE-939|Base|duplicate-of:CWE-862|parents:862,940|name:Improper Authorization in Handler for Custom URL Scheme
CWE-940|Base|out-of-scope:generic-precondition-model|parents:923,346|name:Improper Verification of Source of a Communication Channel
CWE-941|Base|out-of-scope:generic-precondition-model|parents:923|name:Incorrectly Specified Destination in a Communication Channel
CWE-942|Variant|duplicate-of:CWE-863|parents:863,923,183|name:Permissive Cross-domain Security Policy with Untrusted Domains
CWE-943|Class|out-of-scope:sink-classification-model|parents:74|name:Improper Neutralization of Special Elements in Data Query Logic
CWE-1004|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:732|name:Sensitive Cookie Without 'HttpOnly' Flag
CWE-1007|Base|out-of-scope:ui-presentation-model|parents:451|name:Insufficient Visual Distinction of Homoglyphs Presented to User
CWE-1021|Base|out-of-scope:generic-precondition-model|parents:441,451|name:Improper Restriction of Rendered UI Layers or Frames
CWE-1022|Variant|duplicate-of:CWE-269|parents:266|name:Use of Web Link to Untrusted Target with window.opener Access
CWE-1023|Class|out-of-scope:generic-precondition-model|parents:697|name:Incomplete Comparison with Missing Factors
CWE-1024|Base|out-of-scope:generic-precondition-model|parents:697|name:Comparison of Incompatible Types
CWE-1025|Base|out-of-scope:generic-precondition-model|parents:697|name:Comparison Using Wrong Factors
CWE-1037|Base|out-of-scope:generic-precondition-model|parents:1038|name:Processor Optimization Removal or Modification of Security-critical Code
CWE-1038|Class|out-of-scope:generic-precondition-model|parents:435,758|name:Insecure Automated Optimizations
CWE-1039|Class|out-of-scope:generic-precondition-model|parents:693,697|name:Inadequate Detection or Handling of Adversarial Input Perturbations in Automated Recognition Mechanism
CWE-1041|Base|out-of-scope:generic-precondition-model|parents:710|name:Use of Redundant Code
CWE-1042|Variant|out-of-scope:generic-precondition-model|parents:1176|name:Static Member Data Element outside of a Singleton Class Element
CWE-1043|Base|out-of-scope:generic-precondition-model|parents:1093|name:Data Element Aggregating an Excessively Large Number of Non-Primitive Elements
CWE-1044|Base|out-of-scope:generic-precondition-model|parents:710|name:Architecture with Number of Horizontal Layers Outside of Expected Range
CWE-1045|Base|out-of-scope:generic-precondition-model|parents:1076|name:Parent Class with a Virtual Destructor and a Child Class without a Virtual Destructor
CWE-1046|Base|out-of-scope:language-runtime-semantics-model|parents:1176|name:Creation of Immutable Text Using String Concatenation
CWE-1047|Base|out-of-scope:generic-precondition-model|parents:1120|name:Modules with Circular Dependencies
CWE-1048|Base|out-of-scope:generic-precondition-model|parents:710|name:Invokable Control Element with Large Number of Outward Calls
CWE-1049|Base|out-of-scope:generic-precondition-model|parents:1176|name:Excessive Data Query Operations in a Large Data Table
CWE-1050|Base|out-of-scope:generic-precondition-model|parents:405|name:Excessive Platform Resource Consumption within a Loop
CWE-1051|Base|out-of-scope:environment-config-model|parents:1419|name:Initialization with Hard-Coded Network Resource Configuration Data
CWE-1052|Base|out-of-scope:generic-precondition-model|parents:1419|name:Excessive Use of Hard-Coded Literals in Initialization
CWE-1053|Base|out-of-scope:generic-precondition-model|parents:1059|name:Missing Documentation for Design
CWE-1054|Base|out-of-scope:generic-precondition-model|parents:1061|name:Invocation of a Control Element at an Unnecessarily Deep Horizontal Layer
CWE-1055|Base|out-of-scope:generic-precondition-model|parents:1093|name:Multiple Inheritance from Concrete Classes
CWE-1056|Base|out-of-scope:generic-precondition-model|parents:1120|name:Invokable Control Element with Variadic Parameters
CWE-1057|Base|out-of-scope:generic-precondition-model|parents:1061|name:Data Access Operations Outside of Expected Data Manager Component
CWE-1058|Base|out-of-scope:concurrency-scheduling-model|parents:662|name:Invokable Control Element in Multi-Thread Context with non-Final Static Storable or Member Element
CWE-1059|Class|out-of-scope:generic-precondition-model|parents:710|name:Insufficient Technical Documentation
CWE-1060|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessive Number of Inefficient Server-Side Data Accesses
CWE-1061|Class|out-of-scope:generic-precondition-model|parents:710|name:Insufficient Encapsulation
CWE-1062|Base|out-of-scope:generic-precondition-model|parents:1061|name:Parent Class with References to Child Class
CWE-1063|Base|out-of-scope:generic-precondition-model|parents:1176|name:Creation of Class Instance within a Static Code Block
CWE-1064|Base|out-of-scope:generic-precondition-model|parents:1120|name:Invokable Control Element with Signature Containing an Excessive Number of Parameters
CWE-1065|Base|out-of-scope:generic-precondition-model|parents:710|name:Runtime Resource Management Control Element in a Component Built to Run on Application Servers
CWE-1066|Base|out-of-scope:language-runtime-semantics-model|parents:710|name:Missing Serialization Control Element
CWE-1067|Base|out-of-scope:generic-precondition-model|parents:1176|name:Excessive Execution of Sequential Searches of Data Resource
CWE-1068|Base|out-of-scope:generic-precondition-model|parents:710|name:Inconsistency Between Implementation and Documented Design
CWE-1069|Variant|out-of-scope:language-runtime-semantics-model|parents:1071|name:Empty Exception Block
CWE-1070|Base|out-of-scope:language-runtime-semantics-model|parents:1076|name:Serializable Data Element Containing non-Serializable Item Elements
CWE-1071|Base|out-of-scope:generic-precondition-model|parents:1164|name:Empty Code Block
CWE-1072|Base|out-of-scope:generic-precondition-model|parents:405|name:Data Resource Access without Use of Connection Pooling
CWE-1073|Base|out-of-scope:generic-precondition-model|parents:405|name:Non-SQL Invokable Control Element with Excessive Number of Data Resource Accesses
CWE-1074|Base|out-of-scope:generic-precondition-model|parents:1093|name:Class with Excessively Deep Inheritance
CWE-1075|Base|out-of-scope:language-runtime-semantics-model|parents:1120|name:Unconditional Control Flow Transfer outside of Switch Block
CWE-1076|Class|out-of-scope:generic-precondition-model|parents:710|name:Insufficient Adherence to Expected Conventions
CWE-1077|Variant|out-of-scope:language-runtime-semantics-model|parents:697|name:Floating Point Comparison with Incorrect Operator
CWE-1078|Class|out-of-scope:sensitive-data-exposure-sink-model|parents:1076|name:Inappropriate Source Code Style or Formatting
CWE-1079|Base|out-of-scope:generic-precondition-model|parents:1076|name:Parent Class without Virtual Destructor Method
CWE-1080|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1120|name:Source Code File with Excessive Number of Lines of Code
CWE-1082|Base|out-of-scope:generic-precondition-model|parents:1076|name:Class Instance Self Destruction Control Element
CWE-1083|Base|out-of-scope:generic-precondition-model|parents:1061|name:Data Access from Outside Expected Data Manager Component
CWE-1084|Base|out-of-scope:generic-precondition-model|parents:405|name:Invokable Control Element with Excessive File or Data Access Operations
CWE-1085|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1078|name:Invokable Control Element with Excessive Volume of Commented-out Code
CWE-1086|Base|out-of-scope:generic-precondition-model|parents:1093|name:Class with Excessive Number of Child Classes
CWE-1087|Base|out-of-scope:generic-precondition-model|parents:1076|name:Class with Virtual Method without a Virtual Destructor
CWE-1088|Base|out-of-scope:generic-precondition-model|parents:821|name:Synchronous Access of Remote Resource without Timeout
CWE-1089|Base|out-of-scope:generic-precondition-model|parents:405|name:Large Data Table with Excessive Number of Indices
CWE-1090|Base|out-of-scope:generic-precondition-model|parents:1061|name:Method Containing Access of a Member Element from Another Class
CWE-1091|Base|out-of-scope:generic-precondition-model|parents:772,1076|name:Use of Object without Invoking Destructor Method
CWE-1092|Base|out-of-scope:generic-precondition-model|parents:710|name:Use of Same Invokable Control Element in Multiple Architectural Layers
CWE-1093|Class|out-of-scope:generic-precondition-model|parents:710|name:Excessively Complex Data Representation
CWE-1094|Base|out-of-scope:generic-precondition-model|parents:405|name:Excessive Index Range Scan for a Data Resource
CWE-1095|Base|out-of-scope:generic-precondition-model|parents:1120|name:Loop Condition Value Update within the Loop
CWE-1096|Variant|out-of-scope:concurrency-scheduling-model|parents:820|name:Singleton Class Instance Creation without Proper Locking or Synchronization
CWE-1097|Base|out-of-scope:generic-precondition-model|parents:1076|name:Persistent Storable Data Element without Associated Comparison Control Element
CWE-1098|Base|out-of-scope:memory-model|parents:1076|name:Data Element containing Pointer Item without Proper Copy Control Element
CWE-1099|Base|out-of-scope:generic-precondition-model|parents:1078|name:Inconsistent Naming Conventions for Identifiers
CWE-1100|Base|out-of-scope:generic-precondition-model|parents:1061|name:Insufficient Isolation of System-Dependent Functions
CWE-1101|Base|out-of-scope:generic-precondition-model|parents:710|name:Reliance on Runtime Component in Generated Code
CWE-1102|Base|out-of-scope:generic-precondition-model|parents:758|name:Reliance on Machine-Dependent Data Representation
CWE-1103|Base|out-of-scope:generic-precondition-model|parents:758|name:Use of Platform-Dependent Third Party Components
CWE-1104|Base|out-of-scope:generic-precondition-model|parents:1357|name:Use of Unmaintained Third Party Components
CWE-1105|Base|out-of-scope:generic-precondition-model|parents:758,1061|name:Insufficient Encapsulation of Machine-Dependent Functionality
CWE-1106|Base|out-of-scope:generic-precondition-model|parents:1078|name:Insufficient Use of Symbolic Constants
CWE-1107|Base|out-of-scope:generic-precondition-model|parents:1078|name:Insufficient Isolation of Symbolic Constant Definitions
CWE-1108|Base|out-of-scope:generic-precondition-model|parents:1076|name:Excessive Reliance on Global Variables
CWE-1109|Base|out-of-scope:generic-precondition-model|parents:1078|name:Use of Same Variable for Multiple Purposes
CWE-1110|Base|out-of-scope:generic-precondition-model|parents:1059|name:Incomplete Design Documentation
CWE-1111|Base|out-of-scope:generic-precondition-model|parents:1059|name:Incomplete I/O Documentation
CWE-1112|Base|out-of-scope:generic-precondition-model|parents:1059|name:Incomplete Documentation of Program Execution
CWE-1113|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1078|name:Inappropriate Comment Style
CWE-1114|Base|out-of-scope:generic-precondition-model|parents:1078|name:Inappropriate Whitespace Style
CWE-1115|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1078|name:Source Code Element without Standard Prologue
CWE-1116|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1078|name:Inaccurate Source Code Comments
CWE-1117|Base|out-of-scope:generic-precondition-model|parents:1078|name:Callable with Insufficient Behavioral Summary
CWE-1118|Base|out-of-scope:generic-precondition-model|parents:1059|name:Insufficient Documentation of Error Handling Techniques
CWE-1119|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessive Use of Unconditional Branching
CWE-1120|Class|out-of-scope:generic-precondition-model|parents:710|name:Excessive Code Complexity
CWE-1121|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessive McCabe Cyclomatic Complexity
CWE-1122|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessive Halstead Complexity
CWE-1123|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessive Use of Self-Modifying Code
CWE-1124|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessively Deep Nesting
CWE-1125|Base|out-of-scope:generic-precondition-model|parents:1120|name:Excessive Attack Surface
CWE-1126|Base|out-of-scope:language-runtime-semantics-model|parents:710|name:Declaration of Variable with Unnecessarily Wide Scope
CWE-1127|Base|out-of-scope:generic-precondition-model|parents:710|name:Compilation with Insufficient Warnings or Errors
CWE-1164|Class|out-of-scope:generic-precondition-model|parents:710|name:Irrelevant Code
CWE-1173|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Use of Validation Framework
CWE-1174|Variant|duplicate-of:CWE-20|parents:1173|name:ASP.NET Misconfiguration: Improper Model Validation
CWE-1176|Class|out-of-scope:generic-precondition-model|parents:405|name:Inefficient CPU Computation
CWE-1177|Class|out-of-scope:generic-precondition-model|parents:710|name:Use of Prohibited Code
CWE-1188|Base|out-of-scope:generic-precondition-model|parents:1419,344|name:Initialization of a Resource with an Insecure Default
CWE-1189|Base|out-of-scope:hardware-firmware-model|parents:653,668|name:Improper Isolation of Shared Resources on System-on-a-Chip (SoC)
CWE-1190|Base|out-of-scope:generic-precondition-model|parents:696|name:DMA Device Enabled Too Early in Boot Phase
CWE-1191|Base|out-of-scope:authn-authz-boundary-predicate|parents:284|name:On-Chip Debug and Test Interface With Improper Access Control
CWE-1192|Base|out-of-scope:hardware-firmware-model|parents:657|name:Improper Identifier for IP Block used in System-On-Chip (SOC)
CWE-1193|Base|out-of-scope:authn-authz-boundary-predicate|parents:696|name:Power-On of Untrusted Execution Core Before Enabling Fabric Access Control
CWE-1204|Base|out-of-scope:crypto-primitive-model|parents:330|name:Generation of Weak Initialization Vector (IV)
CWE-1209|Base|out-of-scope:generic-precondition-model|parents:710|name:Failure to Disable Reserved Bits
CWE-1220|Base|out-of-scope:authn-authz-boundary-predicate|parents:284|name:Insufficient Granularity of Access Control
CWE-1221|Base|out-of-scope:hardware-firmware-model|parents:1419|name:Incorrect Register Defaults or Module Parameters
CWE-1222|Variant|out-of-scope:hardware-firmware-model|parents:1220|name:Insufficient Granularity of Address Regions Protected by Register Locks
CWE-1223|Base|duplicate-of:CWE-362|parents:362|name:Race Condition for Write-Once Attributes
CWE-1224|Base|out-of-scope:generic-precondition-model|parents:284|name:Improper Restriction of Write-Once Bit Fields
CWE-1229|Class|out-of-scope:generic-precondition-model|parents:664|name:Creation of Emergent Resource
CWE-1230|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:285|name:Exposure of Sensitive Information Through Metadata
CWE-1231|Base|out-of-scope:generic-precondition-model|parents:284|name:Improper Prevention of Lock Bit Modification
CWE-1232|Base|out-of-scope:generic-precondition-model|parents:667|name:Improper Lock Behavior After Power State Transition
CWE-1233|Base|out-of-scope:hardware-firmware-model|parents:284,667|name:Security-Sensitive Hardware Controls with Missing Lock Bit Protection
CWE-1234|Base|out-of-scope:hardware-firmware-model|parents:667|name:Hardware Internal or Debug Modes Allow Override of Locks
CWE-1235|Base|out-of-scope:generic-precondition-model|parents:400|name:Incorrect Use of Autoboxing and Unboxing for Performance Critical Operations
CWE-1236|Base|out-of-scope:sink-classification-model|parents:74|name:Improper Neutralization of Formula Elements in a CSV File
CWE-1239|Variant|out-of-scope:hardware-firmware-model|parents:226|name:Improper Zeroization of Hardware Register
CWE-1240|Base|out-of-scope:crypto-primitive-model|parents:327|name:Use of a Cryptographic Primitive with a Risky Implementation
CWE-1241|Base|out-of-scope:crypto-primitive-model|parents:330|name:Use of Predictable Algorithm in Random Number Generator
CWE-1242|Base|out-of-scope:generic-precondition-model|parents:912|name:Inclusion of Undocumented Features or Chicken Bits
CWE-1243|Base|out-of-scope:generic-precondition-model|parents:1263|name:Sensitive Non-Volatile Information Not Protected During Debug
CWE-1244|Base|out-of-scope:generic-precondition-model|parents:863|name:Internal Asset Exposed to Unsafe Debug Access Level or State
CWE-1245|Base|out-of-scope:hardware-firmware-model|parents:684|name:Improper Finite State Machines (FSMs) in Hardware Logic
CWE-1246|Base|out-of-scope:generic-precondition-model|parents:400|name:Improper Write Handling in Limited-write Non-Volatile Memories
CWE-1247|Base|out-of-scope:hardware-firmware-model|parents:1384|name:Improper Protection Against Voltage and Clock Glitches
CWE-1248|Base|out-of-scope:hardware-firmware-model|parents:693|name:Semiconductor Defects in Hardware Logic with Security-Sensitive Implications
CWE-1249|Base|out-of-scope:generic-precondition-model|parents:1250|name:Application-Level Admin Tool with Inconsistent View of Underlying Operating System
CWE-1250|Base|out-of-scope:generic-precondition-model|parents:664|name:Improper Preservation of Consistency Between Independent Representations of Shared State
CWE-1251|Base|out-of-scope:generic-precondition-model|parents:1250|name:Mirrored Regions with Different Values
CWE-1252|Base|out-of-scope:hardware-firmware-model|parents:284|name:CPU Hardware Not Configured to Support Exclusivity of Write and Execute Operations
CWE-1253|Base|out-of-scope:generic-precondition-model|parents:693|name:Incorrect Selection of Fuse Values
CWE-1254|Base|out-of-scope:generic-precondition-model|parents:208,697|name:Incorrect Comparison Logic Granularity
CWE-1255|Variant|out-of-scope:hardware-firmware-model|parents:1300|name:Comparison Logic is Vulnerable to Power Side-Channel Attacks
CWE-1256|Base|out-of-scope:hardware-firmware-model|parents:285|name:Improper Restriction of Software Interfaces to Hardware Features
CWE-1257|Base|out-of-scope:memory-model|parents:284|name:Improper Access Control Applied to Mirrored or Aliased Memory Regions
CWE-1258|Base|out-of-scope:generic-precondition-model|parents:212|name:Exposure of Sensitive System Information Due to Uncleared Debug Information
CWE-1259|Base|out-of-scope:generic-precondition-model|parents:284|name:Improper Restriction of Security Token Assignment
CWE-1260|Base|out-of-scope:memory-model|parents:284|name:Improper Handling of Overlap Between Protected Memory Ranges
CWE-1261|Base|out-of-scope:generic-precondition-model|parents:1384|name:Improper Handling of Single Event Upsets
CWE-1262|Base|out-of-scope:authn-authz-boundary-predicate|parents:284|name:Improper Access Control for Register Interface
CWE-1263|Class|out-of-scope:authn-authz-boundary-predicate|parents:284|name:Improper Physical Access Control
CWE-1264|Base|out-of-scope:concurrency-scheduling-model|parents:821|name:Hardware Logic with Insecure De-Synchronization between Control and Data Channels
CWE-1265|Base|out-of-scope:generic-precondition-model|parents:662|name:Unintended Reentrant Invocation of Non-reentrant Code Via Nested Calls
CWE-1266|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:404|name:Improper Scrubbing of Sensitive Data from Decommissioned Device
CWE-1267|Base|out-of-scope:sink-classification-model|parents:284|name:Policy Uses Obsolete Encoding
CWE-1268|Base|duplicate-of:CWE-269|parents:266|name:Policy Privileges are not Assigned Consistently Between Control and Data Agents
CWE-1269|Base|out-of-scope:environment-config-model|parents:693|name:Product Released in Non-Release Configuration
CWE-1270|Base|out-of-scope:generic-precondition-model|parents:284|name:Generation of Incorrect Security Tokens
CWE-1271|Base|out-of-scope:memory-model|parents:909|name:Uninitialized Value on Reset for Registers Holding Security Settings
CWE-1272|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:226|name:Sensitive Information Uncleared Before Debug/Power State Transition
CWE-1273|Base|out-of-scope:generic-precondition-model|parents:200|name:Device Unlock Credential Sharing
CWE-1274|Base|out-of-scope:memory-model|parents:284|name:Improper Access Control for Volatile Memory Containing Boot Code
CWE-1275|Variant|out-of-scope:sensitive-data-exposure-sink-model|parents:923|name:Sensitive Cookie with Improper SameSite Attribute
CWE-1276|Base|out-of-scope:hardware-firmware-model|parents:284|name:Hardware Child Block Incorrectly Connected to Parent System
CWE-1277|Base|out-of-scope:hardware-firmware-model|parents:1329|name:Firmware Not Updateable
CWE-1278|Base|out-of-scope:hardware-firmware-model|parents:693|name:Missing Protection Against Hardware Reverse Engineering Using Integrated Circuit (IC) Imaging Techniques
CWE-1279|Base|out-of-scope:crypto-primitive-model|parents:696,665|name:Cryptographic Operations are run Before Supporting Units are Ready
CWE-1280|Base|out-of-scope:authn-authz-boundary-predicate|parents:696,284|name:Access Control Check Implemented After Asset is Accessed
CWE-1281|Base|out-of-scope:generic-precondition-model|parents:691|name:Sequence of Processor Instructions Leads to Unexpected Behavior
CWE-1282|Base|out-of-scope:memory-model|parents:668|name:Assumed-Immutable Data is Stored in Writable Memory
CWE-1283|Base|out-of-scope:generic-precondition-model|parents:284|name:Mutable Attestation or Measurement Reporting Data
CWE-1284|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Validation of Specified Quantity in Input
CWE-1285|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Validation of Specified Index, Position, or Offset in Input
CWE-1286|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Validation of Syntactic Correctness of Input
CWE-1287|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Validation of Specified Type of Input
CWE-1288|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Validation of Consistency within Input
CWE-1289|Base|out-of-scope:generic-precondition-model|parents:20|name:Improper Validation of Unsafe Equivalence in Input
CWE-1290|Base|out-of-scope:generic-precondition-model|parents:284|name:Incorrect Decoding of Security Identifiers
CWE-1291|Base|out-of-scope:generic-precondition-model|parents:693|name:Public Key Re-Use for Signing both Debug and Production Code
CWE-1292|Base|out-of-scope:generic-precondition-model|parents:284|name:Incorrect Conversion of Security Identifiers
CWE-1293|Base|out-of-scope:generic-precondition-model|parents:345|name:Missing Source Correlation of Multiple Independent Data
CWE-1294|Class|out-of-scope:generic-precondition-model|parents:284|name:Insecure Security Identifier Mechanism
CWE-1295|Base|out-of-scope:generic-precondition-model|parents:200|name:Debug Messages Revealing Unnecessary Information
CWE-1296|Base|out-of-scope:generic-precondition-model|parents:284|name:Incorrect Chaining or Granularity of Debug Components
CWE-1297|Base|out-of-scope:generic-precondition-model|parents:285|name:Unprotected Confidential Information on Device is Accessible by OSAT Vendors
CWE-1298|Base|duplicate-of:CWE-362|parents:362|name:Hardware Logic Contains Race Conditions
CWE-1299|Base|out-of-scope:hardware-firmware-model|parents:420,288|name:Missing Protection Mechanism for Alternate Hardware Interface
CWE-1300|Base|out-of-scope:hardware-firmware-model|parents:203|name:Improper Protection of Physical Side Channels
CWE-1301|Base|out-of-scope:hardware-firmware-model|parents:226|name:Insufficient or Incomplete Data Removal within Hardware Component
CWE-1302|Base|out-of-scope:hardware-firmware-model|parents:1294|name:Missing Source Identifier in Entity Transactions on a System-On-Chip (SOC)
CWE-1303|Base|out-of-scope:generic-precondition-model|parents:1189,203|name:Non-Transparent Sharing of Microarchitectural Resources
CWE-1304|Base|out-of-scope:hardware-firmware-model|parents:284|name:Improperly Preserved Integrity of Hardware Configuration State During a Power Save/Restore Operation
CWE-1310|Base|out-of-scope:generic-precondition-model|parents:1329|name:Missing Ability to Patch ROM Code
CWE-1311|Base|out-of-scope:generic-precondition-model|parents:284|name:Improper Translation of Security Attributes by Fabric Bridge
CWE-1312|Base|out-of-scope:hardware-firmware-model|parents:284|name:Missing Protection for Mirrored Regions in On-Chip Fabric Firewall
CWE-1313|Base|out-of-scope:hardware-firmware-model|parents:284|name:Hardware Allows Activation of Test or Debug Logic at Runtime
CWE-1314|Base|out-of-scope:generic-precondition-model|parents:862|name:Missing Write Protection for Parametric Data Values
CWE-1315|Base|out-of-scope:hardware-firmware-model|parents:284|name:Improper Setting of Bus Controlling Capability in Fabric End-point
CWE-1316|Base|out-of-scope:generic-precondition-model|parents:284|name:Fabric-Address Map Allows Programming of Unwarranted Overlaps of Protected and Unprotected Ranges
CWE-1317|Base|out-of-scope:authn-authz-boundary-predicate|parents:284|name:Improper Access Control in Fabric Bridge
CWE-1318|Base|out-of-scope:hardware-firmware-model|parents:693|name:Missing Support for Security Features in On-chip Fabrics or Buses
CWE-1319|Base|out-of-scope:hardware-firmware-model|parents:693|name:Improper Protection against Electromagnetic Fault Injection (EM-FI)
CWE-1320|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:284|name:Improper Protection for Outbound Error Messages and Alert Signals
CWE-1321|Variant|out-of-scope:generic-precondition-model|parents:915|name:Improperly Controlled Modification of Object Prototype Attributes ('Prototype Pollution')
CWE-1322|Base|out-of-scope:concurrency-scheduling-model|parents:834|name:Use of Blocking Code in Single-threaded, Non-blocking Context
CWE-1323|Base|out-of-scope:generic-precondition-model|parents:284|name:Improper Management of Sensitive Trace Data
CWE-1325|Base|out-of-scope:memory-model|parents:770|name:Improperly Controlled Sequential Memory Allocation
CWE-1326|Base|out-of-scope:hardware-firmware-model|parents:693|name:Missing Immutable Root of Trust in Hardware
CWE-1327|Base|out-of-scope:generic-precondition-model|parents:668|name:Binding to an Unrestricted IP Address
CWE-1328|Base|out-of-scope:generic-precondition-model|parents:285|name:Security Version Number Mutable to Older Versions
CWE-1329|Base|out-of-scope:generic-precondition-model|parents:1357,664|name:Reliance on Component That is Not Updateable
CWE-1330|Variant|out-of-scope:memory-model|parents:1301|name:Remanent Data Readable after Memory Erase
CWE-1331|Base|out-of-scope:hardware-firmware-model|parents:653,668|name:Improper Isolation of Shared Resources in Network On Chip (NoC)
CWE-1332|Base|out-of-scope:generic-precondition-model|parents:1384|name:Improper Handling of Faults that Lead to Instruction Skips
CWE-1333|Base|out-of-scope:sink-classification-model|parents:407|name:Inefficient Regular Expression Complexity
CWE-1334|Base|out-of-scope:authn-authz-boundary-predicate|parents:284|name:Unauthorized Error Injection Can Degrade Hardware Redundancy
CWE-1335|Base|out-of-scope:memory-model|parents:682|name:Incorrect Bitwise Shift of Integer
CWE-1336|Base|out-of-scope:sink-classification-model|parents:94|name:Improper Neutralization of Special Elements Used in a Template Engine
CWE-1338|Base|out-of-scope:hardware-firmware-model|parents:693|name:Improper Protections Against Hardware Overheating
CWE-1339|Base|out-of-scope:generic-precondition-model|parents:682|name:Insufficient Precision or Accuracy of a Real Number
CWE-1341|Base|out-of-scope:generic-precondition-model|parents:675|name:Multiple Releases of Same Resource or Handle
CWE-1342|Base|out-of-scope:generic-precondition-model|parents:226|name:Information Exposure through Microarchitectural State after Transient Execution
CWE-1351|Base|out-of-scope:hardware-firmware-model|parents:1384|name:Improper Handling of Hardware Behavior in Exceptionally Cold Environments
CWE-1357|Class|out-of-scope:generic-precondition-model|parents:710|name:Reliance on Insufficiently Trustworthy Component
CWE-1384|Class|out-of-scope:hardware-firmware-model|parents:703|name:Improper Handling of Physical or Environmental Conditions
CWE-1385|Variant|out-of-scope:authn-authz-boundary-predicate|parents:346|name:Missing Origin Validation in WebSockets
CWE-1386|Base|out-of-scope:generic-precondition-model|parents:59|name:Insecure Operation on Windows Junction / Mount Point
CWE-1389|Base|out-of-scope:generic-precondition-model|parents:704|name:Incorrect Parsing of Numbers with Different Radices
CWE-1390|Class|duplicate-of:CWE-287|parents:287|name:Weak Authentication
CWE-1391|Class|out-of-scope:generic-precondition-model|parents:1390|name:Use of Weak Credentials
CWE-1392|Base|out-of-scope:generic-precondition-model|parents:1391|name:Use of Default Credentials
CWE-1393|Base|out-of-scope:generic-precondition-model|parents:1392|name:Use of Default Password
CWE-1394|Base|out-of-scope:crypto-primitive-model|parents:1392|name:Use of Default Cryptographic Key
CWE-1395|Class|out-of-scope:generic-precondition-model|parents:1357,657|name:Dependency on Vulnerable Third-Party Component
CWE-1419|Class|out-of-scope:generic-precondition-model|parents:665|name:Incorrect Initialization of Resource
CWE-1420|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:669|name:Exposure of Sensitive Information during Transient Execution
CWE-1421|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1420|name:Exposure of Sensitive Information in Shared Microarchitectural Structures during Transient Execution
CWE-1422|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1420|name:Exposure of Sensitive Information caused by Incorrect Data Forwarding during Transient Execution
CWE-1423|Base|out-of-scope:sensitive-data-exposure-sink-model|parents:1420|name:Exposure of Sensitive Information caused by Shared Microarchitectural Predictor State that Influences Transient Execution
CWE-1426|Base|out-of-scope:generic-precondition-model|parents:707|name:Improper Validation of Generative AI Output
CWE-1427|Base|out-of-scope:sink-classification-model|parents:77|name:Improper Neutralization of Input Used for LLM Prompting
CWE-1428|Base|out-of-scope:generic-precondition-model|parents:319|name:Reliance on HTTP instead of HTTPS
CWE-1429|Base|out-of-scope:hardware-firmware-model|parents:223|name:Missing Security-Relevant Feedback for Unexecuted Operations in Hardware Interface
CWE-1431|Base|out-of-scope:crypto-primitive-model|parents:200|name:Driving Intermediate Cryptographic State/Results to Hardware Module Outputs
CWE-1434|Base|out-of-scope:generic-precondition-model|parents:440,665|name:Insecure Setting of Generative AI/ML Model Inference Parameters
TOTAL: 944
```

## What this changes in `docs/strata/threat.md`

The prior text ("`cwe-1000` ... Transcribing it wholesale would produce
hundreds of near-identical `OutOfScopeEntry` rows ... out-of-scope spam
that would bury the genuinely actionable gaps") is corrected by this
registry, not superseded operationally: `frob.toml`'s `std.cwe` view
selection stays on `cwe-top-25` for the exhaustiveness GATE (944
near-duplicate `OutOfScopeEntry` rows in the live catalog would still bury
signal in `frob check` output, so the runtime catalog is unchanged), but
the CLAIM that going through CWE-1000 entry-by-entry was worth skipping was
wrong -- it took one systematic pass to produce an honest, falsifiable,
individually-reasoned disposition for all 944 ids, and that pass belongs in
version control as this document, not re-derived from memory next time
someone asks "did we actually look at CWE-1000."

