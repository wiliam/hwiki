from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Optional

import typer

from . import get_client, get_config
from .._http import HwikiHttpError
from .._manifest import (
    Manifest, ManifestEntry, content_hash, load_manifest,
    now_iso, page_filename, save_manifest, MANIFEST_FILE,
)
from .._storage_to_md import storage_to_md
from .._frontmatter import write_frontmatter

name = "pull"
help_text = "Pull a Confluence page tree into local Markdown files"


def run(
    root: str = typer.Argument(..., help="Root page ID or URL"),
    depth: int = typer.Option(0, "-n", "--depth", metavar="N",
                               help="Recursion depth (0 = root only)"),
    directory: Path = typer.Option(Path("./wiki"), "-d", "--dir",
                                    help="Local directory"),
    attachments: bool = typer.Option(False, "--attachments", is_flag=True,
                                      help="Download attachment files"),
    attachments_dir: Optional[Path] = typer.Option(None, "--attachments-dir",
                                                     help="Custom attachments directory"),
) -> None:
    client = get_client()
    cfg = get_config()
    host = cfg["host"].rstrip("/")
    directory.mkdir(parents=True, exist_ok=True)

    root_id = client.resolve_page_id(root)

    # BFS traversal up to depth N
    # queue entries: (page_id, depth)
    queue: deque[tuple[str, int]] = deque([(root_id, 0)])
    visited: set[str] = set()
    ordered_ids: list[str] = []  # insertion order for writing
    pages_data: dict[str, dict] = {}  # page_id → Page

    typer.echo(f"Pulling pages from {host}...", err=True)

    while queue:
        pid, d = queue.popleft()
        if pid in visited:
            continue
        visited.add(pid)

        try:
            page = client.get_page(pid)
        except HwikiHttpError as e:
            typer.echo(f"  WARN: get {pid}: {e.status_code} — skipping", err=True)
            continue

        pages_data[pid] = page
        ordered_ids.append(pid)
        typer.echo(f"  fetched [{d}] {page['title']} ({pid})", err=True)

        if d < depth:
            try:
                children = client.get_children(pid)
                for child in children:
                    if child["id"] not in visited:
                        queue.append((child["id"], d + 1))
            except HwikiHttpError as e:
                typer.echo(f"  WARN: children of {pid}: {e.status_code} — skipping", err=True)

    if not pages_data:
        typer.echo("ERROR: pull: no pages fetched", err=True)
        raise typer.Exit(3)

    # Build link_map and title_index from the full pull set
    link_map: dict[str, str] = {}
    title_index: dict[tuple[str, str], str] = {}
    for pid, page in pages_data.items():
        fname = page_filename(pid, page["title"])
        link_map[pid] = fname
        title_index[(page["space_key"], page["title"])] = pid

    # Load existing manifest (if any) to preserve entries for pages not re-pulled
    existing_manifest: dict = {}
    manifest_path = directory / MANIFEST_FILE
    if manifest_path.exists():
        try:
            existing_manifest = load_manifest(directory).get("pages", {})
        except Exception:
            pass

    manifest_pages: dict[str, ManifestEntry] = dict(existing_manifest)

    # Write md files
    att_dir = directory / "attachments"
    eff_att_dir = attachments_dir if attachments_dir else att_dir
    try:
        att_dir_rel_base = "./" + str(eff_att_dir.relative_to(directory))
    except ValueError:
        att_dir_rel_base = str(eff_att_dir)

    for pid in ordered_ids:
        page = pages_data[pid]
        fname = link_map[pid]
        # Use local attachment paths if files already exist on disk
        att_dir_rel = att_dir_rel_base if _has_local_attachments(eff_att_dir, pid) or attachments else ""
        md_body = storage_to_md(
            page["body_storage"],
            host=host,
            space_key=page["space_key"],
            page_id=pid,
            link_map=link_map,
            title_index=title_index,
            attachment_dir_rel=att_dir_rel,
        )

        meta = {
            "id": pid,
            "title": page["title"],
            "space": page["space_key"],
            "version": page["version"],
            "parent_id": None,
        }
        write_frontmatter(directory / fname, meta, md_body)

        # Download attachments if requested
        if attachments:
            _pull_attachments(client, pid, eff_att_dir)

        manifest_pages[pid] = ManifestEntry(
            title=page["title"],
            space=page["space_key"],
            version=page["version"],
            parent_id=None,
            path=fname,
            content_hash=content_hash(md_body),
        )

    manifest: Manifest = {
        "host": host,
        "space": cfg.get("default_space", ""),
        "root_id": root_id,
        "pulled_at": now_iso(),
        "pages": manifest_pages,
    }
    save_manifest(directory, manifest)

    n = len(ordered_ids)
    typer.echo(f"pulled {n} page{'s' if n != 1 else ''} → {directory}/")


def _has_local_attachments(att_dir: Path, page_id: str) -> bool:
    return att_dir.exists() and any(att_dir.glob(f"{page_id}_*"))


def _pull_attachments(client, page_id: str, att_dir: Path) -> None:
    try:
        data = client._http.get(
            f"rest/api/content/{page_id}/child/attachment",
            params={"limit": 50},
        )
    except HwikiHttpError:
        return
    results = data.get("results", [])
    if not results:
        return
    att_dir.mkdir(exist_ok=True)
    for result in results:
        filename = result["title"]
        download_url = result.get("_links", {}).get("download", "")
        if not download_url:
            continue
        try:
            content = client.get_attachment_content(download_url)
            out_path = att_dir / f"{page_id}_{filename}"
            out_path.write_bytes(content)
            typer.echo(f"    attachment {filename} → {out_path}", err=True)
        except HwikiHttpError as e:
            typer.echo(f"    WARN: attachment {filename}: {e.status_code} — skipping", err=True)
