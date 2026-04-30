from __future__ import annotations

import re
import sys
from pathlib import Path

from . import HwikiOperation
from .._http import HwikiHttpError
from .._manifest import (
    content_hash, find_manifest_dir, load_manifest, save_manifest, MANIFEST_FILE,
)
from .._frontmatter import read_frontmatter
from .._md_to_storage import md_to_storage

_ID_FROM_FILENAME = re.compile(r'^(\d+)[-.]')


class Operation(HwikiOperation):
    def configure_arg_parser(self, subparsers):
        p = subparsers.add_parser(
            "push",
            help="push local markdown changes back to Confluence",
        )
        p.add_argument(
            "target", nargs="?", default=None,
            help="file path, page ID, or URL to push (omit for all changed files)",
        )
        p.add_argument("-d", "--dir", default=None, dest="directory",
                       help="local wiki directory (default: auto-detect from .hwiki.json)")
        p.add_argument("--dry-run", action="store_true",
                       help="show what would be pushed without making changes")
        p.add_argument("--force", action="store_true",
                       help="push even if wiki version is ahead (overwrite)")
        p.set_defaults(func=self._run, op=self)

    def _run(self, args):
        # --- Resolve directory and manifest ---
        directory = _resolve_dir(args.directory, args.target)
        if directory is None:
            print("ERROR: push: cannot find .hwiki.json — specify --dir or run from wiki dir",
                  file=sys.stderr)
            sys.exit(2)

        try:
            manifest = load_manifest(directory)
        except FileNotFoundError:
            print(f"ERROR: push: {directory / MANIFEST_FILE} not found", file=sys.stderr)
            sys.exit(2)

        # --- Collect target files ---
        if args.target:
            target_files = _resolve_target_files(args.target, directory, manifest)
            if not target_files:
                print(f"ERROR: push: cannot find file for {args.target!r} in {directory}",
                      file=sys.stderr)
                sys.exit(2)
        else:
            target_files = sorted(directory.glob("*.md"))

        # page_map for link conversion: {page_id → (title, space)}
        page_map: dict[str, tuple[str, str]] = {
            pid: (entry["title"], entry["space"])
            for pid, entry in manifest["pages"].items()
        }

        pushed = unchanged = conflicts = skipped = 0
        dirty_manifest = False

        for md_path in target_files:
            meta, body = read_frontmatter(md_path)
            page_id = str(meta.get("id", "")).strip()
            if not page_id:
                print(f"  WARN: {md_path.name}: no id in front-matter — skipping",
                      file=sys.stderr)
                skipped += 1
                continue

            if page_id not in manifest["pages"]:
                print(f"  WARN: {md_path.name}: id={page_id} not in manifest — skipping",
                      file=sys.stderr)
                skipped += 1
                continue

            entry = manifest["pages"][page_id]
            current_hash = content_hash(body)
            if current_hash == entry["content_hash"]:
                unchanged += 1
                continue

            # Dirty — check for conflict
            try:
                wiki_page = self.client().get_page(page_id)
            except HwikiHttpError as e:
                print(f"  ERROR: push {page_id}: {e.status_code} {e.body}", file=sys.stderr)
                skipped += 1
                continue

            wiki_v = wiki_page["version"]
            meta_v = int(meta.get("version", 0))

            if wiki_v > meta_v and not args.force:
                print(f"  CONFLICT: {entry['title']} (wiki v{wiki_v} > local v{meta_v}) — skipping",
                      file=sys.stderr)
                conflicts += 1
                continue

            title = str(meta.get("title", entry["title"]))
            storage_xhtml = md_to_storage(body, page_map=page_map)

            if args.dry_run:
                print(f"  DRY-RUN: would update {title!r} ({page_id}) v{wiki_v}→{wiki_v+1}")
                pushed += 1
                continue

            try:
                updated = self.client().update_page(
                    page_id,
                    title=title,
                    storage_xhtml=storage_xhtml,
                    current_version=wiki_v,
                )
            except HwikiHttpError as e:
                print(f"  ERROR: update {page_id}: {e.status_code} {e.body}", file=sys.stderr)
                skipped += 1
                continue

            new_version = updated["version"]
            print(f"  pushed {title!r} ({page_id}) → v{new_version}")

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

        if dirty_manifest and not args.dry_run:
            save_manifest(directory, manifest)

        parts = []
        if pushed:
            prefix = "would push" if args.dry_run else "pushed"
            parts.append(f"{pushed} {prefix}")
        if unchanged:
            parts.append(f"{unchanged} unchanged")
        if conflicts:
            parts.append(f"{conflicts} conflict{'s' if conflicts != 1 else ''}")
        if skipped:
            parts.append(f"{skipped} skipped")
        print(", ".join(parts) if parts else "nothing to push")


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
