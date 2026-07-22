# knowledgebase site generator

This directory (`site/`) builds the documentation website at `docs.astrobeam` — a static site that mirrors the README of every public repository in the Astro-BEAM-AUTh organization, plus the guides already in `docs/`, and rebuilds automatically.

This file documents the generator. It does not replace the repository's own top-level `README.md`, which still describes `docs/`'s own structure for
anyone browsing on GitHub directly.

## What it does

`site/build.py` asks the GitHub API which repos in the org are public, skips anything listed in `exclude_repos` in `config.yml`, and for each remaining repo fetches the README from its default branch plus any other branch whose README is actually different from the default branch's version. It separately walks this repo's own `docs/` folder in full (every `.md` file, not just READMEs) and mirrors it under `/guides/`. Everything is rendered through Jinja2 templates into `dist/`, which a GitHub Actions workflow uploads to GitHub Pages. The whole thing reruns every Sunday.

## Features

**Deploying from `knowledgebase`, via GitHub Pages.**
Pages deploying straight from a repo matches `infrastructure`'s own documented `deploy-and-release` workflow that already does this for the Angular apps.

**Repo discovery is dynamic, not a hardcoded list.** `list_public_repos()` in `build.py` asks the API for public repos only, and separately re-checks `private is False`. `rag-tool` never appears in that response and so is never even a candidate If a repo is made private later, or a new private repo is added, it won't be there next build. `ASTRO` is (currently) the one repo excluded by name (in `config.yml`, `exclude_repos`) since it's public but deprecated, superseded by the per-component repos, per `docs/research-how-tos/migrate-to-organization-repos.md`.

**A branch only gets its own page if its README actually differs from the default branch's** (`differs()` in `build.py`, `branch_display` in `config.yml`). Checked against the real org: `data-analysis`'s `feature/gpr` and `feature/ica` branches carry genuinely different, substantial docs and are shown; `HydrogenDetection`, `pipeline-scripts`, and `background-Removal-NN` carry the same two-line stub as `main` and are suppressed; every repo's `develop` branch was identical to `main` at the time of writing (so none show up) but will start showing up automatically the moment that stops being true. Dependabot/Renovate branches are excluded by name pattern regardless of content.

**`knowledgebase/docs/` is mirrored in full, not just its README**, because that's what this repo already is ("project docs, onboarding, guides" per its own description). Every other repo is mirrored at README-only (plus `backend/migrations/README.md`, added by hand to `extra_tracked_paths` after noticing it during setup, because it's genuinely useful internal docs).

**Two self-contained files already in `docs/architecture/system-architecture/` and `docs/protocols/REST API/`** — `architecture-diagram.html` and `redoc-static.html` (a rendered OpenAPI reference) are copied into the build and embedded live via `<iframe>` on their guide pages, rather than re-derived. They already exist and are self-contained (CDN scripts, no other file dependencies).

**The repo relationship map is in `config.yml` (`relationships`).** It started from the categorisation already in `docs/architecture/README.md` (extended to cover `data-analysis`, `optimization`, `reinforcement-learning`, and `portal`, which that table didn't mention yet), plus specific real links noticed while reading each README (e.g. portal generating its TypeScript types from backend's OpenAPI spec). On top of that, the build also scans every rendered README for direct `github.com/Astro-BEAM-AUTh/<repo>` links and adds those automatically as "linked directly from this README" — so a repo whose docs start linking somewhere new picks up a related-repo entry without anyone having to edit `config.yml`.

**Fetches go through `gh_get`-style helpers that try the REST API first and fall back to `raw.githubusercontent.com` / `git ls-remote` on failure.**
This is defensive, because this sandbox's shared network egress hit GitHub's unauthenticated rate limit mid-build, and the fallbacks carried the build to completion anyway. In production, `GITHUB_TOKEN` raises the ceiling to 5000 requests/hour, which is generous for ~13 repos. The fallback exists for resilience against a transient hiccup, not because the primary path is expected to be short on quota.

## Repository layout

```
.github/workflows/build-deploy.yml            the only workflow that actually runs automatically
site/
  build.py             the generator (single file, read top to bottom)
  config.yml           the one file we should edit as the org evolves
  requirements.txt
  templates/           Jinja2 templates
  static/
    css/main.css       hand-authored, no framework
    js/{main,search}.js  vanilla JS, no framework, no build step
    fonts/              self-hosted Spectral / Source Sans 3 / IBM Plex Mono
dist/                  build output, gitignored (this is what gets deployed)
```

