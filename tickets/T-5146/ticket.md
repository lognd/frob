---
id: T-5146
title: 'A11Y: WCAG 2.2 Level A and AA static rules over HTML/JSX/TSX/Vue/templates
  plus accessibility statement page (42 criteria, 40 static)'
state: queued
kind: ux
origin: human
created: '2026-09-20'
priority: high
parent: T-5140
tier: story
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'owner 2026-09-20: carry the research corpus in the ticket body, not only
    as an attachment'
  actor: logan
  at: '2026-09-20'
  old_length: 1070
  new_length: 26062
designated_repro_test: null
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
45 entries, 40 static: alt on img and svg role=img; heading order and single h1 (also SEO); html lang and lang on parts; page title unique; link and button accessible names; form inputs with labels; autocomplete on identity fields (1.3.5); skip link (2.4.1); focus visible not suppressed (outline:none without replacement); tabindex>0; aria-hidden on focusable; invalid ARIA role/attribute pairs; duplicate ids; autoplay media without controls; video without track kind=captions; target size 24px (2.5.8); prefers-reduced-motion respected when animations exist; color-only meaning (dynamic-only -> axe obligation); contrast (static where colors are literal in CSS, else axe). Accessibility statement page required with the W3C WAI statement contents (commitment, standard applied WCAG 2.2 AA, contact, known limitations, measures, technical prerequisites, tested environments). Authorities: WCAG 2.2, ADA Title II rule 28 CFR 35.200, EAA 2019/882, Section 508, EN 301 549. axe-core/pa11y as an optional adapter for dynamic-only criteria, registered in the tool registry.

# Remaining WCAG 2.2 Level A/AA success criteria lint authorities

Fills gaps left in lint-authorities.md section B (which covered 1.1.1,
1.3.1, 2.4.2, 3.1.1, 2.4.4, 1.4.3, 2.5.8, 3.3.7, 3.3.8). Source: W3C WCAG
2.2, https://www.w3.org/TR/WCAG22/, same fetch as the prior pass, re-grepped
for the criteria below. Where the static extraction did not isolate a clean
sentence, flagged inline; the criterion number/name and level are still
authoritative from the spec's own table of contents.

### 1. SC 1.2.2 Captions (Prerecorded) -- Level A
Authority: W3C WCAG 2.2, Success Criterion 1.2.2
URL: https://www.w3.org/TR/WCAG22/#captions-prerecorded
Quote: extraction did not isolate the operative sentence cleanly this pass (search for "captions are provided for all" returned empty against the stripped text) -- flagging as a partial gap; the criterion's well-documented text requires "Captions are provided for all prerecorded audio content in synchronized media, except when the media is a media alternative for text and is clearly labeled as such."
Lint condition: `<video>`/media-player component lint for a video source with no `<track kind="captions">` (or platform equivalent) attached.
Static: yes

### 2. SC 1.2.5 Audio Description (Prerecorded) -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.2.5
URL: https://www.w3.org/TR/WCAG22/#audio-description-prerecorded
Quote: "Audio description of the prerecorded video content is provided for all prerecorded video content in synchronized media."
Lint condition: media-player component lint for prerecorded video content with no linked audio-description track/alternate source.
Static: yes

### 3. SC 1.4.2 Audio Control -- Level A
Authority: W3C WCAG 2.2, Success Criterion 1.4.2
URL: https://www.w3.org/TR/WCAG22/#audio-control
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule is that if audio plays automatically for more than 3 seconds, a mechanism must exist to pause/stop it or control volume independently of overall system volume.
Lint condition: template lint for an `<audio>`/`<video>` element with `autoplay` and no `controls` attribute and no adjacent pause/mute UI control.
Static: yes

### 4. SC 1.3.4 Orientation -- Level AA (new-ish, WCAG 2.1)
Authority: W3C WCAG 2.2, Success Criterion 1.3.4
URL: https://www.w3.org/TR/WCAG22/#orientation
Quote: "[Content] does not restrict its view and operation to a single display orientation, such as portrait or landscape, unless a specific display orientation is [essential]."
Lint condition: CSS lint for a `@media (orientation: portrait)` (or landscape) rule that hides/breaks core functionality rather than adapting layout, with no documented essential-orientation justification.
Static: yes

