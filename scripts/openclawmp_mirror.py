#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
import tarfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


DEFAULT_BASE_URL = "https://openclawmp.stepfun.com"
CONNECT_SERVICE = "step.seafood.catalog.CatalogService"
USER_AGENT = "openclawmp-mirror/0.1"
REQUEST_TIMEOUT = 60
TEXT_EXTENSIONS = {
    ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".js", ".ts", ".py", ".sh", ".html", ".css", ".svg", ".xml", ".ini", ".env", ".gitignore", ".npmignore"
}


def should_fetch_missing_file(path_value: str) -> bool:
    lower = path_value.lower()
    name = lower.rsplit('/', 1)[-1]
    if name in {"skill.md", "readme.md", "package.json", "claude.md"}:
        return True
    for ext in TEXT_EXTENSIONS:
        if lower.endswith(ext):
            return True
    return False


CATALOG_COLUMNS = [
    "id",
    "name",
    "displayName",
    "type",
    "description",
    "tags_json",
    "installs",
    "rating",
    "author",
    "authorId",
    "authorReputation",
    "version",
    "updatedAt",
    "category",
    "githubStars",
    "totalStars",
    "installCommand",
    "asset_url",
    "readme_url",
    "download_url",
    "local_zip_path",
    "zip_size_bytes",
    "zip_sha256",
    "files_count",
    "download_status",
    "download_source",
    "error",
]


class Progress:
    def __init__(self, total: int) -> None:
        self.total = total
        self.completed = 0
        self.lock = threading.Lock()
        self.counts: Dict[str, int] = {}
        self.started_at = time.time()

    def update(self, status: str) -> None:
        with self.lock:
            self.completed += 1
            self.counts[status] = self.counts.get(status, 0) + 1
            if self.completed % 50 == 0 or self.completed == self.total:
                elapsed = max(1, int(time.time() - self.started_at))
                rate = self.completed / elapsed
                counts_str = "  ".join(f"{key}={value}" for key, value in sorted(self.counts.items()))
                print(f"progress {self.completed}/{self.total}  {counts_str}  rate={rate:.2f}/s", flush=True)


def http_request(url: str, accept: str = "application/json") -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
        },
    )


def connect_request(url: str, payload: Dict[str, Any]) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Connect-Protocol-Version": "1",
        },
    )


