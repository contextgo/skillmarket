#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


LIST_URL = "https://lightmake.site/api/skills"
API_DOWNLOAD_URL_TEMPLATE = "https://lightmake.site/api/v1/download?slug={slug}"
DIRECT_DOWNLOAD_URL_TEMPLATE = "https://skillhub-1388575217.cos.accelerate.myqcloud.com/skills/{slug}/{version}.zip"
FALLBACK_DOWNLOAD_URL_TEMPLATE = "https://skillhub-1388575217.cos.ap-guangzhou.myqcloud.com/skills/{slug}.zip"
USER_AGENT = "skillhub-mirror/0.1"
PAGE_SIZE_MAX = 100
REQUEST_TIMEOUT = 60
CATALOG_COLUMNS = [
    "slug",
    "name",
    "version",
    "ownerName",
    "category",
    "downloads",
    "stars",
    "installs",
    "score",
    "updated_at",
    "homepage",
    "description",
    "description_zh",
    "tags_json",
    "direct_download_url",
    "api_download_url",
    "fallback_download_url",
    "local_zip_path",
    "zip_size_bytes",
    "zip_sha256",
    "download_status",
    "download_source",
    "download_final_url",
    "error",
]


class Progress:
    def __init__(self, total: int) -> None:
        self.total = total
        self.completed = 0
        self.ok = 0
        self.failed = 0
        self.skipped = 0
        self.lock = threading.Lock()
        self.started_at = time.time()

    def update(self, status: str) -> None:
        with self.lock:
            self.completed += 1
            if status == "downloaded":
                self.ok += 1
            elif status == "existing":
                self.ok += 1
                self.skipped += 1
            else:
                self.failed += 1

            if self.completed % 50 == 0 or self.completed == self.total:
                elapsed = max(1, int(time.time() - self.started_at))
                rate = self.completed / elapsed
                print(
                    f"progress {self.completed}/{self.total}  ok={self.ok}  failed={self.failed}  "
                    f"existing={self.skipped}  rate={rate:.2f}/s",
                    flush=True,
                )


def json_request(url: str, timeout: int = REQUEST_TIMEOUT) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def build_list_url(page: int, page_size: int) -> str:
    query = urllib.parse.urlencode(
        {
            "page": page,
            "pageSize": page_size,
            "sortBy": "score",
            "order": "desc",
        }
    )
    return f"{LIST_URL}?{query}"


