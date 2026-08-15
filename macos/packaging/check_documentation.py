#!/usr/bin/env python3
"""Check local Markdown links and release-language invariants."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
IGNORED_PARTS = {".git", ".tools", ".venv", "node_modules", "target", "build", "dist", "Workspace", "test-results"}


def markdown_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*.md")
        if not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    )


def main() -> None:
    errors: list[str] = []
    for document in markdown_files():
        text = document.read_text(encoding="utf-8")
        for raw in LINK.findall(text):
            target = raw.strip().split()[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_text = unquote(target.split("#", 1)[0])
            if not path_text:
                continue
            resolved = (ROOT / path_text.lstrip("/")) if target.startswith("/") else (document.parent / path_text)
            if not resolved.exists():
                errors.append(f"{document.relative_to(ROOT)}: missing link target {target}")
    public_docs = "\n".join(path.read_text(encoding="utf-8") for path in [ROOT / "README.md", *markdown_files()])
    stale = [
        "local/visioneval:ve-40-rc6-arm64",
        "It does not apply the former local household-alignment patch",
        "Advisory VisionEval release freshness checks that can be disabled",
        "Once daily, it checks the official VisionEval release list",
    ]
    for phrase in stale:
        if phrase in public_docs:
            errors.append(f"stale release language remains: {phrase}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Documentation verified: {len(markdown_files())} Markdown files")


if __name__ == "__main__":
    main()
