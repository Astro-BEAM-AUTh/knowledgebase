#!/usr/bin/env python3
"""
ASTRO-BEAM-AUTh knowledgebase generator.

Fetches the README (and, for `knowledgebase`, its   docs/ tree) from every public repository in the org, renders them
to a static site, and writes the result to ../dist.

Design notes -> see README.md in repo root for the full explanation)
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import jinja2
import markdown
import yaml
from bs4 import BeautifulSoup

SITE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SITE_DIR.parent
DIST = REPO_ROOT / "dist"

API_ROOT = "https://api.github.com"
RAW_ROOT = "https://raw.githubusercontent.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
UA = "astro-beam-knowledgebase-builder"

FETCH_LOG = {"api": 0, "raw": 0, "git": 0, "cache": 0, "failed": 0}

# Optional local disk cache, off by default
CACHE_DIR = os.environ.get("KB_CACHE_DIR", "").strip()


def _cache_key_path(key: str) -> Path:
    import hashlib
    return Path(CACHE_DIR) / f"{hashlib.sha256(key.encode()).hexdigest()[:28]}.json"


def _cache_get(key: str):
    if not CACHE_DIR:
        return None, False
    p = _cache_key_path(key)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))["v"], True
        except Exception:
            return None, False
    return None, False


def _cache_set(key: str, value) -> None:
    if not CACHE_DIR:
        return
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    try:
        _cache_key_path(key).write_text(json.dumps({"v": value}), encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------------
# Low-level fetch layer: REST API first, raw.githubusercontent.com / git fallback.
# --------------------------------------------------------------------------

def _api_request(path: str, params: dict | None = None):
    url = f"{API_ROOT}{path}"
    if params:
        from urllib.parse import urlencode
        url += "?" + urlencode(params)
    cached, hit = _cache_get("api:" + url)
    if hit:
        FETCH_LOG["cache"] += 1
        return cached
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
        **({"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        _cache_set("api:" + url, data)
        return data


def api_get(path: str, params: dict | None = None):
    """GET against the REST API. Returns None on 404, raises on other errors
    (caller decides whether to fall back)."""
    try:
        return _api_request(path, params)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def raw_get(owner: str, repo: str, ref: str, path: str) -> str | None:
    """Fetch a file straight from the raw CDN. Doesn't touch the API rate
    limit at all, so it's also our fallback when that's exhausted."""
    from urllib.parse import quote
    url = f"{RAW_ROOT}/{owner}/{repo}/{quote(ref)}/{quote(path)}"
    cached, hit = _cache_get("raw:" + url)
    if hit:
        FETCH_LOG["cache"] += 1
        return cached
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            FETCH_LOG["raw"] += 1
            text = resp.read().decode("utf-8", errors="replace")
            _cache_set("raw:" + url, text)
            return text
    except urllib.error.HTTPError:
        return None
    except urllib.error.URLError:
        return None


def git_ls_remote_heads(owner: str, repo: str) -> list[str]:
    """Branch names via the git smart-HTTP protocol. Separate rate bucket
    from the REST API, and doesn't need a token for public repos."""
    cache_key = f"heads:{owner}/{repo}"
    cached, hit = _cache_get(cache_key)
    if hit:
        FETCH_LOG["cache"] += 1
        return cached
    try:
        out = subprocess.run(
            ["git", "ls-remote", "--heads", f"https://github.com/{owner}/{repo}.git"],
            capture_output=True, text=True, timeout=20,
        )
        if out.returncode != 0:
            return []
        heads = []
        for line in out.stdout.splitlines():
            m = re.match(r"^[0-9a-f]+\trefs/heads/(.+)$", line)
            if m:
                heads.append(m.group(1))
        FETCH_LOG["git"] += 1
        _cache_set(cache_key, heads)
        return heads
    except Exception:
        return []


def get_readme(owner: str, repo: str, ref: str) -> tuple[str, str] | None:
    """Returns (content_text, actual_path) for the repo's root README on `ref`, or None if there isn't one. Tries the
    API's readme-detection endpoint (handles README.md/Readme.md/README casing automatically), then falls back to raw
    fetches of the common filename variants."""
    try:
        data = api_get(f"/repos/{owner}/{repo}/readme", {"ref": ref})
        if data and data.get("encoding") == "base64":
            FETCH_LOG["api"] += 1
            text = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return text, data["path"]
    except Exception as e:
        print(f"  [warn] API readme lookup failed for {owner}/{repo}@{ref}: {e}", file=sys.stderr)

    for candidate in ("README.md", "Readme.md", "readme.md", "README.MD", "README.rst", "README"):
        text = raw_get(owner, repo, ref, candidate)
        if text is not None:
            return text, candidate
    return None


