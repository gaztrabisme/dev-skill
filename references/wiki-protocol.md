# Wiki Protocol

Persistent project wiki that compounds understanding across sessions. Replaces session-scoped work tracking with a knowledge base Claude maintains directly as markdown.

Inspired by Karpathy's LLM Wiki pattern: knowledge is compiled once and kept current, not re-derived every session. The human curates and directs; Claude does the bookkeeping.

---

## Three Layers

1. **Raw sources** — The codebase, docs, configs, data files. Immutable — Claude reads but never modifies these as part of wiki operations.
2. **The wiki** — `wiki/` directory of Claude-maintained markdown. Summaries, entity pages, decision records, work status. Claude owns this entirely.
3. **The schema** — This protocol file. Tells Claude how to maintain the wiki.

---

## Location

The wiki lives at `wiki/` in the project root (visible in Obsidian, git-trackable). Symlink from `.claude/wiki` for Claude Code native access:

```bash
# First session initialization
mkdir -p wiki
ln -sf "$(pwd)/wiki" .claude/wiki
```

Ask the user: add `wiki/` to `.gitignore` (private) or track it in git (team-shared)?

---

## Wiki Structure

```
wiki/
├── index.md          # Catalog of all pages — one-line summary each
├── log.md            # Append-only chronological record
├── architecture.md   # System architecture understanding
├── decisions.md      # Key decisions and rationale
├── active-work.md    # Current workstreams, status, next steps
└── [topic].md        # Entity pages, concept pages, investigation notes — as needed
```

### index.md

Content-oriented catalog. Every wiki page listed with link + one-line summary, organized by category. Update on every ingest or page creation.

```markdown
# Wiki Index

## Architecture
- [architecture.md](architecture.md) — System overview, component map, data flow

## Decisions
- [decisions.md](decisions.md) — Why we chose X over Y, constraints, tradeoffs

## Active Work
- [active-work.md](active-work.md) — Current workstreams, blockers, next steps

## Topics
- [auth-system.md](auth-system.md) — Authentication flow, token lifecycle, session management
```

### log.md

Append-only. Each entry prefixed consistently for grep-ability:

```markdown
# Wiki Log

## [2026-04-08] session | Initial setup
- Created wiki, ingested codebase architecture
- Started auth-system refactor workstream

## [2026-04-09] session | Auth refactor progress
- Completed token rotation implementation
- Discovered session store race condition — added to active-work.md
```

### active-work.md

Replaces `.tracks/` node files. Each workstream is a section:

```markdown
# Active Work

## Auth System Refactor
**Status:** In progress
**Started:** 2026-04-08
**Goal:** Replace session-token storage for compliance

### Current State
- Token rotation implemented, tests passing
- Session store race condition discovered — needs investigation

### Next Steps
- [ ] Investigate race condition in concurrent session invalidation
- [ ] Add integration tests for token refresh flow

### Breadcrumbs
- 2026-04-09: `SessionStore.invalidate()` not atomic — wraps Redis MULTI but doesn't handle partial failure
- 2026-04-08: Existing tests mock the session store — need real Redis tests
```

---

## Operations

### 1. Ingest (First Encounter or New Major Area)

When entering a project for the first time or exploring a new area:

1. **Check for existing wiki** — Read `wiki/index.md`. If it exists, skip to Session Protocol.
2. **Initialize** — Create `wiki/` directory, symlink, create index.md and log.md.
3. **Build understanding** — Read codebase structure, key files, existing docs. Create:
   - `architecture.md` — Component map, data flow, key abstractions
   - Entity pages for major components (as needed)
   - `active-work.md` — Current state of any in-progress work
4. **Update index.md** — Add all new pages.
5. **Log** — Append ingest entry to log.md.

**Don't over-ingest.** Create pages for what you've actually read and understood, not for everything that exists. Pages grow organically as you work.

### 2. Session Protocol (Every Session)

On entry to any dev mode:

1. **Read** `wiki/index.md` → `wiki/active-work.md`
2. **Brief the user** — Current status, last breadcrumbs, pending items
3. **During work:**
   - Update `active-work.md` with findings, decisions, breadcrumbs
   - Create/update topic pages when you learn something worth preserving
   - Cross-reference: when page A mentions a concept that has page B, link them
4. **On completion:**
   - Update relevant wiki pages with outcomes
   - Append session entry to `log.md`
   - Update `index.md` if new pages were created

### 3. Lint (Periodic or On Request)

Health-check the wiki. Run when user asks, or suggest after 10+ sessions.

Check for:
- **Stale pages** — Last updated many sessions ago. Still accurate?
- **Contradictions** — Page A says X, page B says Y
- **Orphan pages** — In index but never linked from other pages
- **Missing pages** — Concepts referenced but lacking their own page
- **Active-work decay** — Workstreams with no updates. Still active or done?

Output: list of findings, suggested actions. User approves which to fix.

---

## Principles

- **Wiki is Claude's memory, not the user's docs.** It captures what Claude learned about the project — architecture understanding, decision rationale, work state. It's not user-facing documentation (that's in the project's own docs).
- **Compile once, update incrementally.** Don't re-read the entire codebase each session. Read the wiki, work, update what changed.
- **Breadcrumbs over summaries.** Record specific findings ("SessionStore.invalidate() not atomic") not vague summaries ("looked at session code").
- **Pages earn their existence.** A page should exist because it's been referenced or will be referenced. Don't create pages speculatively.
- **Cross-reference aggressively.** The value of a wiki is the links. When you mention a concept that has a page, link it.