def fetch_page(page: int, page_size: int) -> Dict[str, Any]:
    payload = json_request(build_list_url(page, page_size))
    if not isinstance(payload, dict) or payload.get("code") != 0:
        raise RuntimeError(f"unexpected page payload for page={page}: {payload}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"missing data object for page={page}")
    skills = data.get("skills")
    if not isinstance(skills, list):
        raise RuntimeError(f"missing skills list for page={page}")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dedupe_skills(skills: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_slug: Dict[str, Dict[str, Any]] = {}
    for skill in skills:
        slug = str(skill.get("slug", "")).strip()
        if not slug:
            continue
        current = by_slug.get(slug)
        if current is None:
            by_slug[slug] = skill
            continue
        current_updated = int(current.get("updated_at") or 0)
        new_updated = int(skill.get("updated_at") or 0)
        if new_updated >= current_updated:
            by_slug[slug] = skill
    return sorted(by_slug.values(), key=lambda item: str(item.get("slug", "")))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_valid_zip(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        with zipfile.ZipFile(path, "r") as archive:
            archive.infolist()
        return True
    except Exception:
        return False


def build_urls(skill: Dict[str, Any]) -> List[Tuple[str, str]]:
    slug = str(skill.get("slug", "")).strip()
    version = str(skill.get("version", "")).strip()
    candidates: List[Tuple[str, str]] = []
    if slug and version:
        candidates.append(
            (
                "direct",
                DIRECT_DOWNLOAD_URL_TEMPLATE.format(
                    slug=urllib.parse.quote(slug, safe=""),
                    version=urllib.parse.quote(version, safe=""),
                ),
            )
        )
    if slug:
        candidates.append(
            (
                "api",
                API_DOWNLOAD_URL_TEMPLATE.format(slug=urllib.parse.quote(slug, safe="")),
            )
        )
        candidates.append(
            (
                "fallback",
                FALLBACK_DOWNLOAD_URL_TEMPLATE.format(slug=urllib.parse.quote(slug, safe="")),
            )
        )

    seen = set()
    unique: List[Tuple[str, str]] = []
    for source, url in candidates:
        if url in seen:
            continue
        seen.add(url)
        unique.append((source, url))
    return unique


def local_zip_path(base_dir: Path, skill: Dict[str, Any]) -> Path:
    slug = str(skill.get("slug", "")).strip()
    version = str(skill.get("version", "")).strip() or "unknown"
    return base_dir / "zips" / slug / f"{version}.zip"


def stream_download(url: str, destination: Path) -> Tuple[int, str, int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/zip,application/octet-stream,*/*",
        },
    )
    sha = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                sha.update(chunk)
                total += len(chunk)
        status = int(getattr(response, "status", 200) or 200)
        final_url = response.geturl()
    return status, final_url, total, sha.hexdigest()


def attempt_download(skill: Dict[str, Any], output_root: Path, retries: int = 2) -> Dict[str, Any]:
    slug = str(skill.get("slug", "")).strip()
    zip_path = local_zip_path(output_root, skill)

    if is_valid_zip(zip_path):
        return {
            "download_status": "existing",
            "download_source": "existing",
            "download_final_url": "",
            "local_zip_path": str(zip_path),
            "zip_size_bytes": zip_path.stat().st_size,
            "zip_sha256": sha256_file(zip_path),
            "error": "",
        }

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    for source, url in build_urls(skill):
        last_error = ""
        for attempt in range(1, retries + 1):
            temp_path = zip_path.with_suffix(zip_path.suffix + f".part-{os.getpid()}-{threading.get_ident()}")
            if temp_path.exists():
                temp_path.unlink()
            try:
                status, final_url, size_bytes, sha256_value = stream_download(url, temp_path)
                if not is_valid_zip(temp_path):
                    raise RuntimeError(f"invalid zip archive from {url}")
                zip_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.replace(zip_path)
                return {
                    "download_status": "downloaded",
                    "download_source": source,
                    "download_final_url": final_url,
                    "local_zip_path": str(zip_path),
                    "zip_size_bytes": size_bytes,
                    "zip_sha256": sha256_value,
                    "error": "",
                    "http_status": status,
                }
            except Exception as exc:
                last_error = f"{source} attempt {attempt}: {exc}"
                if temp_path.exists():
                    temp_path.unlink()
                time.sleep(min(attempt, 3))
        if last_error:
            final_error = last_error
        else:
            final_error = f"{source}: unknown error"
    return {
        "download_status": "failed",
        "download_source": "",
        "download_final_url": "",
        "local_zip_path": str(zip_path),
        "zip_size_bytes": 0,
        "zip_sha256": "",
        "error": final_error,
    }


def enrich_row(skill: Dict[str, Any], output_root: Path) -> Dict[str, Any]:
    row = dict(skill)
    tags = row.get("tags")
    row["tags_json"] = json.dumps(tags, ensure_ascii=False) if tags is not None else ""
    row["direct_download_url"] = ""
    row["api_download_url"] = ""
    row["fallback_download_url"] = ""
    for source, url in build_urls(skill):
        if source == "direct":
            row["direct_download_url"] = url
        elif source == "api":
            row["api_download_url"] = url
        elif source == "fallback":
            row["fallback_download_url"] = url
    row["local_zip_path"] = str(local_zip_path(output_root, skill))
    row["zip_size_bytes"] = 0
    row["zip_sha256"] = ""
    row["download_status"] = "pending"
    row["download_source"] = ""
    row["download_final_url"] = ""
    row["error"] = ""
    return row


def fetch_catalog(output_root: Path, page_size: int, page_concurrency: int) -> List[Dict[str, Any]]:
    if page_size > PAGE_SIZE_MAX:
        raise RuntimeError(f"page_size must be <= {PAGE_SIZE_MAX}")

    first_page = fetch_page(1, page_size)
    total = int(first_page.get("total") or 0)
    total_pages = max(1, (total + page_size - 1) // page_size)

    pages_dir = output_root / "catalog" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    write_json(pages_dir / "page-0001.json", first_page)

    page_results: Dict[int, Dict[str, Any]] = {1: first_page}
    if total_pages > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, page_concurrency)) as executor:
            future_to_page = {
                executor.submit(fetch_page, page, page_size): page
                for page in range(2, total_pages + 1)
            }
            for future in concurrent.futures.as_completed(future_to_page):
                page = future_to_page[future]
                data = future.result()
                page_results[page] = data
                write_json(pages_dir / f"page-{page:04d}.json", data)
                if page % 25 == 0 or page == total_pages:
                    print(f"catalog page {page}/{total_pages}", flush=True)

    all_skills: List[Dict[str, Any]] = []
    for page in range(1, total_pages + 1):
        skills = page_results[page].get("skills", [])
        for skill in skills:
            if isinstance(skill, dict):
                all_skills.append(skill)

    deduped = dedupe_skills(all_skills)
    write_json(
        output_root / "catalog" / "skills_catalog.json",
        {
            "total_reported": total,
            "total_pages": total_pages,
            "fetched_items": len(all_skills),
            "deduped_items": len(deduped),
            "skills": deduped,
        },
    )
    return deduped


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CATALOG_COLUMNS})


def write_summary(path: Path, rows: List[Dict[str, Any]], started_at: float) -> None:
    total = len(rows)
    ok = sum(1 for row in rows if row.get("download_status") in {"downloaded", "existing"})
    failed = sum(1 for row in rows if row.get("download_status") == "failed")
    existing = sum(1 for row in rows if row.get("download_status") == "existing")
    total_bytes = sum(int(row.get("zip_size_bytes") or 0) for row in rows)
    elapsed = int(time.time() - started_at)
    top_downloads = sorted(rows, key=lambda row: int(row.get("downloads") or 0), reverse=True)[:20]
    failed_rows = [row for row in rows if row.get("download_status") == "failed"][:50]

    lines = [
        "# SkillHub Mirror Summary",
        "",
        f"- Generated at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- Total skills in catalog: {total}",
        f"- Downloaded or already present: {ok}",
        f"- Existing local archives reused: {existing}",
        f"- Failed downloads: {failed}",
        f"- Total archive bytes: {total_bytes}",
        f"- Elapsed seconds: {elapsed}",
        "",
        "## Top 20 by downloads",
        "",
        "| slug | version | downloads | stars | status | size_bytes |",
        "| --- | --- | ---: | ---: | --- | ---: |",
    ]
    for row in top_downloads:
        lines.append(
            f"| {row.get('slug','')} | {row.get('version','')} | {row.get('downloads',0)} | {row.get('stars',0)} | "
            f"{row.get('download_status','')} | {row.get('zip_size_bytes',0)} |"
        )

    lines.extend(["", "## First 50 failures", "", "| slug | version | error |", "| --- | --- | --- |"])
    if failed_rows:
        for row in failed_rows:
            error = str(row.get("error", "")).replace("|", "/")
            lines.append(f"| {row.get('slug','')} | {row.get('version','')} | {error} |")
    else:
        lines.append("| - | - | none |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mirror(
    output_root: Path,
    page_size: int,
    page_concurrency: int,
    download_concurrency: int,
    limit: int,
) -> None:
    started_at = time.time()
    skills = fetch_catalog(output_root=output_root, page_size=page_size, page_concurrency=page_concurrency)
    if limit > 0:
        skills = skills[:limit]
    rows = [enrich_row(skill, output_root) for skill in skills]
    progress = Progress(len(rows))

    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = reports_dir / "download_results.jsonl"
    jsonl_lock = threading.Lock()

    def worker(row: Dict[str, Any]) -> Dict[str, Any]:
        result = attempt_download(row, output_root=output_root)
        merged = dict(row)
        merged.update(result)
        with jsonl_lock:
            with jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(merged, ensure_ascii=False) + "\n")
        progress.update(str(merged.get("download_status", "failed")))
        return merged

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, download_concurrency)) as executor:
        future_to_index = {executor.submit(worker, row): index for index, row in enumerate(rows)}
        for future in concurrent.futures.as_completed(future_to_index):
            index = future_to_index[future]
            rows[index] = future.result()

    write_json(reports_dir / "skills_table.json", rows)
    write_csv(reports_dir / "skills_table.csv", rows)
    write_summary(reports_dir / "skills_summary.md", rows, started_at)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirror SkillHub skills into local zip archives")
    parser.add_argument("--output-root", default="mirror")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--page-concurrency", type=int, default=8)
    parser.add_argument("--download-concurrency", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    output_root = Path(args.output_root).expanduser().resolve()
    mirror(
        output_root=output_root,
        page_size=args.page_size,
        page_concurrency=args.page_concurrency,
        download_concurrency=args.download_concurrency,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