def get_file(owner: str, repo: str, ref: str, path: str) -> str | None:
    """Fetch one specific file's text content."""
    try:
        data = api_get(f"/repos/{owner}/{repo}/contents/{path}", {"ref": ref})
        if data and isinstance(data, dict) and data.get("encoding") == "base64":
            FETCH_LOG["api"] += 1
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        pass
    return raw_get(owner, repo, ref, path)


def get_tree(owner: str, repo: str, ref: str) -> list[dict]:
    """Full recursive file tree for a ref. Used only for knowledgebase's
    docs/ walk, so one call is cheap regardless of how it's fetched."""
    try:
        data = api_get(f"/repos/{owner}/{repo}/git/trees/{ref}", {"recursive": "1"})
        if data and "tree" in data:
            FETCH_LOG["api"] += 1
            return data["tree"]
    except Exception as e:
        print(f"  [warn] tree API fetch failed for {owner}/{repo}@{ref}, falling back to a shallow clone: {e}", file=sys.stderr)
    return _get_tree_via_clone(owner, repo, ref)


def _get_tree_via_clone(owner: str, repo: str, ref: str) -> list[dict]:
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="kb-clone-")
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, "--quiet",
             f"https://github.com/{owner}/{repo}.git", tmpdir],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            print(f"  [warn] git clone fallback failed for {owner}/{repo}@{ref}: {proc.stderr.strip()}", file=sys.stderr)
            return []
        FETCH_LOG["git"] += 1
        tree = []
        for dirpath, dirnames, filenames in os.walk(tmpdir):
            if ".git" in dirnames:
                dirnames.remove(".git")
            for fn in filenames:
                rel = os.path.relpath(os.path.join(dirpath, fn), tmpdir).replace(os.sep, "/")
                tree.append({"path": rel, "type": "blob", "sha": None})
        return tree
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def last_commit_date(owner: str, repo: str, path: str, ref: str) -> str | None:
    cache_key = f"lastcommit:{owner}/{repo}/{ref}/{path}"
    cached, hit = _cache_get(cache_key)
    if hit:
        FETCH_LOG["cache"] += 1
        return cached
    try:
        data = api_get(f"/repos/{owner}/{repo}/commits", {"path": path, "sha": ref, "per_page": 1})
        if data:
            FETCH_LOG["api"] += 1
            date = data[0]["commit"]["committer"]["date"]
            _cache_set(cache_key, date)
            return date
    except Exception as e:
        print(f"  [warn] last-commit-date lookup failed for {owner}/{repo}@{ref}:{path}: {e}", file=sys.stderr)
    return None


def list_public_repos(org: str) -> list[dict]:
    """The one and only place repo visibility is decided.
    Deliberately has no fallback.
    """
    try:
        repos = api_get(f"/orgs/{org}/repos", {"type": "public", "per_page": 100})
    except Exception as e:
        raise RuntimeError(
            f"Could not list org repos from the GitHub API ({e!r}). This is "
            f"usually a rate limit or transient network issue — there is no "
            f"safe fallback for repo *discovery* (unlike README content, "
            f"which does have one), because guessing wrong here could mean "
            f"guessing a repo is public when it isn't. Retry once the rate "
            f"limit window resets (see https://api.github.com/rate_limit), "
            f"or set GITHUB_TOKEN for a much higher limit."
        ) from e
    if not repos:
        raise RuntimeError("GitHub API returned no public repos for the org — refusing to build an empty site; check the org name in config.yml.")
    FETCH_LOG["api"] += 1
    return [r for r in repos if r["private"] is False]


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------

def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "x"


def normalize_for_diff(text: str) -> str:
    """Collapse whitespace so two READMEs that differ only in line endings
    or trailing spaces don't count as 'different'."""
    return re.sub(r"\s+", " ", text).strip()


