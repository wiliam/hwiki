from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import typer

from . import get_client
from .._http import HwikiHttpError
from .._manifest import (
    content_hash, find_manifest_dir, load_manifest, save_manifest, MANIFEST_FILE,
)
from .._frontmatter import read_frontmatter
from .._md_to_storage import md_to_storage

_ID_FROM_FILENAME = re.compile(r'^(\d+)[-.]')

name = "push"
help_text = "Push local Markdown changes back to Confluence"


def run(
    target: Optional[str] = typer.Argument(None, help="File, page ID, or URL (omit for all)"),
    directory: Optional[Path] = typer.Option(None, "-d", "--dir",
                                              help="Wiki directory (auto-detects if omitted)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show changes without applying"),
    force: bool = typer.Option(False, "--force", help="Push even if wiki version is ahead"),
) -> None:
    # --- Resolve directory and manifest ---
    resolved_dir = _resolve_dir(str(directory) if directory else None, target)
    if resolved_dir is None:
        typer.echo("ERROR: push: cannot find .hwiki.json — specify --dir or run from wiki dir",
                   err=True)
        raise typer.Exit(2)

    try:
        manifest = load_manifest(resolved_dir)
    except FileNotFoundError:
        typer.echo(f"ERROR: push: {resolved_dir / MANIFEST_FILE} not found", err=True)
        raise typer.Exit(2)

    # --- Collect target files ---
    if target:
        target_files = _resolve_target_files(target, resolved_dir, manifest)
        if not target_files:
            typer.echo(f"ERROR: push: cannot find file for {target!r} in {resolved_dir}",
                       err=True)
            raise typer.Exit(2)
    else:
        target_files = sorted(resolved_dir.glob("*.md"))

    # page_map for link conversion: {page_id → (title, space)}
    page_map: dict[str, tuple[str, str]] = {
        pid: (entry["title"], entry["space"])
        for pid, entry in manifest["pages"].items()
    }

    client = get_client()
    pushed = unchanged = conflicts = skipped = 0
    dirty_manifest = False

    for md_path in target_files:
        meta, body = read_frontmatter(md_path)
        page_id = str(meta.get("id", "")).strip()
        if not page_id:
            typer.echo(f"  WARN: {md_path.name}: no id in front-matter — skipping", err=True)
            skipped += 1
            continue

        if page_id not in manifest["pages"]:
            typer.echo(f"  WARN: {md_path.name}: id={page_id} not in manifest — skipping",
                       err=True)
            skipped += 1
            continue

        entry = manifest["pages"][page_id]
        current_hash = content_hash(body)
        if current_hash == entry["content_hash"]:
            unchanged += 1
            continue

        # Dirty — check for conflict
        try:
            wiki_page = client.get_page(page_id)
        except HwikiHttpError as e:
            typer.echo(f"  ERROR: push {page_id}: {e.status_code} {e.body}", err=True)
            skipped += 1
            continue

        wiki_v = wiki_page["version"]
        meta_v = int(meta.get("version", 0))

        if wiki_v > meta_v and not force:
            typer.echo(
                f"  CONFLICT: {entry['title']} (wiki v{wiki_v} > local v{meta_v}) — skipping",
                err=True,
            )
            conflicts += 1
            continue

        title = str(meta.get("title", entry["title"]))
        storage_xhtml = md_to_storage(body, page_map=page_map)

        if dry_run:
            typer.echo(f"  DRY-RUN: would update {title!r} ({page_id}) v{wiki_v}→{wiki_v+1}")
            pushed += 1
            continue

        try:
            updated = client.update_page(
                page_id,
                title=title,
                storage_xhtml=storage_xhtml,
                current_version=wiki_v,
            )
        except HwikiHttpError as e:
            typer.echo(f"  ERROR: update {page_id}: {e.status_code} {e.body}", err=True)
            skipped += 1
            continue

        new_version = updated["version"]
        typer.echo(f"  pushed {title!r} ({page_id}) → v{new_version}")

        # Update manifest entry
        manifest["pages"][page_id] = {
            **entry,
            "version": new_version,
            "content_hash": current_hash,
        }
        # Sync version in front-matter
        meta["version"] = new_version
        write_frontmatter_back = True
        if write_frontmatter_back:
            from .._frontmatter import write_frontmatter
            write_frontmatter(md_path, meta, body)

        pushed += 1
        dirty_manifest = True

    if dirty_manifest and not dry_run:
        save_manifest(resolved_dir, manifest)

    parts = []
    if pushed:
        prefix = "would push" if dry_run else "pushed"
        parts.append(f"{pushed} {prefix}")
    if unchanged:
        parts.append(f"{unchanged} unchanged")
    if conflicts:
        parts.append(f"{conflicts} conflict{'s' if conflicts != 1 else ''}")
    if skipped:
        parts.append(f"{skipped} skipped")
    typer.echo(", ".join(parts) if parts else "nothing to push")


def _resolve_dir(directory_arg: str | None, target_arg: str | None) -> Path | None:
    if directory_arg:
        return Path(directory_arg)
    # If target is a file path, look for manifest starting from that file's dir
    if target_arg and Path(target_arg).exists():
        return find_manifest_dir(Path(target_arg).parent)
    # Walk up from cwd
    return find_manifest_dir(Path.cwd())


def _resolve_target_files(target: str, directory: Path,
                           manifest: dict) -> list[Path]:
    # Case 1: existing file path
    p = Path(target)
    if p.exists() and p.suffix == ".md":
        return [p]

    # Case 2: page ID or URL — find file in directory by id prefix or front-matter
    from .._text import parse_page_id
    from .._frontmatter import read_frontmatter as _rfm
    pid = parse_page_id(target)
    if not pid.isdigit():
        # try resolving display URL without API (just extract numeric ID)
        pass

    # Quick check: filename starts with pid-
    for md_path in sorted(directory.glob(f"{pid}-*.md")) + sorted(directory.glob(f"{pid}.md")):
        return [md_path]

    # Fallback: scan front-matter (slower)
    for md_path in sorted(directory.glob("*.md")):
        try:
            meta, _ = _rfm(md_path)
            if str(meta.get("id", "")) == pid:
                return [md_path]
        except Exception:
            continue

    return []
