#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


SKILLHUB_CSV = Path("mirror/reports/skills_table.csv")
OPENCLAWMP_CSV = Path("openclawmp_mirror/reports/skills_table.csv")
OUTPUT_DIR = Path("comparison")


def normalize_name(value: str) -> str:
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


def choose_best_skillhub(rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        rows,
        key=lambda row: (
            to_int(row.get("downloads", "0")),
            to_int(row.get("installs", "0")),
            to_int(row.get("stars", "0")),
            row.get("version", ""),
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
            row.get("version", ""),
            row.get("id", ""),
        ),
    )


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    skillhub_rows = load_csv(SKILLHUB_CSV)
    openclawmp_rows = load_csv(OPENCLAWMP_CSV)

    skillhub_by_name = defaultdict(list)
    for row in skillhub_rows:
        skillhub_by_name[normalize_name(row.get("name", ""))].append(row)

    openclawmp_by_name = defaultdict(list)
    for row in openclawmp_rows:
        openclawmp_by_name[normalize_name(row.get("name", ""))].append(row)

    overlap_keys = sorted(key for key in set(skillhub_by_name) & set(openclawmp_by_name) if key)

    all_pairs: List[Dict[str, str]] = []
    best_rows: List[Dict[str, str]] = []
    for key in overlap_keys:
        skillhub_group = skillhub_by_name[key]
        openclawmp_group = openclawmp_by_name[key]

        best_skillhub = choose_best_skillhub(skillhub_group)
        best_openclawmp = choose_best_openclawmp(openclawmp_group)

        best_rows.append(
            {
                "normalized_name": key,
                "skillhub_candidates": str(len(skillhub_group)),
                "openclawmp_candidates": str(len(openclawmp_group)),
                "skillhub_slug": best_skillhub.get("slug", ""),
                "skillhub_name": best_skillhub.get("name", ""),
                "skillhub_version": best_skillhub.get("version", ""),
                "skillhub_downloads": best_skillhub.get("downloads", ""),
                "skillhub_installs": best_skillhub.get("installs", ""),
                "skillhub_stars": best_skillhub.get("stars", ""),
                "skillhub_owner": best_skillhub.get("ownerName", ""),
                "openclawmp_id": best_openclawmp.get("id", ""),
                "openclawmp_name": best_openclawmp.get("name", ""),
                "openclawmp_display_name": best_openclawmp.get("displayName", ""),
                "openclawmp_version": best_openclawmp.get("version", ""),
                "openclawmp_installs": best_openclawmp.get("installs", ""),
                "openclawmp_total_stars": best_openclawmp.get("totalStars", ""),
                "openclawmp_github_stars": best_openclawmp.get("githubStars", ""),
                "openclawmp_author": best_openclawmp.get("author", ""),
            }
        )

        for skillhub_row in skillhub_group:
            for openclawmp_row in openclawmp_group:
                all_pairs.append(
                    {
                        "normalized_name": key,
                        "skillhub_slug": skillhub_row.get("slug", ""),
                        "skillhub_name": skillhub_row.get("name", ""),
                        "skillhub_version": skillhub_row.get("version", ""),
                        "skillhub_downloads": skillhub_row.get("downloads", ""),
                        "skillhub_installs": skillhub_row.get("installs", ""),
                        "skillhub_stars": skillhub_row.get("stars", ""),
                        "skillhub_owner": skillhub_row.get("ownerName", ""),
                        "openclawmp_id": openclawmp_row.get("id", ""),
                        "openclawmp_name": openclawmp_row.get("name", ""),
                        "openclawmp_display_name": openclawmp_row.get("displayName", ""),
                        "openclawmp_version": openclawmp_row.get("version", ""),
                        "openclawmp_installs": openclawmp_row.get("installs", ""),
                        "openclawmp_total_stars": openclawmp_row.get("totalStars", ""),
                        "openclawmp_github_stars": openclawmp_row.get("githubStars", ""),
                        "openclawmp_author": openclawmp_row.get("author", ""),
                    }
                )

    write_csv(
        OUTPUT_DIR / "merged_exact_name_all.csv",
        [
            "normalized_name",
            "skillhub_slug",
            "skillhub_name",
            "skillhub_version",
            "skillhub_downloads",
            "skillhub_installs",
            "skillhub_stars",
            "skillhub_owner",
            "openclawmp_id",
            "openclawmp_name",
            "openclawmp_display_name",
            "openclawmp_version",
            "openclawmp_installs",
            "openclawmp_total_stars",
            "openclawmp_github_stars",
            "openclawmp_author",
        ],
        all_pairs,
    )

    write_csv(
        OUTPUT_DIR / "merged_exact_name_best.csv",
        [
            "normalized_name",
            "skillhub_candidates",
            "openclawmp_candidates",
            "skillhub_slug",
            "skillhub_name",
            "skillhub_version",
            "skillhub_downloads",
            "skillhub_installs",
            "skillhub_stars",
            "skillhub_owner",
            "openclawmp_id",
            "openclawmp_name",
            "openclawmp_display_name",
            "openclawmp_version",
            "openclawmp_installs",
            "openclawmp_total_stars",
            "openclawmp_github_stars",
            "openclawmp_author",
        ],
        best_rows,
    )

    summary = {
        "skillhub_rows": len(skillhub_rows),
        "openclawmp_rows": len(openclawmp_rows),
        "exact_name_overlap_groups": len(overlap_keys),
        "exact_name_overlap_pairs": len(all_pairs),
        "skillhub_available_metrics": ["downloads", "installs", "stars"],
        "openclawmp_available_metrics": ["installs", "totalStars", "githubStars", "rating"],
        "note": "openclawmp public API does not expose a dedicated download-count field; installs is the closest public adoption metric.",
        "best_csv": str(OUTPUT_DIR / "merged_exact_name_best.csv"),
        "all_pairs_csv": str(OUTPUT_DIR / "merged_exact_name_all.csv"),
    }
    (OUTPUT_DIR / "merged_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Merged Comparison Summary",
        "",
        f"- SkillHub rows: {len(skillhub_rows)}",
        f"- openclawmp rows: {len(openclawmp_rows)}",
        f"- Exact-name overlap groups: {len(overlap_keys)}",
        f"- Exact-name overlap pairs: {len(all_pairs)}",
        "",
        "## Public Metrics",
        "",
        "- SkillHub: `downloads`, `installs`, `stars`",
        "- openclawmp: `installs`, `totalStars`, `githubStars`, `rating`",
        "- openclawmp 没有公开的独立 `downloads` 字段，公开可拿到的最接近指标是 `installs`。",
        "",
        "## Outputs",
        "",
        f"- `comparison/merged_exact_name_best.csv`",
        f"- `comparison/merged_exact_name_all.csv`",
        f"- `comparison/merged_summary.json`",
    ]
    (OUTPUT_DIR / "merged_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