def differs(a: str | None, b: str | None, threshold: int) -> bool:
    if a is None or b is None:
        return a is not b
    na, nb = normalize_for_diff(a), normalize_for_diff(b)
    if na == nb:
        return False
    # cheap edit-distance proxy: length delta plus a straight compare avoids
    # pulling in a diff library for what's ultimately a "is this worth a
    # whole extra page" judgment call, not a precise diff.
    common = os.path.commonprefix([na, nb])
    return (len(na) + len(nb) - 2 * len(common)) > threshold


def depth_prefix(output_path: str) -> str:
    """Relative '../' prefix so every internal link/asset reference works
    whether the site is served from a domain root or a GitHub Pages project
    subpath like /knowledgebase/ — see README.md 'Moving the site'."""
    d = os.path.dirname(output_path)
    if d in ("", "."):
        return ""
    return "../" * (d.count("/") + 1)


CALLOUT_RE = re.compile(r"^\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*", re.IGNORECASE)


def apply_github_callouts(soup: BeautifulSoup) -> None:
    """GitHub's `> [!NOTE]` renders as a plain blockquote in vanilla Markdown. Detect that pattern and turn it into
    a styled callout so mirrored READMEs read the way they do on GitHub."""
    for bq in soup.find_all("blockquote"):
        first_p = bq.find("p")
        if not first_p or not first_p.contents:
            continue
        first_node = first_p.contents[0]
        text = first_node if isinstance(first_node, str) else first_node.get_text()
        m = CALLOUT_RE.match(text.strip())
        if not m:
            continue
        kind = m.group(1).lower()
        remainder = CALLOUT_RE.sub("", text, count=1)
        if isinstance(first_node, str):
            if remainder.strip():
                first_node.replace_with(remainder)
            else:
                first_node.extract()
        existing = bq.get("class", [])
        bq["class"] = existing + ["callout", f"callout-{kind}"]
        label = bq.new_tag("span")
        label["class"] = "callout-label"
        label.string = kind.upper()
        if first_p.contents:
            first_p.insert(0, label)
        else:
            first_p.append(label)


LINK_ORG_RE = None  # set in main() once we know the org name


def rewrite_content(html: str, owner: str, repo: str, ref: str) -> tuple[str, set[str]]:
    """Rewrite an <a>/<img> so a mirrored README still works once it's no longer sitting inside the actual repo:
    relative images point at the raw CDN copy on the right branch, relative links point at the file's real location on github.com.
    """
    soup = BeautifulSoup(html, "html.parser")
    raw_base = f"{RAW_ROOT}/{owner}/{repo}/{ref}/"
    blob_base = f"https://github.com/{owner}/{repo}/blob/{ref}/"
    detected: set[str] = set()

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src and not re.match(r"^([a-z]+:)?//|^data:|^https?://", src, re.IGNORECASE):
            from urllib.parse import urljoin
            img["src"] = urljoin(raw_base, src)
        if img.get("src"):
            img["loading"] = "lazy"
            img["decoding"] = "async"

    for a in soup.find_all("a"):
        href = a.get("href", "")
        if not href or href.startswith(("#", "mailto:")):
            continue
        if re.match(r"^https?://", href, re.IGNORECASE):
            m = LINK_ORG_RE.match(href) if LINK_ORG_RE else None
            if m and m.group(1).lower() != repo.lower():
                detected.add(m.group(1))
            continue
        from urllib.parse import urljoin
        a["href"] = urljoin(blob_base, href)
        a["target"] = "_blank"
        a["rel"] = "noopener"

    apply_github_callouts(soup)
    return str(soup), detected


# --------------------------------------------------------------------------
# Markdown rendering
# --------------------------------------------------------------------------

MD_EXTENSIONS = [
    "tables", "fenced_code", "footnotes", "def_list", "abbr", "attr_list",
    "sane_lists", "nl2br",
    "pymdownx.superfences", "pymdownx.highlight", "pymdownx.tilde",
    "pymdownx.tasklist", "pymdownx.magiclink", "pymdownx.arithmatex",
    "toc",
]
MD_EXT_CFG = {
    "pymdownx.highlight": {"css_class": "hl", "guess_lang": False, "use_pygments": True},
    "pymdownx.tasklist": {"custom_checkbox": True, "clickable_checkbox": False},
    "pymdownx.arithmatex": {"generic": True},
    "pymdownx.magiclink": {"repo_url_shortener": False, "social_url_shortener": False},
    "toc": {"anchorlink": False, "permalink": False, "toc_depth": "2-4"},
}


