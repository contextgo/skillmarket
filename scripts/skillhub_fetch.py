#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


LIST_URL = "https://lightmake.site/api/skills"
SEARCH_URL = "https://lightmake.site/api/v1/search"
DOWNLOAD_URL_TEMPLATE = "https://lightmake.site/api/v1/download?slug={slug}"
USER_AGENT = "skillhub-fetch/0.1"


def http_get_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as file_handle:
            shutil.copyfileobj(response, file_handle)


def build_list_url(
    page: int,
    page_size: int,
    sort_by: str | None,
    order: str | None,
    keyword: str | None,
) -> str:
    query: Dict[str, Any] = {
        "page": page,
        "pageSize": page_size,
    }
    if sort_by:
        query["sortBy"] = sort_by
    if order:
        query["order"] = order
    if keyword:
        query["keyword"] = keyword
    return f"{LIST_URL}?{urllib.parse.urlencode(query)}"


def fetch_list(
    page: int,
    page_size: int,
    sort_by: str | None,
    order: str | None,
    keyword: str | None,
) -> Dict[str, Any]:
    payload = http_get_json(build_list_url(page, page_size, sort_by, order, keyword))
    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise RuntimeError(f"unexpected list response: {payload}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("list response missing data object")
    return data


def fetch_search(query: str, limit: int) -> List[Dict[str, Any]]:
    url = f"{SEARCH_URL}?{urllib.parse.urlencode({'q': query, 'limit': limit})}"
    payload = http_get_json(url)
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected search response: {payload}")
    results = payload.get("results")
    if not isinstance(results, list):
        raise RuntimeError("search response missing results array")
    return [item for item in results if isinstance(item, dict)]


def print_rows(rows: Iterable[Tuple[str, ...]]) -> None:
    table = list(rows)
    if not table:
        return
    widths = [max(len(str(row[index])) for row in table) for index in range(len(table[0]))]
    for row_index, row in enumerate(table):
        formatted = "  ".join(str(cell).ljust(widths[index]) for index, cell in enumerate(row))
        print(formatted.rstrip())
        if row_index == 0:
            print("  ".join("-" * width for width in widths).rstrip())


def command_list(args: argparse.Namespace) -> int:
    data = fetch_list(
        page=args.page,
        page_size=args.page_size,
        sort_by=args.sort_by,
        order=args.order,
        keyword=args.keyword,
    )
    skills = data.get("skills", [])
    total = data.get("total", len(skills))

    if args.json_output:
        print(json.dumps({"total": total, "skills": skills}, ensure_ascii=False, indent=2))
        return 0

    print(f"total={total}  page={args.page}  page_size={args.page_size}")
    rows = [("slug", "name", "version", "downloads", "stars")]
    for skill in skills:
        rows.append(
            (
                str(skill.get("slug", "")),
                str(skill.get("name", "")),
                str(skill.get("version", "")),
                str(skill.get("downloads", "")),
                str(skill.get("stars", "")),
            )
        )
    print_rows(rows)
    return 0


def command_search(args: argparse.Namespace) -> int:
    results = fetch_search(args.query, args.limit)
    if args.json_output:
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
        return 0

    rows = [("slug", "name", "version")]
    for item in results:
        rows.append(
            (
                str(item.get("slug", "")),
                str(item.get("displayName") or item.get("name") or ""),
                str(item.get("version", "")),
            )
        )
    print_rows(rows)
    return 0


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"unsafe zip entry: {member.filename}")
        archive.extractall(destination)


def command_download(args: argparse.Namespace) -> int:
    slug = args.slug.strip()
    if not slug:
        raise RuntimeError("slug is required")

    output_dir = Path(args.output_dir).expanduser().resolve()
    zip_path = output_dir / f"{slug}.zip"
    url = DOWNLOAD_URL_TEMPLATE.format(slug=urllib.parse.quote(slug, safe=""))

    print(f"downloading {slug} -> {zip_path}")
    download_file(url, zip_path)

    if args.unzip:
        extract_dir = output_dir / slug
        extract_dir.mkdir(parents=True, exist_ok=True)
        safe_extract_zip(zip_path, extract_dir)
        print(f"extracted -> {extract_dir}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List, search, and download SkillHub skills")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List remote skills from SkillHub page API")
    list_parser.add_argument("--page", type=int, default=1)
    list_parser.add_argument("--page-size", type=int, default=24)
    list_parser.add_argument("--sort-by", default="score")
    list_parser.add_argument("--order", default="desc", choices=["asc", "desc"])
    list_parser.add_argument("--keyword")
    list_parser.add_argument("--json", dest="json_output", action="store_true")
    list_parser.set_defaults(func=command_list)

    search_parser = subparsers.add_parser("search", help="Search remote skills by keyword")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--json", dest="json_output", action="store_true")
    search_parser.set_defaults(func=command_search)

    download_parser = subparsers.add_parser("download", help="Download a skill zip by slug")
    download_parser.add_argument("slug")
    download_parser.add_argument("--output-dir", default="downloads")
    download_parser.add_argument("--unzip", action="store_true")
    download_parser.set_defaults(func=command_download)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