### 5. SC 1.3.5 Identify Input Purpose -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.3.5
URL: https://www.w3.org/TR/WCAG22/#identify-input-purpose
Quote: "The purpose of each input field collecting information about the user can be programmatically determined when [the field serves a purpose identified in the WCAG input-purposes list, and the content is implemented using technologies with support for identifying the purpose]."
Lint condition: form-field lint for an `<input>` collecting a common data type (name, email, address, phone) with no matching `autocomplete` attribute value.
Static: yes

### 6. SC 1.4.4 Resize Text -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.4.4
URL: https://www.w3.org/TR/WCAG22/#resize-text
Quote: "[Text can be] resized without assistive technology up to 200 percent without loss of content or functionality."
Lint condition: CSS lint for `font-size` set in fixed `px` with no relative-unit fallback, or a viewport `<meta>` tag containing `user-scalable=no`/`maximum-scale=1` that blocks pinch-zoom.
Static: yes

### 7. SC 1.4.10 Reflow -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.4.10
URL: https://www.w3.org/TR/WCAG22/#reflow
Quote: content must be "presented without loss of content or functionality, and without requiring scrolling in two dimensions" at a 320 CSS-pixel-equivalent width.
Lint condition: CSS lint for a fixed-width layout container (`width: 1024px` with no responsive breakpoint) that would force horizontal scrolling at narrow viewports.
Static: yes

### 8. SC 1.4.11 Non-text Contrast -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.4.11
URL: https://www.w3.org/TR/WCAG22/#non-text-contrast
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires a 3:1 contrast ratio for UI-component boundaries/states and graphical-object elements against adjacent colors.
Lint condition: design-token/CSS lint computing contrast ratio for button borders, form-input outlines, and icon graphics against their background, flagging < 3:1.
Static: yes

### 9. SC 1.4.12 Text Spacing -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.4.12
URL: https://www.w3.org/TR/WCAG22/#text-spacing
Quote: "[When a user overrides] text spacing values ... content or functionality is not lost."
Lint condition: CSS lint for text containers with `overflow: hidden` and no minimum height/line-height allowance, which would clip text when a user-stylesheet increases line-height/letter-spacing/word-spacing per the criterion's specified multipliers.
Static: dynamic-only

### 10. SC 1.4.13 Content on Hover or Focus -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 1.4.13
URL: https://www.w3.org/TR/WCAG22/#content-on-hover-or-focus
Quote: "[The user can] dismiss the additional content without moving pointer hover or keyboard focus, unless the additional content communicates an input error or does not obscure or replace other conten[t]."
Lint condition: component lint for a tooltip/popover triggered by `:hover`/`:focus` with no dismiss mechanism (Esc key handler) and no `pointer-events` allowance to hover into the popover itself.
Static: yes

### 11. SC 2.1.1 Keyboard -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.1.1
URL: https://www.w3.org/TR/WCAG22/#keyboard
Quote: "[All] functionality of the content is operable through a keyboard interface without requiring specific timings for individual keystrokes, except where the underlying [function requires input that depends on the path of the user's movement]."
Lint condition: JS lint for a click-only interactive element (`<div onclick=...>` with no `onkeydown`/`role="button"`/`tabindex="0"`) that has no native keyboard-accessible equivalent.
Static: yes

### 12. SC 2.1.2 No Keyboard Trap -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.1.2
URL: https://www.w3.org/TR/WCAG22/#no-keyboard-trap
Quote: keyboard focus, once moved to a component, "can be moved away ... using only a keyboard interface" with no trapping.
Lint condition: modal/widget-component lint for a custom focus-trap implementation with no documented Escape-key/Tab-cycle exit path.
Static: dynamic-only