def render_markdown(text: str, owner: str, repo: str, ref: str) -> dict:
    md = markdown.Markdown(extensions=MD_EXTENSIONS, extension_configs=MD_EXT_CFG)
    html = md.convert(text)
    html, detected_related = rewrite_content(html, owner, repo, ref)
    toc_tokens = getattr(md, "toc_tokens", [])
    title = None
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        title = re.sub(r"[`*_]", "", m.group(1)).strip()
    return {
        "html": html,
        "toc_tokens": toc_tokens,
        "title": title,
        "detected_related": detected_related,
        "word_count": len(text.split()),
    }


# --------------------------------------------------------------------------
# Diagram (Graphviz)
# --------------------------------------------------------------------------

def build_diagram_svg(config: dict, included_repo_names: set[str], tokens: dict) -> str | None:
    cat_by_repo = {}
    for cat in config["categories"]:
        for r in cat["repos"]:
            cat_by_repo[r] = cat["id"]

    lines = [
        "digraph G {",
        f'  bgcolor="transparent";',
        f'  rankdir=LR; splines=ortho; nodesep=0.45; ranksep=0.9;',
        f'  node [shape=box style="rounded,filled" fontname="IBM Plex Mono" '
        f'fontsize=12 penwidth=1.2 margin="0.18,0.12"];',
        f'  edge [fontname="IBM Plex Mono" fontsize=9.5 penwidth=1.1 arrowsize=0.7];',
    ]
    cat_colors = {
        "telescope-control": (tokens["diagram_c1_fill"], tokens["diagram_c1_stroke"]),
        "backend-data": (tokens["diagram_c2_fill"], tokens["diagram_c2_stroke"]),
        "analysis-autonomy": (tokens["diagram_c3_fill"], tokens["diagram_c3_stroke"]),
        "frontend": (tokens["diagram_c4_fill"], tokens["diagram_c4_stroke"]),
        "infra-docs": (tokens["diagram_c5_fill"], tokens["diagram_c5_stroke"]),
    }
    for repo in sorted(included_repo_names):
        if repo == ".github":
            continue  # org-standards repo clutters the pipeline view; it's cross-cutting, listed in the legend instead
        cat = cat_by_repo.get(repo, "infra-docs")
        fill, stroke = cat_colors.get(cat, (tokens["diagram_c5_fill"], tokens["diagram_c5_stroke"]))
        label = repo.replace("-", "-\\n") if len(repo) > 14 else repo
        lines.append(f'  "{repo}" [label="{label}" fillcolor="{fill}" color="{stroke}" fontcolor="{tokens["ink"]}"];')

    for edge in config.get("relationships", []):
        src, dst, label = edge
        if src not in included_repo_names or dst not in included_repo_names:
            continue
        short = (label[:34] + "…") if len(label) > 35 else label
        lines.append(f'  "{src}" -> "{dst}" [label="{short}" color="{tokens["ink_soft"]}" fontcolor="{tokens["ink_soft"]}"];')

    lines.append("}")
    dot_src = "\n".join(lines)

    try:
        proc = subprocess.run(
            ["dot", "-Tsvg"], input=dot_src, capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            print(f"  [warn] graphviz failed: {proc.stderr}", file=sys.stderr)
            return None
        svg = proc.stdout
        svg = re.sub(r"^.*?(?=<svg)", "", svg, flags=re.DOTALL)
        svg = re.sub(r'(<svg[^>]*?)\swidth="[\d.]+pt"\s', r"\1 ", svg, count=1)
        svg = re.sub(r'(<svg[^>]*?)\sheight="[\d.]+pt"\s', r"\1 ", svg, count=1)
        svg = svg.replace("<svg", '<svg class="system-map-svg" preserveAspectRatio="xMidYMid meet"', 1)
        return svg
    except FileNotFoundError:
        print("  [warn] graphviz `dot` not found on PATH — skipping system-map diagram", file=sys.stderr)
        return None


def get_file_bytes(owner: str, repo: str, ref: str, path: str) -> bytes | None:
    """Like get_file, but returns raw bytes — used for copying guide-tree assets (images, the pre-rendered HTML embeds, etc.)
    where decoding as UTF-8 text could corrupt a binary file."""
    cache_key = f"bytes:{owner}/{repo}/{ref}/{path}"
    cached, hit = _cache_get(cache_key)
    if hit:
        FETCH_LOG["cache"] += 1
        return base64.b64decode(cached)
    try:
        data = api_get(f"/repos/{owner}/{repo}/contents/{path}", {"ref": ref})
        if data and isinstance(data, dict) and data.get("encoding") == "base64":
            FETCH_LOG["api"] += 1
            _cache_set(cache_key, data["content"])
            return base64.b64decode(data["content"])
    except Exception:
        pass
    from urllib.parse import quote
    url = f"{RAW_ROOT}/{owner}/{repo}/{quote(ref)}/{quote(path)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as resp:
            FETCH_LOG["raw"] += 1
            content = resp.read()
            _cache_set(cache_key, base64.b64encode(content).decode("ascii"))
            return content
    except Exception:
        return None


DESIGN_TOKENS = {
    "ink": "#1C2733",
    "ink_soft": "#4B5A64",
    "diagram_c1_fill": "#E4E9E6", "diagram_c1_stroke": "#7C8B84",   # telescope-control
    "diagram_c2_fill": "#EFE3D0", "diagram_c2_stroke": "#B8791E",   # backend-data
    "diagram_c3_fill": "#E2E8EC", "diagram_c3_stroke": "#3E5C76",   # analysis-autonomy
    "diagram_c4_fill": "#EDE6EE", "diagram_c4_stroke": "#7A5C82",   # frontend
    "diagram_c5_fill": "#EAEAE6", "diagram_c5_stroke": "#8A8F87",   # infra-docs
}


# --------------------------------------------------------------------------
# Per-repo processing
# --------------------------------------------------------------------------

def process_repo(org: str, meta: dict, config: dict) -> tuple[dict, list[dict]]:
    name = meta["name"]
    default_branch = meta["default_branch"]
    slug = config.get("slug_overrides", {}).get(name, name)
    display_name = config.get("display_names", {}).get(name, name)
    description = meta.get("description") or config.get("description_overrides", {}).get(name, "")

    try:
        branches_api = api_get(f"/repos/{org}/{name}/branches", {"per_page": 100})
    except Exception as e:
        print(f"  [warn] branches API failed for {name}, falling back to git ls-remote: {e}", file=sys.stderr)
        branches_api = None
    if branches_api is not None:
        FETCH_LOG["api"] += 1
        branch_names = [b["name"] for b in branches_api]
    else:
        branch_names = git_ls_remote_heads(org, name)
    if default_branch not in branch_names:
        branch_names.append(default_branch)

    exclude_patterns = [re.compile(p) for p in config["branch_display"]["exclude_patterns"]]
    others = sorted(b for b in set(branch_names) if b != default_branch and not any(p.search(b) for p in exclude_patterns))
    candidate_branches = [default_branch] + others

    readme_result = get_readme(org, name, default_branch)
    default_text = readme_result[0] if readme_result else ""
    default_path = readme_result[1] if readme_result else "README.md"
    if not readme_result:
        print(f"  [warn] {name}: no README found on default branch '{default_branch}'", file=sys.stderr)

    threshold = config["branch_display"]["diff_threshold_chars"]
    max_branches = config["branch_display"]["max_branches_shown"]

    shown_branches = [default_branch]
    branch_texts = {default_branch: default_text}
    for b in candidate_branches[1:]:
        if len(shown_branches) >= max_branches:
            break
        r = get_readme(org, name, b)
        text = r[0] if r else None
        if text is not None and differs(default_text, text, threshold):
            branch_texts[b] = text
            shown_branches.append(b)

    pages = []
    detected_related: set[str] = set()
    repo_last_updated = None

    for b in shown_branches:
        text = branch_texts[b]
        if not text:
            continue
        rendered = render_markdown(text, org, name, b)
        detected_related |= rendered["detected_related"]
        out_path = f"repos/{slug}/index.html" if b == default_branch else f"repos/{slug}/branch/{slugify(b)}/index.html"
        ts = last_commit_date(org, name, default_path, b)
        if b == default_branch:
            repo_last_updated = ts
        pages.append({
            "output_path": out_path, "kind": "repo", "repo": name, "branch": b,
            "is_default_branch": b == default_branch,
            "title": rendered["title"] or display_name,
            "html": rendered["html"], "toc_tokens": rendered["toc_tokens"],
            "last_updated": ts,
            "source_url": f"https://github.com/{org}/{name}/blob/{b}/{default_path}",
            "word_count": rendered["word_count"],
        })

    for extra in config.get("extra_tracked_paths", {}).get(name, []):
        text = get_file(org, name, default_branch, extra["path"])
        if text is None:
            print(f"  [warn] {name}: extra tracked path '{extra['path']}' not found on {default_branch}", file=sys.stderr)
            continue
        rendered = render_markdown(text, org, name, default_branch)
        detected_related |= rendered["detected_related"]
        extra_slug = slugify(extra.get("title") or extra["path"])
        out_path = f"repos/{slug}/{extra_slug}/index.html"
        ts = last_commit_date(org, name, extra["path"], default_branch)
        pages.append({
            "output_path": out_path, "kind": "repo-extra", "repo": name, "branch": default_branch,
            "is_default_branch": True,
            "title": extra.get("title", extra["path"]),
            "html": rendered["html"], "toc_tokens": rendered["toc_tokens"],
            "last_updated": ts,
            "source_url": f"https://github.com/{org}/{name}/blob/{default_branch}/{extra['path']}",
            "word_count": rendered["word_count"], "parent_slug": slug,
        })

    summary = {
        "name": name, "slug": slug, "display_name": display_name,
        "description": description, "archived": meta["archived"],
        "default_branch": default_branch, "branches_shown": shown_branches,
        "url": f"repos/{slug}/index.html", "last_updated": repo_last_updated,
        "detected_related": detected_related,
        "extra_pages": [p for p in pages if p["kind"] == "repo-extra"],
    }
    return summary, pages


# --------------------------------------------------------------------------
# knowledgebase/docs/** -> "Guides" section
# --------------------------------------------------------------------------

def process_guides(org: str, config: dict, repo_by_name: dict) -> tuple[list[dict], dict]:
    gsrc = config["guides_source"]
    repo, base_path = gsrc["repo"], gsrc["path"]
    if repo not in repo_by_name:
        print(f"  [warn] guides_source repo '{repo}' not in the built repo set — skipping guides", file=sys.stderr)
        return [], {"children": {}, "page": None}

    default_branch = repo_by_name[repo]["default_branch"]
    tree = get_tree(org, repo, default_branch)
    md_entries = [t for t in tree if t["type"] == "blob" and t["path"].startswith(base_path + "/") and t["path"].lower().endswith(".md")]
    asset_entries = [t for t in tree if t["type"] == "blob" and t["path"].startswith(base_path + "/") and not t["path"].lower().endswith(".md")]

    pages = []
    for entry in md_entries:
        rel_path = entry["path"][len(base_path) + 1:]
        parts = rel_path.split("/")
        filename, dir_parts = parts[-1], parts[:-1]
        text = get_file(org, repo, default_branch, entry["path"])
        if text is None:
            continue
        rendered = render_markdown(text, org, repo, default_branch)

        is_readme = filename.lower() == "readme.md"
        nav_path = dir_parts if is_readme else dir_parts + [filename[:-3]]
        slug_parts = [slugify(p) for p in nav_path] or ["overview"]
        out_path = "guides/" + "/".join(slug_parts) + "/index.html"

        title = rendered["title"]
        if not title:
            base = nav_path[-1] if nav_path else "Guide"
            title = base.replace("-", " ").replace("_", " ").title()

        ts = last_commit_date(org, repo, entry["path"], default_branch)

        src_dir = "/".join([base_path] + dir_parts) if dir_parts else base_path
        siblings = [a for a in asset_entries if "/".join(a["path"].split("/")[:-1]) == src_dir]
        out_dir_slug_parts = [slugify(p) for p in dir_parts]
        sibling_links = [{
            "name": sib["path"].split("/")[-1],
            "href": "/".join(["guides"] + out_dir_slug_parts + [sib["path"].split("/")[-1]]),
            "is_html": sib["path"].lower().endswith(".html"),
        } for sib in siblings]

        pages.append({
            "output_path": out_path, "kind": "guide", "repo": repo, "branch": default_branch,
            "title": title, "html": rendered["html"], "toc_tokens": rendered["toc_tokens"],
            "last_updated": ts,
            "source_url": f"https://github.com/{org}/{repo}/blob/{default_branch}/{entry['path']}",
            "word_count": rendered["word_count"], "nav_path": nav_path, "siblings": sibling_links,
        })

    for asset in asset_entries:
        rel = asset["path"][len(base_path) + 1:]
        parts = rel.split("/")
        out_rel = "guides/" + "/".join([slugify(p) for p in parts[:-1]] + [parts[-1]])
        content = get_file_bytes(org, repo, default_branch, asset["path"])
        if content is None:
            continue
        out_file = DIST / out_rel
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(content)

    nav_tree: dict = {"children": {}, "page": None, "label": "Guides"}
    for p in pages:
        node = nav_tree
        for part in p["nav_path"]:
            node = node["children"].setdefault(part, {"children": {}, "page": None, "label": part.replace("-", " ").replace("_", " ").title()})
        node["page"] = p

    return pages, nav_tree


def build_related_map(config: dict, repo_summaries: list[dict], included_names: set[str]) -> dict:
    related: dict = {name: {} for name in included_names}
    for src, dst, label in config.get("relationships", []):
        if src in included_names and dst in included_names:
            related.setdefault(src, {})[dst] = label
    for summary in repo_summaries:
        for other in summary["detected_related"]:
            if other in included_names and other != summary["name"] and other not in related.get(summary["name"], {}):
                related.setdefault(summary["name"], {})[other] = "linked directly from this README"
    return related


def dateformat_filter(iso_str, fmt="%d %b %Y"):
    if not iso_str:
        return "date unknown"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime(fmt)
    except Exception:
        return iso_str


# --------------------------------------------------------------------------
# Rendering + output
# --------------------------------------------------------------------------

def render_site(config, pages, repo_summaries, guide_nav, related_map, recent_items, search_docs, diagram_svg, about_html):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(SITE_DIR / "templates")),
        autoescape=jinja2.select_autoescape(["html"]),
        trim_blocks=True, lstrip_blocks=True,
    )
    env.filters["dateformat"] = dateformat_filter

    categories = config["categories"]
    repo_by_name = {s["name"]: s for s in repo_summaries}
    cat_for_repo = {}
    for c in categories:
        for r in c["repos"]:
            cat_for_repo[r] = c["id"]
    grouped = {c["id"]: [] for c in categories}
    for s in repo_summaries:
        grouped.setdefault(cat_for_repo.get(s["name"], categories[-1]["id"]), []).append(s)

    common_ctx = dict(
        site=config["site"], categories=categories, grouped_repos=grouped,
        repo_by_name=repo_by_name, guide_nav=guide_nav, related_map=related_map,
        organization=config["organization"], math_enabled=bool(config.get("math")),
        build_time=datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
    )

    def write(out_path, template_name, **ctx):
        tmpl = env.get_template(template_name)
        html = tmpl.render(**common_ctx, **ctx, prefix=depth_prefix(out_path), out_path=out_path)
        out_file = DIST / out_path
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(html, encoding="utf-8")

    write("index.html", "home.html", diagram_svg=diagram_svg, recent_items=recent_items)
    write("about/index.html", "about.html", about_html=about_html)
    write("404.html", "404.html")

    for p in pages:
        if p["kind"] == "repo":
            summary = repo_by_name[p["repo"]]
            related = related_map.get(p["repo"], {})
            related_summaries = [(repo_by_name[r], label) for r, label in related.items() if r in repo_by_name]
            siblings = [pg for pg in pages if pg["kind"] == "repo" and pg["repo"] == p["repo"]]
            write(p["output_path"], "repo.html", page=p, repo_summary=summary,
                  related=related_summaries, branch_pages=siblings)
        elif p["kind"] == "repo-extra":
            summary = repo_by_name[p["repo"]]
            write(p["output_path"], "repo_extra.html", page=p, repo_summary=summary)
        elif p["kind"] == "guide":
            write(p["output_path"], "guide.html", page=p)

    (DIST / "search-index.json").write_text(json.dumps(search_docs, ensure_ascii=False), encoding="utf-8")


