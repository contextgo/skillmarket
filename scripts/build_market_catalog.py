#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

from build_curated_catalog import build_curated_outputs, enrich_items


SKILLHUB_CSV = Path('mirror/reports/skills_table.csv')
OPENCLAWMP_CSV = Path('openclawmp_mirror/reports/skills_table.csv')
OUT_JSON = Path('market/data/skills.json')
OUT_STATS = Path('market/data/stats.json')


def normalize(value: str) -> str:
    text = (value or '').strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def parse_json_array(raw: str) -> List[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    except Exception:
        pass
    return []


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
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
            to_int(row.get('downloads', '0')),
            to_int(row.get('installs', '0')),
            to_int(row.get('stars', '0')),
            row.get('slug', ''),
        ),
    )


def choose_best_openclawmp(rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        rows,
        key=lambda row: (
            to_int(row.get('installs', '0')),
            to_int(row.get('totalStars', '0')),
            to_int(row.get('githubStars', '0')),
            row.get('id', ''),
        ),
    )


def pick_description(skillhub_rows: List[Dict[str, str]], open_rows: List[Dict[str, str]]) -> str:
    candidates = []
    for row in skillhub_rows:
        for field in ('description_zh', 'description'):
            text = (row.get(field) or '').strip()
            if text:
                candidates.append(text)
    for row in open_rows:
        text = (row.get('description') or '').strip()
        if text:
            candidates.append(text)
    if not candidates:
        return ''
    return max(candidates, key=len)


def skillhub_archive_path(row: Dict[str, str]) -> str:
    zip_path = (row.get('local_zip_path') or '').strip()
    marker = '/mirror/zips/'
    if marker in zip_path:
        return zip_path.split(marker, 1)[1]
    return ''


def openclawmp_archive_path(row: Dict[str, str]) -> str:
    zip_path = (row.get('local_zip_path') or '').strip()
    marker = '/openclawmp_mirror/zips/'
    if marker in zip_path:
        return zip_path.split(marker, 1)[1]
    return ''


def main() -> int:
    skillhub_rows = load_csv(SKILLHUB_CSV)
    open_rows = load_csv(OPENCLAWMP_CSV)

    skillhub_groups: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in skillhub_rows:
        key = (
            normalize(row.get('name', '')),
            normalize(row.get('version', '')),
            normalize(row.get('ownerName', '')),
        )
        if all(key):
            skillhub_groups[key].append(row)

    open_groups: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in open_rows:
        key = (
            normalize(row.get('name', '')),
            normalize(row.get('version', '')),
            normalize(row.get('author', '')),
        )
        if all(key):
            open_groups[key].append(row)

    all_keys = sorted(set(skillhub_groups) | set(open_groups))
    items = []
    categories: Set[str] = set()
    sources_count = {'skillhub': 0, 'openclawmp': 0, 'merged': 0}

    for key in all_keys:
        skillhub_group = skillhub_groups.get(key, [])
        open_group = open_groups.get(key, [])
        best_skillhub = choose_best_skillhub(skillhub_group) if skillhub_group else None
        best_open = choose_best_openclawmp(open_group) if open_group else None

        name = ''
        display_name = ''
        version = key[1]
        author = key[2]
        description = pick_description(skillhub_group, open_group)
        tags = set()
        category_list = []
        source_list = []
        archive_variants = []
        homepage = ''
        readme_url = ''
        install_command = ''
        metrics = {
            'skillhub_downloads': 0,
            'skillhub_installs': 0,
            'skillhub_stars': 0,
            'openclawmp_installs': 0,
            'openclawmp_total_stars': 0,
            'openclawmp_github_stars': 0,
        }

        if best_skillhub:
            source_list.append('skillhub')
            name = best_skillhub.get('name', '') or name
            display_name = best_skillhub.get('name', '') or display_name
            homepage = best_skillhub.get('homepage', '') or homepage
            category = (best_skillhub.get('category') or '').strip()
            if category:
                category_list.append(category)
                categories.add(category)
            for tag in parse_json_array(best_skillhub.get('tags_json', '')):
                tags.add(tag)
            metrics['skillhub_downloads'] = to_int(best_skillhub.get('downloads', '0'))
            metrics['skillhub_installs'] = to_int(best_skillhub.get('installs', '0'))
            metrics['skillhub_stars'] = to_int(best_skillhub.get('stars', '0'))
            rel = skillhub_archive_path(best_skillhub)
            if rel:
                archive_variants.append({
                    'source': 'skillhub',
                    'relativePath': rel,
                    'label': 'SkillHub Archive',
                })

        if best_open:
            source_list.append('openclawmp')
            name = best_open.get('name', '') or name
            display_name = best_open.get('displayName', '') or best_open.get('name', '') or display_name
            readme_url = best_open.get('readme_url', '') or readme_url
            install_command = best_open.get('installCommand', '') or install_command
            category = (best_open.get('category') or '').strip()
            if category:
                category_list.append(category)
                categories.add(category)
            for tag in parse_json_array(best_open.get('tags_json', '')):
                tags.add(tag)
            metrics['openclawmp_installs'] = to_int(best_open.get('installs', '0'))
            metrics['openclawmp_total_stars'] = to_int(best_open.get('totalStars', '0'))
            metrics['openclawmp_github_stars'] = to_int(best_open.get('githubStars', '0'))
            rel = openclawmp_archive_path(best_open)
            if rel:
                archive_variants.append({
                    'source': 'openclawmp',
                    'relativePath': rel,
                    'label': 'OpenClawMP Archive',
                })
            if not homepage:
                homepage = best_open.get('asset_url', '') or homepage

        if len(source_list) == 2:
            sources_count['merged'] += 1
        elif source_list == ['skillhub']:
            sources_count['skillhub'] += 1
        elif source_list == ['openclawmp']:
            sources_count['openclawmp'] += 1

        popularity = max(
            metrics['skillhub_downloads'],
            metrics['skillhub_installs'] * 20,
            metrics['openclawmp_installs'] * 20,
            metrics['openclawmp_total_stars'] * 10,
            metrics['skillhub_stars'] * 10,
        )

        items.append({
            'id': f"{key[0]}::{key[1]}::{key[2]}",
            'name': name,
            'displayName': display_name or name,
            'version': version,
            'author': author,
            'description': description,
            'categories': sorted(set(filter(None, category_list))),
            'tags': sorted(tags),
            'sources': source_list,
            'homepage': homepage,
            'readmeUrl': readme_url,
            'installCommand': install_command,
            'archives': archive_variants,
            'metrics': metrics,
            'popularity': popularity,
        })

    items.sort(key=lambda item: (-item['popularity'], item['displayName'].lower(), item['version']))

    enriched_items = enrich_items(items)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({'items': enriched_items}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    OUT_STATS.write_text(json.dumps({
        'total': len(items),
        'categories': sorted(categories),
        'sources': sources_count,
    }, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    curated_summary = build_curated_outputs(enriched_items)
    print(json.dumps({
        'total': len(items),
        'sources': sources_count,
        'categories': len(categories),
        'curated': curated_summary,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
