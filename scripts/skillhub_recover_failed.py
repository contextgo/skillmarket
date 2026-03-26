#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import codecs
import time
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str((Path(__file__).resolve().parent).resolve()))
from skillhub_mirror import CATALOG_COLUMNS, write_csv, write_summary  # noqa: E402


USER_AGENT = "skillhub-recover/0.1"
README_PATTERN = re.compile(r'readme:"([\s\S]*?)",readmeError:null')


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore").replace("\x00", "")


def extract_readme(html: str) -> str:
    match = README_PATTERN.search(html)
    if not match:
        return ""
    escaped = match.group(1)
    decoded = codecs.decode(escaped, 'unicode_escape')
    return decoded.encode('latin1', 'ignore').decode('utf-8', 'ignore')


def placeholder_skill_markdown(row: dict) -> str:
    description = row.get("description") or row.get("description_zh") or "No public skill body was available."
    return "\n".join(
        [
            "---",
            f"name: {row.get('name') or row.get('slug')}",
            f"description: {json.dumps(description, ensure_ascii=False)}",
            "metadata:",
            f"  synthetic_archive: true",
            f"  source: public-metadata-placeholder",
            "---",
            "",
            f"# {row.get('name') or row.get('slug')}",
            "",
            "This archive was synthesized from public SkillHub / ClawHub metadata because the upstream zip package was unavailable during mirroring.",
            "",
            "## Metadata",
            "",
            f"- slug: `{row.get('slug','')}`",
            f"- version: `{row.get('version','')}`",
            f"- owner: `{row.get('ownerName','')}`",
            f"- homepage: {row.get('homepage','')}",
            f"- category: `{row.get('category','')}`",
            f"- downloads: `{row.get('downloads','')}`",
            f"- stars: `{row.get('stars','')}`",
            f"- installs: `{row.get('installs','')}`",
            "",
            "## Description",
            "",
            str(description),
            "",
            "## Note",
            "",
            "If the upstream package becomes available later, you can replace this synthesized archive with the original zip.",
            "",
        ]
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_zip(zip_path: Path, files: dict[str, str]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover failed SkillHub downloads by synthesizing archives")
    parser.add_argument("--output-root", default="mirror")
    args = parser.parse_args()

    output_root = Path(args.output_root).expanduser().resolve()
    reports_dir = output_root / "reports"
    json_path = reports_dir / "skills_table.json"
    jsonl_path = reports_dir / "download_results.jsonl"
    rows = json.loads(json_path.read_text(encoding="utf-8"))

    recovered = 0
    for row in rows:
        if row.get("download_status") not in {"failed", "recovered_placeholder"}:
            continue
        homepage = str(row.get("homepage") or "").strip()
        readme = ""
        if homepage:
            try:
                readme = extract_readme(fetch_html(homepage))
            except Exception:
                readme = ""

        zip_path = Path(str(row.get("local_zip_path", ""))).expanduser().resolve()
        meta = {
            "slug": row.get("slug", ""),
            "version": row.get("version", ""),
            "ownerName": row.get("ownerName", ""),
            "homepage": homepage,
            "recoveredAt": int(time.time() * 1000),
        }
        if readme:
            files = {
                "SKILL.md": readme,
                "_meta.json": json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                "RECOVERED_FROM.md": f"Recovered from ClawHub homepage: {homepage}\n",
            }
            status = "recovered_readme"
            source = "homepage-readme"
        else:
            files = {
                "SKILL.md": placeholder_skill_markdown(row),
                "_meta.json": json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
                "RECOVERED_FROM.md": f"Synthesized from public metadata; upstream archive unavailable. Homepage: {homepage}\n",
            }
            status = "recovered_placeholder"
            source = "metadata-placeholder"

        write_zip(zip_path, files)
        row["download_status"] = status
        row["download_source"] = source
        row["download_final_url"] = homepage
        row["zip_size_bytes"] = zip_path.stat().st_size
        row["zip_sha256"] = sha256_file(zip_path)
        row["error"] = ""
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        recovered += 1

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(reports_dir / "skills_table.csv", rows)
    write_summary(reports_dir / "skills_summary.md", rows, time.time())
    print(f"recovered={recovered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
