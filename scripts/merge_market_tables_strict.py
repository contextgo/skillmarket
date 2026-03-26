#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


SKILLHUB_CSV = Path("mirror/reports/skills_table.csv")
OPENCLAWMP_CSV = Path("openclawmp_mirror/reports/skills_table.csv")
OUTPUT_DIR = Path("comparison")


def normalize(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def to_int(value: str) -> int:
    try:
        return int(float(value or 0))
    except Exception:
        return 0


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def choose_best_skillhub(rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        rows,
        key=lambda row: (
            to_int(row.get("downloads", "0")),
            to_int(row.get("installs", "0")),
            to_int(row.get("stars", "0")),
            row.get("slug", ""),
        ),
    )


def choose_best_openclawmp(rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        rows,
        key=lambda row: (
            to_int(row.get("installs", "0")),
            to_int(row.get("totalStars", "0")),
            to_int(row.get("githubStars", "0")),
            row.get("id", ""),
        ),
    )


def main() -> int:
    skillhub_rows = load_csv(SKILLHUB_CSV)
    openclawmp_rows = load_csv(OPENCLAWMP_CSV)

    skillhub_groups: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in skillhub_rows:
        key = (
            normalize(row.get("name", "")),
            normalize(row.get("version", "")),
            normalize(row.get("ownerName", "")),
        )
        if all(key):
            skillhub_groups[key].append(row)

    openclawmp_groups: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in openclawmp_rows:
        key = (
            normalize(row.get("name", "")),
            normalize(row.get("version", "")),
            normalize(row.get("author", "")),
        )
        if all(key):
            openclawmp_groups[key].append(row)

    overlap_keys = sorted(set(skillhub_groups) & set(openclawmp_groups))

    all_rows: List[Dict[str, str]] = []
    best_rows: List[Dict[str, str]] = []
    for key in overlap_keys:
        skillhub_group = skillhub_groups[key]
        openclawmp_group = openclawmp_groups[key]
        best_skillhub = choose_best_skillhub(skillhub_group)
        best_openclawmp = choose_best_openclawmp(openclawmp_group)

        best_rows.append(
            {
                "normalized_name": key[0],
                "normalized_version": key[1],
                "normalized_author": key[2],
                "skillhub_candidates": str(len(skillhub_group)),
                "openclawmp_candidates": str(len(openclawmp_group)),
                "skillhub_slug": best_skillhub.get("slug", ""),
                "skillhub_name": best_skillhub.get("name", ""),
                "skillhub_version": best_skillhub.get("version", ""),
                "skillhub_owner": best_skillhub.get("ownerName", ""),
                "skillhub_homepage": best_skillhub.get("homepage", ""),
                "skillhub_downloads": best_skillhub.get("downloads", ""),
                "skillhub_installs": best_skillhub.get("installs", ""),
                "skillhub_stars": best_skillhub.get("stars", ""),
                "openclawmp_id": best_openclawmp.get("id", ""),
                "openclawmp_name": best_openclawmp.get("name", ""),
                "openclawmp_display_name": best_openclawmp.get("displayName", ""),
                "openclawmp_version": best_openclawmp.get("version", ""),
                "openclawmp_author": best_openclawmp.get("author", ""),
                "openclawmp_asset_url": best_openclawmp.get("asset_url", ""),
                "openclawmp_installs": best_openclawmp.get("installs", ""),
                "openclawmp_total_stars": best_openclawmp.get("totalStars", ""),
                "openclawmp_github_stars": best_openclawmp.get("githubStars", ""),
            }
        )

        for s_row in skillhub_group:
            for o_row in openclawmp_group:
                all_rows.append(
                    {
                        "normalized_name": key[0],
                        "normalized_version": key[1],
                        "normalized_author": key[2],
                        "skillhub_slug": s_row.get("slug", ""),
                        "skillhub_name": s_row.get("name", ""),
                        "skillhub_version": s_row.get("version", ""),
                        "skillhub_owner": s_row.get("ownerName", ""),
                        "skillhub_homepage": s_row.get("homepage", ""),
                        "skillhub_downloads": s_row.get("downloads", ""),
                        "skillhub_installs": s_row.get("installs", ""),
                        "skillhub_stars": s_row.get("stars", ""),
                        "openclawmp_id": o_row.get("id", ""),
                        "openclawmp_name": o_row.get("name", ""),
                        "openclawmp_display_name": o_row.get("displayName", ""),
                        "openclawmp_version": o_row.get("version", ""),
                        "openclawmp_author": o_row.get("author", ""),
                        "openclawmp_asset_url": o_row.get("asset_url", ""),
                        "openclawmp_installs": o_row.get("installs", ""),
                        "openclawmp_total_stars": o_row.get("totalStars", ""),
                        "openclawmp_github_stars": o_row.get("githubStars", ""),
                    }
                )

    write_csv(
        OUTPUT_DIR / "merged_strict_name_version_author_all.csv",
        [
            "normalized_name",
            "normalized_version",
            "normalized_author",
            "skillhub_slug",
            "skillhub_name",
            "skillhub_version",
            "skillhub_owner",
            "skillhub_homepage",
            "skillhub_downloads",
            "skillhub_installs",
            "skillhub_stars",
            "openclawmp_id",
            "openclawmp_name",
            "openclawmp_display_name",
            "openclawmp_version",
            "openclawmp_author",
            "openclawmp_asset_url",
            "openclawmp_installs",
            "openclawmp_total_stars",
            "openclawmp_github_stars",
        ],
        all_rows,
    )

    write_csv(
        OUTPUT_DIR / "merged_strict_name_version_author_best.csv",
        [
            "normalized_name",
            "normalized_version",
            "normalized_author",
            "skillhub_candidates",
            "openclawmp_candidates",
            "skillhub_slug",
            "skillhub_name",
            "skillhub_version",
            "skillhub_owner",
            "skillhub_homepage",
            "skillhub_downloads",
            "skillhub_installs",
            "skillhub_stars",
            "openclawmp_id",
            "openclawmp_name",
            "openclawmp_display_name",
            "openclawmp_version",
            "openclawmp_author",
            "openclawmp_asset_url",
            "openclawmp_installs",
            "openclawmp_total_stars",
            "openclawmp_github_stars",
        ],
        best_rows,
    )

    summary = {
        "strict_overlap_groups": len(overlap_keys),
        "strict_overlap_pairs": len(all_rows),
        "skillhub_metric_fields": ["downloads", "installs", "stars"],
        "openclawmp_metric_fields": ["installs", "totalStars", "githubStars", "rating"],
        "note": "Strict merge uses exact normalized name + version + author. openclawmp has no public homepage field, so homepage remains a SkillHub-side reference only.",
        "best_csv": str(OUTPUT_DIR / "merged_strict_name_version_author_best.csv"),
        "all_csv": str(OUTPUT_DIR / "merged_strict_name_version_author_all.csv"),
    }
    (OUTPUT_DIR / "merged_strict_name_version_author_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "merged_strict_name_version_author_summary.md").write_text(
        "\n".join(
            [
                "# Strict Merge Summary",
                "",
                f"- Strict overlap groups: {len(overlap_keys)}",
                f"- Strict overlap pairs: {len(all_rows)}",
                "- Strict key: `name + version + author` (normalized exact match)",
                "- `homepage` 仅作为 SkillHub 侧参考字段保留；openclawmp 无公开 homepage 字段。",
                "",
                "## Public Metrics",
                "",
                "- SkillHub: `downloads`, `installs`, `stars`",
                "- openclawmp: `installs`, `totalStars`, `githubStars`, `rating`",
                "",
                "## Outputs",
                "",
                "- `comparison/merged_strict_name_version_author_best.csv`",
                "- `comparison/merged_strict_name_version_author_all.csv`",
                "- `comparison/merged_strict_name_version_author_summary.json`",
            ]
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
