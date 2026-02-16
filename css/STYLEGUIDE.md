# CSS Token Style Guide

## Token categories

- **Semantic colors**: Use `--color-surface-*`, `--color-text-*`, `--color-accent-*`, and `--color-border-*` for component color decisions.
- **Spacing**: Use `--space-*` for padding, margins, and gaps.
- **Radii**: Use `--radius-*` for corners (`sm`, `md`, `lg`, `pill`).
- **Type scale**: Use `--font-size-*` for heading and UI sizing.

## Usage rules

1. Prefer semantic tokens over hardcoded hex/rgba values inside components.
2. Keep legacy aliases (`--bg`, `--text`, `--border`, etc.) for compatibility while migrating incrementally.
3. For new UI controls, start from `.form-control` or `.btn` and map variants with tokens.
4. For surfaces such as nav, cards, and footer, always pair:
   - surface token (`--bg-secondary`, `--card-bg`, `--nav-bg`)
   - text token (`--text` or `--text-muted`)
   - border token (`--border` / `--color-border-strong`)

## Theme parity checks

- Use the same semantic token names in both `:root` and `[data-theme="light"]`.
- Keep `color-scheme` in sync with the active theme.
- Contrast guardrails are defined via:
  - `@media (prefers-contrast: more)` for stronger text/border pairings.
  - `@media (forced-colors: active)` for system high-contrast support.