### 13. SC 2.1.4 Character Key Shortcuts -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.1.4
URL: https://www.w3.org/TR/WCAG22/#character-key-shortcuts
Quote: single-character key shortcuts must be able to be turned off, remapped, or active only on focus, "if a keyboard shortcut is implemented in content using only letter ... characters."
Lint condition: JS lint for a global `keydown` handler matching a single printable character (`e.key === 'k'`) bound at the document level with no modifier key and no user-configurable disable option.
Static: yes

### 14. SC 2.2.1 Timing Adjustable -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.2.1
URL: https://www.w3.org/TR/WCAG22/#timing-adjustable
Quote: "[For] each time limit that is set by the content, at least one of the following is true: [the user can turn off, adjust, or extend the limit, with documented exceptions]."
Lint condition: session-timeout/form-timeout code lint for a client-side countdown that force-submits or logs the user out with no extend/disable UI presented before expiry.
Static: yes

### 15. SC 2.2.2 Pause, Stop, Hide -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.2.2
URL: https://www.w3.org/TR/WCAG22/#pause-stop-hide
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires a mechanism to pause, stop, or hide any moving, blinking, or scrolling content that starts automatically and lasts more than 5 seconds.
Lint condition: component lint for an auto-rotating carousel/marquee/ticker with no visible pause control.
Static: yes

### 16. SC 2.3.1 Three Flashes or Below Threshold -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.3.1
URL: https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule prohibits content that flashes more than three times in any one-second period, per the General Flash and Red Flash Thresholds.
Lint condition: dynamic-only in general (requires frame-by-frame video/animation analysis); static check limited to flagging any CSS `animation`/`@keyframes` with an iteration rate implying >3 flashes/second on a large screen area.
Static: dynamic-only

### 17. SC 2.4.1 Bypass Blocks (skip link) -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.4.1
URL: https://www.w3.org/TR/WCAG22/#bypass-blocks
Quote: "[A mechanism is available to] bypass blocks of content that are repeated on multiple web pages."
Lint condition: template lint for a page layout with a persistent nav/header of nontrivial size and no "skip to main content" link as the first focusable element.
Static: yes

### 18. SC 2.4.3 Focus Order -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.4.3
URL: https://www.w3.org/TR/WCAG22/#focus-order
Quote: focusable components must "receive focus in an order that preserves meaning and operability" -- extraction confirmed the phrase "meaningful sequence" appears in the related SC 1.3.2 text used as the basis for this ordering requirement.
Lint condition: DOM/tabindex lint for elements with a positive `tabindex` value (see item 25) that reorders focus away from visual/DOM order.
Static: yes

### 19. SC 2.4.6 Headings and Labels -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 2.4.6
URL: https://www.w3.org/TR/WCAG22/#headings-and-labels
Quote: extraction confirmed the word "descriptive" as the operative requirement term; the full criterion text requires headings and labels to "describe topic or purpose."
Lint condition: heading/label content lint for generic non-descriptive text ("Section 1", "Untitled", empty `<label>`).
Static: yes

### 20. SC 2.4.7 Focus Visible -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 2.4.7
URL: https://www.w3.org/TR/WCAG22/#focus-visible
Quote: "[Any keyboard operable user interface has a mode of operation where the keyboard] focus indicator is visible."
Lint condition: CSS lint for a global `:focus { outline: none; }` (or `outline: 0`) rule with no replacement focus-visible style declared elsewhere.
Static: yes

### 21. SC 2.4.11 Focus Not Obscured (Minimum) -- Level AA (new in 2.2)
Authority: W3C WCAG 2.2, Success Criterion 2.4.11
URL: https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires the focused element not be entirely hidden by author-created content (sticky headers/footers) when it receives keyboard focus.
Lint condition: layout lint for a `position: sticky`/`fixed` header/footer with a z-index above scrollable content and no `scroll-margin-top`/`scroll-padding-top` compensation, which would let the sticky element cover a newly focused element.
Static: dynamic-only

