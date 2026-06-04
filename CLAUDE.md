
<!-- pneuma:start -->
## Pneuma Slide Mode

You are running inside **Pneuma**, a co-creation workspace where you and the user build content together — you edit files, the user sees live results in a browser preview panel.

This is **Slide Mode**: HTML presentation creation with live fixed-viewport preview.

For design workflow, height calculation rules, layout patterns, and quality checklist, consult the `pneuma-slide` skill. Slides have no scroll — getting the layout right requires the skill's guidance.

### Architecture
- `slides/*.html` — HTML fragments per slide (no `<html>`/`<body>` tags)
- `manifest.json` — Slide ordering (always update when adding/removing slides)
- `theme.css` — Shared CSS theme via custom properties
- Canvas: 1280×720px fixed viewport — content beyond this is invisible
- **Content sets**: Each top-level directory (e.g. `en-dark/`, `my-deck/`) is a switchable content set with its own slides, manifest, and theme

### Core Rules
- Content must fit within 1280×720px — overflow is the #1 quality issue (no scroll)
- No CSS animations — they break snapshot-based export and print
- **New task → new content set**: When the user asks for a completely new presentation, create a new top-level directory (content set) rather than overwriting existing content — this preserves seed templates and prior work
- **Importing external content → new content set**: When the user provides original content (uploaded files, pasted slides, or a URL), always create a new content set for it. Place imported files inside the new directory with a proper `manifest.json` and `theme.css`. This ensures seed templates are preserved and all built-in features (set switching, comparison, export) work correctly.
- For new decks: design outline first → theme → scaffold → fill content
- Do not ask for confirmation on simple edits — just do them

<!-- pneuma:end -->

<!-- pneuma:viewer-api:start -->
## Viewer API

### Viewer Context

Each user message may be prefixed with a `<viewer-context>` block.
It describes what the user is currently seeing — the active file, viewport position, and selected elements.
Use this to resolve references like "this page", "here", "this section" in user messages.

### User Actions

Messages may include a `<user-actions>` block listing significant actions
the user performed in the viewer since the last message.
Use this to understand workspace state changes that happened outside of your edits.

### Workspace
- Type: manifest (ordered, multi-file, active file tracking)
- Index file: manifest.json

### Content Sets
This workspace may contain multiple content sets as top-level directories (e.g. en-dark/, ja-light/).
The `<viewer-context>` includes a `content-set` attribute. File paths include the content set prefix.
Always edit files within the active content set's directory unless asked to work across content sets.

### Actions

The viewer supports these operations. Invoke via Bash:
`curl -s -X POST $PNEUMA_API/api/viewer/action -H 'Content-Type: application/json' -d '{"actionId":"<id>","params":{...}}'`

| Action | Description | Params |
|--------|-------------|--------|
| `navigate-to` | Navigate to a specific slide | file: string |

### Scaffold

Initialize workspace with slide scaffolding from a structure spec. When creating a new theme/deck, pass contentSet to avoid overwriting the active content set. **Requires user confirmation in browser.**

Invoke via the viewer action API:
`curl -s -X POST $PNEUMA_API/api/viewer/action -H 'Content-Type: application/json' -d '{"actionId":"scaffold","params":{...}}'`

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | yes | Presentation title |
| `slides` | string | yes | JSON array of {title, subtitle?} |
| `contentSet` | string | no | Target content set name (e.g. 'my-theme'). If omitted, overwrites the active content set. |

Clears: `slides/*.html`, `manifest.json`

### Locator Cards

You may embed clickable navigation cards in your messages using this tag:
`<viewer-locator label="Display Label" data='{"key":"value"}' />`

After creating or editing slides, embed locator cards so the user can jump to them. Navigate by file: `data='{"file":"slides/slide-03.html"}'`. Navigate by number: `data='{"index":3}'`. Switch content set: `data='{"contentSet":"deck-2"}'`. Switch content set and slide: `data='{"contentSet":"deck-2","index":1}'`.

When the user clicks a locator card, the viewer navigates to that location.

**Always** embed locator cards at the end of your response when you create or edit content. The user may have navigated away while you were working — locators let them jump directly to what changed.

### Native Desktop APIs

The runtime provides native desktop capabilities via `/api/native/`. Available when running inside the Pneuma desktop app.

**Discovery:** `curl -s $PNEUMA_API/api/native` — returns `{ available: true, capabilities: { module: [methods...] } }` or `{ available: false }`.
Always check this first to see what's available — the capability list is dynamic and auto-generated from Electron modules.

**Invoke:** `curl -s -X POST $PNEUMA_API/api/native/<module>/<method> -H 'Content-Type: application/json' -d '[...args]'`
Returns `{ ok: true, result: ... }` or `{ ok: false, error: "..." }`.

**Common modules:** `clipboard` (readText, writeText, readImage→base64, writeImage←base64, ...), `shell` (openPath, openExternal, ...), `app` (getVersion, getPath, ...), `system` (platform, cpus, totalMemory, hostname, ...), `screen`, `nativeTheme`, `notification` (show, isSupported), `window` (minimize, maximize, setAlwaysOnTop, getBounds, ...)

<!-- pneuma:viewer-api:end -->

<!-- pneuma:skills:start -->
## Available Skills

The following skills are installed and available for use:

- **pneuma-preferences** — Persistent user preference memory. Consult BEFORE making design, style, or aesthetic decisions in any mode. Also use when starting creative work or when the user corrects your choices.

Use `/<skill-name>` to invoke these skills.
<!-- pneuma:skills:end -->
