# RFC: Migrate Site from Raw HTML to a Static Site Generator

- **Status:** Proposed
- **Author:** Site maintainers
- **Date:** 2026-02-16
- **Related paths:** `index.html`, `pages/`, `pages/blog/`, `css/`, `js/`, `scripts/`

## 1) Summary

This RFC proposes migrating the site from hand-authored raw HTML files to a static site generator (SSG), with **Astro** or **Eleventy (11ty)** as candidate frameworks.

The migration will happen in three phases to reduce risk:

1. **Phase 1:** Wrap existing pages in shared templates/layouts with no visual changes.
2. **Phase 2:** Move blog content generation into structured markdown/content collections while preserving existing blog URLs under `pages/blog/`.
3. **Phase 3:** Retire ad-hoc duplication and formalize build/deploy pipeline with preview checks.

## 2) Motivation

The current raw HTML approach works but creates growing maintenance cost:

- Shared structure (head metadata, nav/footer, script includes) is duplicated across pages.
- Cross-page updates are error-prone and slow.
- Blog content and listing behavior are harder to evolve without a clear content model.
- Build/deploy and quality checks are informal, increasing regressions risk.

A generator-based approach can preserve the current output while improving maintainability, consistency, and release confidence.

## 3) Goals

- Preserve the existing site appearance during migration.
- Introduce shared layouts/partials to remove duplicated markup.
- Model blog content as structured source files (markdown/frontmatter and/or collections).
- Preserve existing public URL paths, especially `pages/blog/` URLs.
- Add a repeatable build + preview + validation workflow.

## 4) Non-Goals

- Redesigning the site UI in this migration.
- Changing site information architecture.
- Breaking existing links or permalinks.
- Introducing heavy client-side frameworks.

## 5) Candidate Generator Options

### 5.1 Astro

Pros:
- Component-based layouts and islands architecture if progressive enhancement is needed.
- Strong markdown/content collection support.
- Good performance defaults and straightforward static output.

Cons:
- Slightly higher conceptual overhead if only simple templating is needed.

### 5.2 Eleventy (11ty)

Pros:
- Minimal, content-first model and broad templating support.
- Very good for markdown-first sites and incremental migration.
- Lightweight and flexible URL/permalink control.

Cons:
- Less opinionated structure means more conventions to define ourselves.

### 5.3 Selection Criteria

The final choice should prioritize:
- URL/permalink control for strict backward compatibility.
- Ease of wrapping existing HTML into shared templates quickly.
- Low migration complexity for current maintainers.
- CI/deploy integration simplicity.

If both are acceptable, prefer the one that minimizes rewrite effort for Phase 1.

## 6) Migration Plan

### Phase 1 — Template Wrapping (No Visual Changes)

Objective: introduce generator structure while preserving rendered output.

Work items:
- Set up generator project in-place.
- Create shared base layout(s) and partials (head, nav, footer, scripts).
- Convert existing top-level and `pages/*.html` into template/page files.
- Keep CSS, JS, and assets paths stable.
- Verify output HTML remains functionally and visually equivalent.

Acceptance criteria:
- Existing pages render with no intentional visual changes.
- Shared global markup is centralized in layouts/partials.
- Existing URLs continue to resolve.

### Phase 2 — Blog as Structured Content Collection

Objective: migrate blog content generation to structured source while preserving URL compatibility under `pages/blog/`.

Work items:
- Define blog content schema (title, date, tags, summary, slug, canonical path).
- Move blog entries into markdown/content collection files.
- Generate blog index and article pages from collection.
- Preserve existing article URLs under `pages/blog/` via permalink config.
- Add redirects only if absolutely necessary (prefer exact path preservation).

Acceptance criteria:
- Blog pages are generated from structured content.
- Existing blog URLs under `pages/blog/` remain unchanged.
- Blog listing/search behavior remains functional.

### Phase 3 — Build/Deploy Formalization + Preview Checks

Objective: remove ad-hoc duplication and establish a reliable delivery pipeline.

Work items:
- Remove remaining duplicated template fragments and legacy generation paths.
- Define canonical build commands (`dev`, `build`, `preview`).
- Add CI checks: install, build, link/permalink validation, and optional linting.
- Add PR preview deployment checks (e.g., Pages preview, Netlify/Vercel preview, or equivalent).
- Document release/deploy process in `README.md`.

Acceptance criteria:
- Single documented build/deploy path is in active use.
- PRs require passing preview/build checks before merge.
- No remaining critical content path depends on manual duplication.

## 7) URL and Backward Compatibility Requirements

- All existing public URLs must remain valid.
- In particular, blog URLs under `pages/blog/` must be preserved exactly.
- Asset paths should remain stable unless a redirect/mapping is explicitly added.
- If any unavoidable URL drift is discovered, it must be listed and addressed with redirects before cutover.

## 8) Validation Strategy

Per phase:
- Compare generated output against current pages for structure and rendering consistency.
- Run link checks for internal navigation.
- Spot-check metadata, canonical URLs, and script/style includes.

Before rollout:
- Perform preview review of key pages (home, primary nav pages, blog index, several blog posts).
- Confirm no 404 regressions for known URLs.

## 9) Risks and Mitigations

- **Risk:** URL regressions in blog migration.
  - **Mitigation:** explicit permalink mapping and automated URL checks.

- **Risk:** Visual drift after template extraction.
  - **Mitigation:** no-change policy in Phase 1 and side-by-side preview checks.

- **Risk:** Build complexity increases.
  - **Mitigation:** keep tooling minimal; document commands and ownership clearly.

## 10) Rollout and Ownership

- Execute phases sequentially, with each phase merged only after acceptance criteria are met.
- Maintain a short migration checklist in the repository for progress tracking.
- Assign an owner/reviewer for URL compatibility sign-off in Phases 2 and 3.

## 11) Open Questions

- Final generator choice: Astro vs 11ty.
- Preferred preview hosting target for PR checks.
- Whether to add schema validation for frontmatter/content collections from day one.

## 12) Decision Request

Approve this phased migration plan and proceed with Phase 1 implementation, selecting Astro or 11ty based on the criteria in Section 5.