### 22. SC 2.5.1 Pointer Gestures -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.5.1
URL: https://www.w3.org/TR/WCAG22/#pointer-gestures
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires multipoint or path-based gestures (pinch-zoom, swipe) to have a single-pointer alternative unless essential.
Lint condition: touch-event-handler lint for a `touchmove`/gesture-library binding (pinch, multi-touch swipe) implementing a core action with no equivalent single-tap/button control.
Static: yes

### 23. SC 2.5.2 Pointer Cancellation -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.5.2
URL: https://www.w3.org/TR/WCAG22/#pointer-cancellation
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires functions triggered by a single pointer to be actuated on the up-event (not down-event), with an ability to abort/undo.
Lint condition: event-handler lint for a critical action (submit, delete) bound to `onmousedown`/`ontouchstart` rather than `onclick`/`onmouseup`/`ontouchend`, which prevents users from moving away to cancel.
Static: yes

### 24. SC 2.5.3 Label in Name -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.5.3
URL: https://www.w3.org/TR/WCAG22/#label-in-name
Quote: for components with a visible text label, the accessible name must contain the visible text -- the criterion's own short name is "Label in Name."
Lint condition: component lint for an `aria-label` value that does not include (or contradicts) the element's visible text content.
Static: yes

### 25. SC 2.5.4 Motion Actuation -- Level A
Authority: W3C WCAG 2.2, Success Criterion 2.5.4
URL: https://www.w3.org/TR/WCAG22/#motion-actuation
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires functionality triggered by device motion (shake to undo, tilt to scroll) to also be operable via a standard UI control, and to be disableable to prevent accidental actuation.
Lint condition: JS lint for a `devicemotion`/`deviceorientation` event handler implementing a core action with no equivalent button/menu control and no way to disable the motion trigger.
Static: yes

### 26. SC 2.5.7 Dragging Movements -- Level AA (new in 2.2)
Authority: W3C WCAG 2.2, Success Criterion 2.5.7
URL: https://www.w3.org/TR/WCAG22/#dragging-movements
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires drag-based functionality (drag-and-drop reordering, slider drag) to have a single-pointer, non-dragging alternative (e.g., up/down buttons).
Lint condition: component lint for a drag-and-drop library integration (sortable list, slider) with no keyboard/button-based reorder alternative in the same component.
Static: yes

### 27. SC 3.1.2 Language of Parts -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 3.1.2
URL: https://www.w3.org/TR/WCAG22/#language-of-parts
Quote: the default human language of each passage or phrase in a different language "can be programmatically determined."
Lint condition: content lint for an inline foreign-language phrase/quote in a page with no `lang="xx"` attribute on the containing element.
Static: yes

### 28. SC 3.2.1 On Focus -- Level A
Authority: W3C WCAG 2.2, Success Criterion 3.2.1
URL: https://www.w3.org/TR/WCAG22/#on-focus
Quote: extraction confirmed the heading "on focus" as the criterion's own short name; the full text requires that "when any component receives focus, it does not initiate a change of context."
Lint condition: form-field lint for an `onfocus` handler that triggers navigation, form submission, or opens a new window, rather than an explicit user-initiated action.
Static: yes

### 29. SC 3.2.2 On Input -- Level A
Authority: W3C WCAG 2.2, Success Criterion 3.2.2
URL: https://www.w3.org/TR/WCAG22/#on-input
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires that changing a form control's setting does not automatically cause a context change unless the user is advised beforehand.
Lint condition: form-field lint for an `onchange` handler on a `<select>`/`<input>` that immediately submits the form or navigates, with no preceding "this will submit the form" notice and no explicit submit button as the alternative.
Static: yes

### 30. SC 3.2.3 Consistent Navigation -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 3.2.3
URL: https://www.w3.org/TR/WCAG22/#consistent-navigation
Quote: extraction confirmed the phrase "occurs in the same relative order" as central to this criterion and 3.2.4; the full text requires navigational mechanisms repeated across pages to appear "in the same relative order each time."
Lint condition: template/layout lint comparing the nav-component structure across page templates for reordered menu items between otherwise-identical layouts.
Static: yes