def copy_static():
    dest = DIST / "static"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(SITE_DIR / "static", dest)


def write_sitemap_robots(config, pages):
    base = (config["site"].get("canonical_url") or "").rstrip("/")
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
    if not base:
        print("  [info] site.canonical_url not set in config.yml — skipping sitemap.xml (fill it in once the Pages URL is known)", file=sys.stderr)
        return
    urls = ["index.html", "about/index.html"] + [p["output_path"] for p in pages]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        loc = f"{base}/{u}"
        if loc.endswith("/index.html"):
            loc = loc[: -len("index.html")]
        lines.append(f"  <url><loc>{loc}</loc></url>")
    lines.append("</urlset>")
    (DIST / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(repo_summaries, pages):
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repos": [{"name": s["name"], "branches_shown": s["branches_shown"], "archived": s["archived"]} for s in repo_summaries],
        "page_count": len(pages),
        "fetch_stats": FETCH_LOG,
    }
    (DIST / "build-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def load_config() -> dict:
    with open(SITE_DIR / "config.yml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    global LINK_ORG_RE
    t0 = time.time()
    config = load_config()
    org = config["organization"]
    LINK_ORG_RE = re.compile(rf"https?://github\.com/{re.escape(org)}/([A-Za-z0-9_.-]+)", re.IGNORECASE)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    print(f"Discovering public repositories in {org} ...")
    all_public = list_public_repos(org)
    excluded = set(config.get("exclude_repos", []))
    repos = [r for r in all_public if r["name"] not in excluded]
    repo_by_name_meta = {r["name"]: r for r in repos}
    print(f"  {len(all_public)} public repos visible; {len(excluded)} excluded by config; building {len(repos)}.")

    repo_summaries, pages = [], []
    for name in sorted(repo_by_name_meta):
        meta = repo_by_name_meta[name]
        print(f"Processing {name} (default branch: {meta['default_branch']}) ...")
        try:
            summary, repo_pages = process_repo(org, meta, config)
        except Exception as e:
            print(f"  [error] {name}: {e!r} — skipping, build continues", file=sys.stderr)
            continue
        print(f"  -> {len(repo_pages)} page(s), branches shown: {summary['branches_shown']}")
        repo_summaries.append(summary)
        pages.extend(repo_pages)

    included_names = {s["name"] for s in repo_summaries}

    print("Processing knowledgebase guides tree ...")
    guide_pages, guide_nav = process_guides(org, config, repo_by_name_meta)
    print(f"  -> {len(guide_pages)} guide page(s)")
    pages.extend(guide_pages)

    print("Fetching org profile (About page) ...")
    gh_repo_meta = repo_by_name_meta.get(".github")
    about_text = None
    if gh_repo_meta:
        about_text = get_file(org, ".github", gh_repo_meta["default_branch"], "profile/README.md")
    about_html = render_markdown(about_text, org, ".github", gh_repo_meta["default_branch"])["html"] if about_text else "<p>Profile README not found.</p>"

    related_map = build_related_map(config, repo_summaries, included_names)

    recent_items = sorted((p for p in pages if p.get("last_updated")), key=lambda p: p["last_updated"], reverse=True)[:10]

    search_docs = [{
        "title": p["title"], "url": p["output_path"], "kind": p["kind"], "repo": p.get("repo"),
        "text": BeautifulSoup(p["html"], "html.parser").get_text(" ", strip=True)[:4000],
    } for p in pages]
    search_docs.append({"title": "About " + config["site"]["short_title"], "url": "about/index.html", "kind": "about", "repo": None,
                         "text": BeautifulSoup(about_html, "html.parser").get_text(" ", strip=True)[:4000]})

    print("Rendering system-map diagram ...")
    diagram_svg = build_diagram_svg(config, included_names, DESIGN_TOKENS)

    print("Rendering site ...")
    render_site(config, pages, repo_summaries, guide_nav, related_map, recent_items, search_docs, diagram_svg, about_html)
    copy_static()
    write_sitemap_robots(config, pages)
    write_manifest(repo_summaries, pages)

    dt = time.time() - t0
    print(f"Build complete in {dt:.1f}s — {len(pages)} pages, {len(repo_summaries)} repos. Fetch stats: {FETCH_LOG}")


if __name__ == "__main__":
    main()