def http_get_json(url: str) -> Any:
    with urllib.request.urlopen(http_request(url), timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def http_post_json(url: str, payload: Dict[str, Any]) -> Any:
    with urllib.request.urlopen(connect_request(url, payload), timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def http_get_bytes(url: str, accept: str = "*/*") -> bytes:
    with urllib.request.urlopen(http_request(url, accept=accept), timeout=REQUEST_TIMEOUT) as response:
        return response.read()


def safe_name(value: str) -> str:
    out = []
    for char in value:
        if char.isalnum() or char in {"-", "_", "."}:
            out.append(char)
        else:
            out.append("-")
    return "".join(out).strip("-") or "asset"


def is_valid_zip(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        with zipfile.ZipFile(path, "r") as archive:
            return len(archive.infolist()) > 0
    except Exception:
        return False


def is_valid_tar_gz(path: Path) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    try:
        with tarfile.open(path, "r:gz") as archive:
            return bool(archive.getmembers())
    except Exception:
        return False


def is_valid_archive(path: Path) -> bool:
    return is_valid_zip(path) or is_valid_tar_gz(path)


def flatten_file_tree(nodes: List[Dict[str, Any]], prefix: str = "") -> List[Tuple[str, Dict[str, Any]]]:
    paths: List[Tuple[str, Dict[str, Any]]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        name = str(node.get("name", "")).strip()
        if not name:
            continue
        current = f"{prefix}/{name}" if prefix else name
        node_type = str(node.get("type", "")).strip().lower()
        if node_type == "directory":
            children = node.get("children")
            if isinstance(children, list):
                paths.extend(flatten_file_tree(children, current))
        else:
            paths.append((current, node))
    return paths


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in CATALOG_COLUMNS})


def write_summary(path: Path, rows: List[Dict[str, Any]], root_info: Dict[str, Any], started_at: float) -> None:
    total = len(rows)
    status_counts: Dict[str, int] = {}
    for row in rows:
        status = str(row.get("download_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    total_bytes = sum(int(row.get("zip_size_bytes") or 0) for row in rows)
    elapsed = int(time.time() - started_at)
    top_installs = sorted(rows, key=lambda row: int(row.get("installs") or 0), reverse=True)[:20]
    failures = [row for row in rows if str(row.get("download_status")) == "failed"][:50]

    lines = [
        "# OpenClawMP Skill Mirror Summary",
        "",
        f"- Generated at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}",
        f"- Platform reported total skills: {root_info.get('stats', {}).get('type_breakdown', {}).get('skill', 'unknown')}",
        f"- Mirrored skill rows: {total}",
        f"- Total archive bytes: {total_bytes}",
        f"- Elapsed seconds: {elapsed}",
        f"- Status counts: {json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}",
        "",
        "## Top 20 by installs",
        "",
        "| id | name | version | installs | stars | status | size_bytes |",
        "| --- | --- | --- | ---: | ---: | --- | ---: |",
    ]
    for row in top_installs:
        lines.append(
            f"| {row.get('id','')} | {row.get('name','')} | {row.get('version','')} | {row.get('installs',0)} | "
            f"{row.get('totalStars',0)} | {row.get('download_status','')} | {row.get('zip_size_bytes',0)} |"
        )
    lines.extend(["", "## First 50 failures", "", "| id | name | error |", "| --- | --- | --- |"])
    if failures:
        for row in failures:
            error = str(row.get("error", "")).replace("|", "/")
            lines.append(f"| {row.get('id','')} | {row.get('name','')} | {error} |")
    else:
        lines.append("| - | - | none |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_base_url(value: str) -> str:
    return str(value or DEFAULT_BASE_URL).strip().rstrip("/")


def connect_url(base_url: str, method: str) -> str:
    return f"{normalize_base_url(base_url)}/api/{CONNECT_SERVICE}/{method}"


ASSET_TYPE_TO_CONNECT = {
    "experience": 1,
    "skill": 2,
    "plugin": 3,
    "trigger": 4,
    "channel": 5,
}

CONNECT_TO_ASSET_TYPE = {value: key for key, value in ASSET_TYPE_TO_CONNECT.items()}


def tag_name(tag: Any) -> str:
    if isinstance(tag, str):
        return tag.strip()
    if isinstance(tag, dict):
        return str(tag.get("displayName") or tag.get("name") or tag.get("tagId") or "").strip()
    return ""


def to_int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def normalize_connect_item(item: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    asset_id = str(item.get("assetId") or item.get("id") or "").strip()
    asset_type_value = item.get("assetType")
    local_type = CONNECT_TO_ASSET_TYPE.get(to_int(asset_type_value), str(asset_type_value or ""))
    author = item.get("author") if isinstance(item.get("author"), dict) else {}
    version = str(item.get("latestSemver") or item.get("version") or "").strip() or "unknown"
    tags = [name for name in (tag_name(tag) for tag in item.get("tags") or []) if name]
    base = normalize_base_url(base_url)

    return {
        "id": asset_id,
        "name": str(item.get("name") or "").strip(),
        "displayName": str(item.get("displayName") or item.get("name") or "").strip(),
        "type": local_type,
        "description": str(item.get("description") or item.get("longDescription") or "").strip(),
        "tags": tags,
        "installs": to_int(item.get("downloadCount") or item.get("installCount") or item.get("installs")),
        "rating": to_int(item.get("rating")),
        "author": str(author.get("displayName") or author.get("name") or item.get("ownerUserId") or "").strip(),
        "authorId": str(author.get("userId") or author.get("id") or item.get("ownerUserId") or "").strip(),
        "authorAvatar": str(author.get("avatarUrl") or author.get("avatar") or "").strip(),
        "authorReputation": to_int(author.get("reputation")),
        "version": version,
        "updatedAt": str(item.get("updatedAt") or item.get("createdAt") or "").strip(),
        "category": str(item.get("category") or "").strip(),
        "githubStars": 0,
        "totalStars": to_int(item.get("totalStars") or item.get("stars")),
        "installCommand": f"openclawmp install {local_type}/{asset_id}" if local_type and asset_id else "",
        "asset_url": f"{base}/explore/{asset_id}" if asset_id else base,
        "readme_url": f"{base}/explore/{asset_id}" if asset_id else base,
        "download_url": "",
        "_connect_asset_id": asset_id,
    }


def fetch_catalog(base_url: str, asset_type: str, limit: int, output_root: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    root_info: Dict[str, Any] = {
        "source": "connect",
        "base_url": normalize_base_url(base_url),
        "stats": {"type_breakdown": {asset_type: "unknown"}},
    }
    pages_dir = output_root / "catalog" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    items: List[Dict[str, Any]] = []
    page_num = 1
    cursor: str | None = None
    seen_ids = set()

    while True:
        payload = http_post_json(
            connect_url(base_url, "SearchAssets"),
            {"query": "", "pageSize": limit, "pageToken": cursor or ""},
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"unexpected assets payload on page {page_num}: {payload}")
        write_json(pages_dir / f"page-{page_num:04d}.json", payload)
        page_items = payload.get("items")
        if not isinstance(page_items, list):
            raise RuntimeError(f"missing items list on page {page_num}")
        for item in page_items:
            if not isinstance(item, dict):
                continue
            normalized = normalize_connect_item(item, base_url)
            if normalized.get("type") != asset_type:
                continue
            asset_id = str(normalized.get("id", "")).strip()
            if not asset_id or asset_id in seen_ids:
                continue
            seen_ids.add(asset_id)
            items.append(normalized)
        cursor = str(payload.get("nextPageToken") or payload.get("nextCursor") or "").strip() or None
        if page_num % 10 == 0 or cursor is None:
            print(f"catalog page {page_num}  items={len(items)}", flush=True)
        if cursor is None:
            break
        page_num += 1

    root_info["stats"] = {"type_breakdown": {asset_type: len(items)}}
    write_json(
        output_root / "catalog" / "skills_catalog.json",
        {
            "root": root_info,
            "asset_type": asset_type,
            "page_limit": limit,
            "total_items": len(items),
            "items": items,
        },
    )
    return root_info, items


def build_row(item: Dict[str, Any], output_root: Path) -> Dict[str, Any]:
    asset_id = str(item.get("id", "")).strip()
    name = str(item.get("name", "")).strip()
    version = str(item.get("version", "")).strip() or "unknown"
    zip_path = output_root / "zips" / asset_id / f"{safe_name(name)}-{safe_name(version)}.tgz"
    tags = item.get("tags")
    return {
        **item,
        "tags_json": json.dumps(tags, ensure_ascii=False) if tags is not None else "",
        "asset_url": item.get("asset_url") or "",
        "readme_url": item.get("readme_url") or "",
        "download_url": item.get("download_url") or "",
        "local_zip_path": str(zip_path),
        "zip_size_bytes": 0,
        "zip_sha256": "",
        "files_count": 0,
        "download_status": "pending",
        "download_source": "",
        "error": "",
    }


def stream_download(url: str, destination: Path) -> Tuple[int, str, int, str]:
    request = http_request(url, accept="application/zip,application/octet-stream,*/*")
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        return int(getattr(response, "status", 200) or 200), response.geturl(), total, digest.hexdigest()


def get_connect_download_url(asset_id: str, base_url: str) -> str:
    payload = http_post_json(connect_url(base_url, "GetReversionDownloadUrl"), {"assetId": asset_id})
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected download url payload for {asset_id}: {payload}")
    download_url = str(payload.get("downloadUrl") or "").strip()
    if not download_url:
        raise RuntimeError(f"missing downloadUrl for {asset_id}")
    return download_url


def download_via_files_api(asset_id: str, version: str, destination: Path, base_url: str) -> Tuple[int, str, int, str, int]:
    detail = http_post_json(connect_url(base_url, "GetAsset"), {"assetId": asset_id})
    if not isinstance(detail, dict):
        raise RuntimeError(f"unexpected detail payload for {asset_id}")

    files_tree = detail.get("files")
    file_nodes = flatten_file_tree(files_tree) if isinstance(files_tree, list) else []
    readme = detail.get("readme")
    interesting_files = {}
    for file_path, node in file_nodes:
        content = node.get("content")
        if not isinstance(content, str):
            continue
        lower = file_path.lower()
        if lower.endswith(("skill.md", "readme.md", "package.json", "claude.md", ".gitignore")):
            interesting_files[file_path] = content

    metadata = {
        "id": detail.get("id", asset_id),
        "name": detail.get("name", ""),
        "displayName": detail.get("displayName", ""),
        "type": detail.get("type", ""),
        "version": detail.get("version", version),
        "author": detail.get("author", ""),
        "authorId": detail.get("authorId", ""),
        "updatedAt": detail.get("updatedAt", ""),
        "category": detail.get("category", ""),
        "installs": detail.get("installs", 0),
        "totalStars": detail.get("totalStars", 0),
        "tags": detail.get("tags", []),
        "description": detail.get("description", ""),
        "dependencies": detail.get("dependencies", []),
        "recoveredFrom": "asset-detail",
        "originalFilesCount": len(file_nodes),
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        if isinstance(readme, str) and readme.strip() and "README.md" not in interesting_files:
            archive.writestr("README.md", readme.encode("utf-8"))
        elif "README.md" in interesting_files:
            pass
        else:
            archive.writestr(
                "README.md",
                (
                    f"# {detail.get('displayName') or detail.get('name') or asset_id}\n\n"
                    "This package was reconstructed from openclawmp asset metadata because the upstream download did not provide a valid zip.\n"
                ).encode("utf-8"),
            )
        for file_path, content in interesting_files.items():
            archive.writestr(file_path, content.encode("utf-8"))
        archive.writestr("_asset.json", json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"))

    if not is_valid_zip(destination):
        raise RuntimeError(f"reconstructed zip is empty for {asset_id}")
    included_count = 1 + len(interesting_files) + 1
    return 200, f"asset-detail:{asset_id}", destination.stat().st_size, sha256_file(destination), included_count


def attempt_download(row: Dict[str, Any], base_url: str) -> Dict[str, Any]:
    destination = Path(str(row["local_zip_path"]))
    if is_valid_archive(destination):
        return {
            "zip_size_bytes": destination.stat().st_size,
            "zip_sha256": sha256_file(destination),
            "download_status": "existing",
            "download_source": "existing",
            "files_count": 0,
            "error": "",
        }

    asset_id = str(row["id"])
    version = str(row.get("version", "")).strip()
    temp_path = destination.with_suffix(destination.suffix + f".part-{threading.get_ident()}")
    if temp_path.exists():
        temp_path.unlink()

    try:
        download_url = str(row.get("download_url") or "").strip() or get_connect_download_url(asset_id, base_url)
        _, _, size_bytes, sha256_value = stream_download(download_url, temp_path)
        if not is_valid_archive(temp_path):
            raise RuntimeError("downloaded file is not a valid archive")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path.replace(destination)
        return {
            "zip_size_bytes": size_bytes,
            "zip_sha256": sha256_value,
            "download_status": "downloaded",
            "download_source": "connect-download",
            "files_count": 0,
            "error": "",
        }
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        try:
            if temp_path.exists():
                temp_path.unlink()
            _, _, size_bytes, sha256_value, files_count = download_via_files_api(asset_id, version, temp_path, base_url)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp_path.replace(destination)
            return {
                "zip_size_bytes": size_bytes,
                "zip_sha256": sha256_value,
                "download_status": "recovered_files",
                "download_source": "files-api",
                "files_count": files_count,
                "error": f"connect-download failed: {exc}",
            }
        except Exception as fallback_exc:
            if temp_path.exists():
                temp_path.unlink()
            return {
                "zip_size_bytes": 0,
                "zip_sha256": "",
                "download_status": "failed",
                "download_source": "",
                "files_count": 0,
                "error": f"connect-download failed: {exc}; files-api failed: {fallback_exc}",
            }


def mirror(output_root: Path, base_url: str, asset_type: str, page_limit: int, download_concurrency: int, limit: int) -> None:
    started_at = time.time()
    root_info, items = fetch_catalog(base_url=base_url, asset_type=asset_type, limit=page_limit, output_root=output_root)
    if limit > 0:
        items = items[:limit]
    rows = [build_row(item, output_root) for item in items]
    progress = Progress(len(rows))

    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = reports_dir / "download_results.jsonl"
    jsonl_lock = threading.Lock()

    def worker(index: int, row: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        result = dict(row)
        result.update(attempt_download(row, base_url))
        with jsonl_lock:
            with jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        progress.update(str(result.get("download_status", "unknown")))
        return index, result

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, download_concurrency)) as executor:
        futures = [executor.submit(worker, index, row) for index, row in enumerate(rows)]
        for future in concurrent.futures.as_completed(futures):
            index, result = future.result()
            rows[index] = result

    write_json(reports_dir / "skills_table.json", rows)
    write_csv(reports_dir / "skills_table.csv", rows)
    write_summary(reports_dir / "skills_summary.md", rows, root_info, started_at)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirror openclawmp skills into local zip archives")
    parser.add_argument("--output-root", default="openclawmp_mirror")
    parser.add_argument("--base-url", default=os.environ.get("OPENCLAWMP_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--type", default="skill")
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--download-concurrency", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    mirror(
        output_root=Path(args.output_root).expanduser().resolve(),
        base_url=normalize_base_url(args.base_url),
        asset_type=args.type,
        page_limit=args.page_limit,
        download_concurrency=args.download_concurrency,
        limit=args.limit,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