### 31. SC 3.2.4 Consistent Identification -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 3.2.4
URL: https://www.w3.org/TR/WCAG22/#consistent-identification
Quote: same "same relative order"/consistent-labeling framing as item 30, applied to icons/components with the same function across pages requiring identical labels.
Lint condition: component-library lint for two icon-buttons performing the same action (e.g., "search") labeled differently (`aria-label="Search"` vs `aria-label="Find"`) across templates.
Static: yes

### 32. SC 3.2.6 Consistent Help -- Level A (new in 2.2)
Authority: W3C WCAG 2.2, Success Criterion 3.2.6
URL: https://www.w3.org/TR/WCAG22/#consistent-help
Quote: extraction confirmed the phrase "context-sensitive help" as present in the spec text; the full requirement is that if a help mechanism (contact info, chat, FAQ link) is provided across multiple pages, it must occur "in the same relative order" on each page.
Lint condition: template lint comparing the position of a help/contact/chat-widget component across page layouts for inconsistent placement or omission on some templates.
Static: yes

### 33. SC 3.3.1 Error Identification -- Level A
Authority: W3C WCAG 2.2, Success Criterion 3.3.1
URL: https://www.w3.org/TR/WCAG22/#error-identification
Quote: "[If an] input error is automatically detected, the item that is in error is identified and the error [is described to the user in text]."
Lint condition: form-validation lint for a field marked invalid via color/border change alone with no adjacent text description of the error and no `aria-invalid`/`aria-describedby` linkage.
Static: yes

### 34. SC 3.3.2 Labels or Instructions -- Level A
Authority: W3C WCAG 2.2, Success Criterion 3.3.2
URL: https://www.w3.org/TR/WCAG22/#labels-or-instructions
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires labels or instructions when content requires user input.
Lint condition: form lint for an `<input>`/`<select>`/`<textarea>` with no associated `<label for=...>`, `aria-label`, or `aria-labelledby`.
Static: yes

### 35. SC 3.3.3 Error Suggestion -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 3.3.3
URL: https://www.w3.org/TR/WCAG22/#error-suggestion
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires that when an input error is detected and suggestions for correction are known, they are provided to the user, unless it would jeopardize security or purpose.
Lint condition: form-validation lint for a generic "Invalid input" error message with no field-specific correction hint (expected format, allowed range) available in the validation-schema definition.
Static: yes

### 36. SC 3.3.4 Error Prevention (Legal, Financial, Data) -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 3.3.4
URL: https://www.w3.org/TR/WCAG22/#error-prevention-legal-financial-data
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires, for pages causing legal/financial commitments or data deletion, that submissions are reversible, checked for errors, or confirmed before finalization.
Lint condition: handler lint for a destructive/financial action (delete account, submit payment) with no confirmation step (review screen, "are you sure" dialog, or undo window) before the irreversible server call.
Static: yes

### 37. SC 4.1.2 Name, Role, Value -- Level A
Authority: W3C WCAG 2.2, Success Criterion 4.1.2
URL: https://www.w3.org/TR/WCAG22/#name-role-value
Quote: extraction did not isolate a clean sentence this pass; the well-documented rule requires every UI component's name and role to be programmatically determinable, and states/values to be programmatically settable.
Lint condition: same as items 11/24/34 plus: `<button>`/`<a>` elements with no text content and no `aria-label`, and custom widgets (`role="slider"`, `role="tab"`) missing the ARIA state attributes (`aria-valuenow`, `aria-selected`) their role requires per the ARIA spec.
Static: yes

### 38. SC 4.1.3 Status Messages -- Level AA
Authority: W3C WCAG 2.2, Success Criterion 4.1.3
URL: https://www.w3.org/TR/WCAG22/#status-messages
Quote: "[Status messages] can be programmatically determined through role or properties such that they can be presented to the user by assistive [technology] without receiving focus."
Lint condition: JS lint for a toast/alert/form-success message rendered by injecting DOM content with no `role="status"`/`role="alert"`/`aria-live` region, so screen readers never announce it.
Static: yes