## Configuration (`site/config.yml`)

Everything you likely need to change lives here:

- `exclude_repos` - public repos to hide anyway.
- `display_names` / `slug_overrides` - cosmetic name/URL overrides.
- `description_overrides` - used only when a repo's GitHub description is blank.
- `categories` - the sidebar grouping and the system-map diagram's node colouring. Add a repo's name to a category's `repos` list; anything not listed anywhere falls into the last category as a default.
- `relationships` - curated `[from, to, label]` edges for the diagram and the "Related repositories" panel, in addition to auto-detected links.
- `extra_tracked_paths` - non-root READMEs worth their own page.
- `guides_source` - which repo/path is walked in full for the Guides section (currently `knowledgebase`/`docs`).
- `branch_display` - the exclude-pattern list, the diff-significance threshold, and the max branches shown per repo.
- `math: true` - enables KaTeX. Turn off if no repo ever uses `$...$` LaTeX in a README (currently at least `data-analysis`'s `feature/gpr` and `feature/ica` do).
- `canonical_url` - leave blank until you know the final Pages URL; it's only used to generate `sitemap.xml`.

None of the Python code should need touching for day-to-day maintenance, if you find yourself editing `build.py` for something that feels like
"just adding a repo" or "just changing a category," check `config.yml` first.

## Deploying this for the first time

1. Copy everything in this delivery into the root of the `knowledgebase`
   repo (the `.github/workflows/`, `scripts/`, and `site/` directories, plus
   this file). This does **not** touch or replace the existing
   `docs/` folder or the repo's own root `README.md`.
2. Commit and push to `main`.
3. In the repo's Settings → Pages, set Source to **GitHub Actions** (not
   "Deploy from a branch" — this project uses the newer Actions-based Pages
   deployment, which is what `build-deploy.yml` expects).
4. Push will trigger `build-deploy.yml` immediately; watch it in the
   Actions tab. First run typically takes under a minute.
5. Once it's live, note the URL GitHub Pages gives you (something like
   `https://astro-beam-auth.github.io/knowledgebase/`) and put it in
   `site/config.yml`'s `site.canonical_url`, then push again — this is only
   used for `sitemap.xml` and nothing breaks if you skip it.
6. That's the whole setup. The 15-minute schedule takes it from there with
   no further action needed anywhere else in the org.

## Local development

```
cd site
pip install -r requirements.txt
export KB_CACHE_DIR=.devcache   # optional but recommended: caches fetched GitHub data on disk so repeated local builds while you tweak CSS/templates don't
                                # keep re-fetching (or re-hitting rate limits). Never used in CI.
python build.py
# open dist/index.html directly in a browser. All internal links/assets are relative, so this works with no local server needed
```

## Design system

Palette, type, and the reasoning are in `static/css/main.css`'s header comment and `:root` block. Short version: cool blueprint-paper base (`#EFF2F0`). Spectral (serif, headings only) + Source Sans 3 (body) + IBM Plex Mono (code, branch/commit chips, small instrument-style labels), all self-hosted in `static/fonts/` — no Google Fonts CDN at runtime. The one deliberately bold element is the system-map diagram on the homepage, drawn as an actual signal-flow schematic (Graphviz, orthogonal connectors) from `config.yml`'s `relationships`, rather than a generic auto-layout graph.

Retheming: everything routes through the CSS custom properties in `:root` and `[data-theme="dark"]` — change colours there, not scattered through the file. The diagram's category colours are duplicated (by necessity — Python generates the SVG, CSS styles the HTML) in `DESIGN_TOKENS` near the top of `build.py`; a comment in each file points at the other.

## Known limitations

- Last-updated timestamps come from one API call per tracked file (`last_commit_date`). If that call fails, the page just omits the date rather than showing something wrong. Cosmetic-only degradation, and it self-corrects on the next scheduled build.
- The branch-difference check is a cheap length/prefix heuristic, not a real diff. `branch_display.diff_threshold_chars` controls its sensitivity if it ever surfaces (or hides) the wrong branch.
- `extra_tracked_paths` and `guides_source` were populated by hand after actually reading through the org's repos once; a new repo that adds its own meaningful nested README (like `backend/migrations/`) won't be picked up automatically — add it to `config.yml` when you notice one.