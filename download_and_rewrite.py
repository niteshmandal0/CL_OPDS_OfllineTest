#!/usr/bin/env python3
"""
download_and_rewrite.py

Reads a manifest JSON, downloads all http(s) asset URLs referenced in it,
saves them to OUT_ROOT/<hostname>/<path> (query strings produce unique filename suffix),
rewrites the manifest to reference the local files (e.g. /hostname/path),
and optionally starts a simple http.server for local testing.

Usage:
  python3 download_and_rewrite.py --manifest /path/to/ftm_af_1.json --out-root ./local_www --concurrency 8 --serve

Requirements:
  pip install requests tqdm
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import hashlib
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
import sys
import http.server
import socketserver
import threading

ANALYTICS_BLOCKLIST = [
    "googletagmanager.com",
    "google-analytics.com",
    "connect.facebook.net",
    "firebaseinstallations.googleapis.com",
    "firebase.googleapis.com",
    "storage.googleapis.com",
    "analytics.",
]

def is_blocked(url: str, blocklist=ANALYTICS_BLOCKLIST) -> bool:
    if not url or not isinstance(url, str):
        return False
    for bad in blocklist:
        if bad in url:
            return True
    return False

def collect_urls_from_manifest(manifest: dict) -> set:
    urls = set()

    def add_if_http(s):
        if isinstance(s, str) and (s.startswith("http://") or s.startswith("https://")) and not is_blocked(s):
            urls.add(s)

    # common top-level lists
    for key in ("links", "images", "readingOrder", "resources"):
        for item in manifest.get(key, []) or []:
            if isinstance(item, dict):
                href = item.get("href")
                add_if_http(href)
            elif isinstance(item, str):
                add_if_http(item)

    # metadata.identifier
    meta = manifest.get("metadata", {})
    if isinstance(meta, dict):
        add_if_http(meta.get("identifier"))

    # deep search: any string that looks like an absolute http(s) URL
    def deep(o):
        if isinstance(o, dict):
            for v in o.values():
                deep(v)
        elif isinstance(o, list):
            for x in o:
                deep(x)
        elif isinstance(o, str):
            if o.startswith("http://") or o.startswith("https://"):
                add_if_http(o)
    deep(manifest)

    return urls

def url_to_local_path(url: str, out_root: Path) -> (Path, str):
    """
    Returns (local_path, manifest_href)
    local_path: where to save the file (absolute Path)
    manifest_href: the href to write into the rewritten manifest (like "/hostname/path...").
    """
    p = urlparse(url)
    host = p.netloc
    path = unquote(p.path or "/")
    if path.endswith("/"):
        path = path + "index.html"
    if path == "":
        path = "/index.html"
    # if query present, append short hash to filename
    if p.query:
        qhash = hashlib.sha1(p.query.encode("utf-8")).hexdigest()[:8]
        base, ext = os.path.splitext(path)
        # ensure ext exists
        if ext == "":
            ext = ".html"
        # base may be a path; join properly
        # base "/foo/bar" -> "/foo/bar__q_<hash>.ext"
        local_rel = f"{Path(base).as_posix()}__q_{qhash}{ext}"
    else:
        local_rel = path
    # local storage: out_root/host/<local_rel-without-leading-slash>
    local_rel_norm = local_rel.lstrip("/")
    local_path = out_root / host / local_rel_norm
    manifest_href = "/" + "/".join([host] + local_rel_norm.split("/"))
    return local_path, manifest_href

def download_one(session: requests.Session, url: str, local_path: Path, timeout=30, max_retries=3):
    tries = 0
    while tries < max_retries:
        tries += 1
        try:
            # stream download
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with session.get(url, stream=True, timeout=timeout) as resp:
                status = resp.status_code
                if status != 200:
                    return False, status, 0
                total = 0
                with open(local_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            total += len(chunk)
                return True, status, total
        except requests.RequestException as e:
            last_exc = e
            time.sleep(0.5 * tries)
            continue
    # if here: failed
    return False, getattr(last_exc, "response", None) and last_exc.response.status_code or None, 0

def download_urls(urls: set, out_root: Path, concurrency=8, skip_existing=True):
    results = {}
    total_bytes = 0
    failed = []
    pbar = tqdm(total=len(urls), desc="Downloading", unit="file")
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=2)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        future_to_url = {}
        for url in urls:
            local_path, manifest_href = url_to_local_path(url, out_root)
            if skip_existing and local_path.exists():
                results[url] = {"ok": True, "status": 200, "bytes": local_path.stat().st_size, "local": str(local_path), "href": manifest_href}
                total_bytes += local_path.stat().st_size
                pbar.update(1)
                continue
            future = ex.submit(download_one, session, url, local_path)
            future_to_url[future] = (url, local_path, manifest_href)
        for fut in as_completed(future_to_url):
            url, local_path, manifest_href = future_to_url[fut]
            try:
                ok, status, bts = fut.result()
            except Exception as e:
                ok, status, bts = False, None, 0
            if ok:
                results[url] = {"ok": True, "status": status, "bytes": bts, "local": str(local_path), "href": manifest_href}
                total_bytes += bts
            else:
                results[url] = {"ok": False, "status": status, "bytes": bts, "local": str(local_path), "href": manifest_href}
                failed.append(url)
            pbar.update(1)
    pbar.close()
    session.close()
    return results, total_bytes, failed

def rewrite_manifest(manifest: dict, out_root: Path):
    changed = []
    removed = []

    def rewrite_string(s):
        if isinstance(s, str) and (s.startswith("http://") or s.startswith("https://")):
            if is_blocked(s):
                removed.append(s)
                return None
            local_path, manifest_href = url_to_local_path(s, out_root)
            changed.append((s, manifest_href, str(local_path)))
            return manifest_href
        return s

    # rewrite known arrays
    for key in ("links", "images", "readingOrder"):
        items = manifest.get(key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and "href" in it:
                    new = rewrite_string(it["href"])
                    if new is None:
                        it.pop("href", None)
                    else:
                        it["href"] = new

    # resources
    new_resources = []
    for r in manifest.get("resources", []):
        if isinstance(r, dict):
            href = r.get("href")
            if isinstance(href, str):
                if is_blocked(href):
                    removed.append(href)
                    continue
                new = rewrite_string(href)
                if new is None:
                    continue
                r["href"] = new
                new_resources.append(r)
            else:
                new_resources.append(r)
        else:
            new_resources.append(r)
    manifest["resources"] = new_resources

    # metadata.identifier
    if isinstance(manifest.get("metadata"), dict):
        ident = manifest["metadata"].get("identifier")
        if isinstance(ident, str):
            new = rewrite_string(ident)
            if new is None:
                manifest["metadata"].pop("identifier", None)
            else:
                manifest["metadata"]["identifier"] = new

    # deep replace of any other absolute urls
    def deep_replace(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, str):
                    if v.startswith("http://") or v.startswith("https://"):
                        new = rewrite_string(v)
                        if new is None:
                            o.pop(k, None)
                        else:
                            o[k] = new
                else:
                    deep_replace(v)
        elif isinstance(o, list):
            for idx, item in enumerate(list(o)):
                if isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
                    new = rewrite_string(item)
                    if new is None:
                        o[idx] = None
                    else:
                        o[idx] = new
                else:
                    deep_replace(item)
            # remove None introduced
            o[:] = [x for x in o if x is not None]
    deep_replace(manifest)

    return manifest, changed, removed

def save_rewritten_manifest(manifest, out_root: Path, source_manifest_path: Path):
    out_dir = out_root / "rewritten-manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = source_manifest_path.stem + "_local" + source_manifest_path.suffix
    out_path = out_dir / out_name
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return out_path

# serve directory (simple)
def serve(out_root: Path, port=8000):
    Handler = http.server.SimpleHTTPRequestHandler
    os.chdir(out_root)
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving {out_root} at http://localhost:{port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Server stopped.")

def main():
    parser = argparse.ArgumentParser(description="Download assets referenced by a manifest and rewrite it to local paths.")
    parser.add_argument("--manifest", required=True, help="Path to manifest JSON")
    parser.add_argument("--out-root", default="./local_www", help="Output root where assets will be stored (default ./local_www)")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent downloads (default 8)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip download if file already exists")
    parser.add_argument("--serve", action="store_true", help="Start a simple HTTP server after work (port 8000)")
    parser.add_argument("--port", type=int, default=8000, help="Port for server if --serve (default 8000)")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print("Manifest not found:", manifest_path, file=sys.stderr)
        sys.exit(2)
    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    print("Collecting URLs from manifest...")
    urls = collect_urls_from_manifest(manifest)
    print(f"Found {len(urls)} candidate URLs (analytics/tracking filtered).")

    # Download phase
    print("Starting downloads...")
    res, total_bytes, failed = download_urls(urls, out_root, concurrency=args.concurrency, skip_existing=args.skip_existing)
    print(f"Downloaded total bytes: {total_bytes:,}. Failures: {len(failed)}")

    # rewrite manifest to local hrefs
    print("Rewriting manifest to local hrefs...")
    rewritten_manifest, changed, removed = rewrite_manifest(manifest, out_root)
    out_manifest_path = save_rewritten_manifest(rewritten_manifest, out_root, manifest_path)
    print("Saved rewritten manifest to:", out_manifest_path)

    # produce verify summary
    verify = {
        "found_urls_count": len(urls),
        "downloads_total_bytes": total_bytes,
        "download_failures": failed,
        "rewritten_count": len(changed),
        "removed_blocked": len(removed),
        "rewritten_manifest": str(out_manifest_path.resolve()),
    }
    verify_path = out_root / "verify.json"
    with verify_path.open("w", encoding="utf-8") as vf:
        json.dump(verify, vf, indent=2)
    print("Wrote verify summary to:", verify_path)

    # list first few missing expected files (files referenced in rewrite but not present)
    missing = []
    for orig, manifest_href, local_path in changed:
        if not Path(local_path).exists():
            missing.append(local_path)
    if missing:
        print("WARNING: the following rewritten local files are MISSING (you may need to re-run/download or copy them):")
        for m in missing[:200]:
            print("  MISSING:", m)
    else:
        print("All rewritten files exist locally. Good.")

    if args.serve:
        print("Starting local server. Press Ctrl-C to stop.")
        serve(out_root, port=args.port)

if __name__ == "__main__":
    main()