### 39. ARIA Authoring Practices misuse -- role on the wrong element type
Authority: WAI-ARIA Authoring Practices Guide (APG), general role-usage guidance (cross-reference to WCAG 4.1.2)
URL: https://www.w3.org/WAI/ARIA/apg/ (not independently re-fetched this pass -- BLOCKED for a verbatim quote; general knowledge of the APG's own "don't override native semantics" guidance)
Quote: BLOCKED for a verbatim quote this pass.
Lint condition: DOM lint for `role="button"` applied to an element that also has a conflicting native role (e.g., `<a role="button">` with no `href` removed, or `<input role="checkbox">` on a text input), and for `aria-hidden="true"` applied to an element containing a focusable child (button, link, input) -- the focusable child remains tab-reachable but invisible to assistive tech.
Static: yes

### 40. Positive tabindex values
Authority: cross-reference WCAG 2.2 SC 2.4.3 (Focus Order, item 18); HTML spec's own guidance that `tabindex` values greater than 0 are discouraged (not independently re-fetched this pass -- BLOCKED for a verbatim spec quote)
URL: https://www.w3.org/TR/WCAG22/#focus-order
Quote: BLOCKED for a verbatim HTML-spec quote this pass; the WCAG focus-order text applies as cited in item 18.
Lint condition: DOM/JSX lint for `tabindex` attribute values greater than `0` anywhere in markup.
Static: yes

### 41. Empty links/buttons
Authority: cross-reference WCAG 2.2 SC 4.1.2 (item 37) and SC 2.4.4 (lint-authorities.md item B5)
URL: https://www.w3.org/TR/WCAG22/#name-role-value
Quote: same as item 37.
Lint condition: DOM lint for `<a href="...">`/`<button>` elements with empty text content, an icon-only child with no `alt`/`aria-label`, and no accessible name from any source.
Static: yes

### 42. Duplicate IDs
Authority: cross-reference WCAG 2.2 SC 4.1.2 (item 37) -- duplicate IDs break `aria-labelledby`/`aria-describedby`/`for` associations
URL: https://www.w3.org/TR/WCAG22/#name-role-value
Quote: same as item 37 (programmatic determinability breaks when an `id` reference resolves to multiple elements).
Lint condition: build-time HTML lint (e.g., axe-core's `duplicate-id` rule) for more than one element sharing the same `id` attribute value on a rendered page.
Static: yes

### 43. Missing form labels (cross-ref)
See item 34.

### 44. Color-only meaning
Authority: cross-reference WCAG 2.2 SC 1.4.1 Use of Color (Level A; not separately re-fetched this pass beyond the criteria explicitly requested, but is the direct authority for this item) -- BLOCKED for a fresh verbatim quote this pass, citing by criterion number/name only.
URL: https://www.w3.org/TR/WCAG22/#use-of-color
Quote: BLOCKED for a verbatim quote this pass; the criterion's well-documented text requires "color is not used as the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element."
Lint condition: design-token lint for a status/error indicator implemented only via a color class change (`.text-red-500`) with no accompanying icon, text label, or pattern.
Static: yes

### 45. prefers-reduced-motion support
Authority: cross-reference WCAG 2.2 SC 2.3.3 Animation from Interactions (Level AAA, not Level A/AA -- flagging that this exceeds the AA scope the coordinator requested, included anyway since it was explicitly named); W3C WCAG Techniques (not independently re-fetched this pass -- BLOCKED for a verbatim quote)
URL: https://www.w3.org/TR/WCAG22/#animation-from-interactions
Quote: BLOCKED for a verbatim quote this pass; the well-documented technique is wrapping non-essential motion in a `@media (prefers-reduced-motion: reduce)` query that disables/reduces it.
Lint condition: CSS lint for a `transition`/`animation` declaration on a UI-motion effect with no corresponding `@media (prefers-reduced-motion: reduce)` override anywhere in the stylesheet.
Static: yes
