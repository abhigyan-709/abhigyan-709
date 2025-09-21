#!/usr/bin/env python3
import re, sys, requests
from datetime import datetime
from urllib.parse import quote

# ====== CONFIGURE THESE ======
API_URL = "https://api.projectdevops.in/blogs"   # returns list of blog objects
SITE_BASE = "https://blogs.projectdevops.in"
# Final target: https://blogs.projectdevops.in/b/<id>-<slug>
LINK_TEMPLATE = "{base}/b/{id}-{slug}"
TOP_N = 5
README_PATH = "README.md"
START_MARK = "<!-- BLOG-POST-LIST:START -->"
END_MARK = "<!-- BLOG-POST-LIST:END -->"
TIMEOUT = 15
# ============================================

def slugify(title: str) -> str:
    # mirror your Next.js-friendly style: lowercase, alnum+hyphen
    s = (title or "").strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s or "post"

def parse_date(item: dict) -> str:
    dt = item.get("created_at") or item.get("updated_at") or ""
    # Try ISO datetime (e.g., 2025-07-27T13:45:00.000Z)
    try:
        dt = dt.replace("Z", "+00:00")
        d = datetime.fromisoformat(dt)
        return d.strftime("%Y-%m-%d")
    except Exception:
        return ""

def fetch_posts():
    # If your API supports filtering (e.g. ?published=true), add it here.
    resp = requests.get(API_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    # Some APIs wrap results in {"results": [...]}
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    if not isinstance(data, list):
        return []

    # Sort newest first if API isn’t already sorted
    def key(x):
        return x.get("created_at") or x.get("updated_at") or ""
    data = sorted(data, key=key, reverse=True)
    return data[:TOP_N]

def to_url(item: dict) -> str:
    _id = str(item.get("_id") or item.get("id") or "").strip()
    title = item.get("title") or "Untitled"
    slug = slugify(title)
    if _id:
        # ensure safe, though _id is usually hex and safe
        return LINK_TEMPLATE.format(base=SITE_BASE, id=quote(_id, safe=""), slug=quote(slug, safe="-"))
    # fallback: just base
    return SITE_BASE

def build_markdown(items):
    lines = []
    for it in items:
        title = it.get("title") or "Untitled"
        url = to_url(it)
        date = parse_date(it)
        if date:
            lines.append(f"- [{title}]({url}) — *{date}*")
        else:
            lines.append(f"- [{title}]({url})")
    return "\n".join(lines) if lines else "_No posts found_"

def update_readme(md_block: str):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"({re.escape(START_MARK)})(.*)({re.escape(END_MARK)})",
        flags=re.DOTALL
    )
    replacement = f"{START_MARK}\n{md_block}\n{END_MARK}"

    if re.search(pattern, content):
        new_content = re.sub(pattern, replacement, content)
    else:
        # If markers were missing, append a new section at the end
        new_content = content + f"\n\n## Latest Blog Posts\n\n{replacement}\n"

    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README updated.")
    else:
        print("README already up to date.")

def main():
    try:
        posts = fetch_posts()
        block = build_markdown(posts)
        update_readme(block)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
