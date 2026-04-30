from __future__ import annotations
import re
from pathlib import Path


_FM_RE = re.compile(r'^---\n(.*?)\n---\n', re.DOTALL)
_INT_RE = re.compile(r'^-?\d+$')


def read_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta = _parse_yaml_simple(m.group(1))
    body = text[m.end():]
    return meta, body


def write_frontmatter(path: Path, meta: dict, body: str) -> None:
    fm_lines = ["---"]
    for k, v in meta.items():
        if v is None:
            fm_lines.append(f"{k}: null")
        elif isinstance(v, bool):
            fm_lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, int):
            fm_lines.append(f"{k}: {v}")
        elif isinstance(v, str):
            # Quote strings that contain special chars or look like numbers
            if _needs_quoting(v):
                escaped = v.replace('"', '\\"')
                fm_lines.append(f'{k}: "{escaped}"')
            else:
                fm_lines.append(f"{k}: {v}")
        else:
            fm_lines.append(f"{k}: {v!r}")
    fm_lines.append("---")
    path.write_text("\n".join(fm_lines) + "\n" + body, encoding="utf-8")


def _needs_quoting(s: str) -> bool:
    if not s:
        return True
    if _INT_RE.match(s):
        return True
    if s.lower() in ("true", "false", "null", "yes", "no"):
        return True
    if any(c in s for c in ':#{}[]|>&*!,'):
        return True
    return False


def _parse_yaml_simple(text: str) -> dict:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            continue
        key, _, val = line.partition(':')
        key = key.strip()
        val = val.strip()
        result[key] = _coerce(val)
    return result


def _coerce(val: str):
    if val == "null" or val == "~":
        return None
    if val == "true":
        return True
    if val == "false":
        return False
    if _INT_RE.match(val):
        return int(val)
    # Quoted string
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1].replace('\\"', '"').replace("\\'", "'")
    return val
