#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
SECRETS_ENV = ROOT / '.secrets' / 'aliyun-oss.env'
MANIFEST_KEY = '.deploy-manifest.json'


@dataclass
class UploadItem:
    local_path: Optional[Path]
    oss_key: str
    content_type: str
    cache_control: str
    data: Optional[bytes] = None


class OSSClient:
    def __init__(self, bucket: str, endpoint: str, access_key_id: str, access_key_secret: str) -> None:
        self.bucket = bucket
        self.endpoint = endpoint.replace('https://', '').replace('http://', '').strip('/')
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret

    def _date(self) -> str:
        return datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

    def _resource(self, key: str = '') -> str:
        clean = key.lstrip('/')
        return f'/{self.bucket}/' + clean

    def _url(self, key: str = '') -> str:
        clean = quote(key.lstrip('/'), safe='/~')
        if clean:
            return f'https://{self.bucket}.{self.endpoint}/{clean}'
        return f'https://{self.bucket}.{self.endpoint}/'

    def _auth_header(self, method: str, date: str, resource: str, content_type: str = '', x_oss_headers: Optional[Dict[str, str]] = None) -> str:
        canon_headers = ''
        if x_oss_headers:
            for name, value in sorted((k.lower().strip(), str(v).strip()) for k, v in x_oss_headers.items()):
                canon_headers += f'{name}:{value}\n'
        string_to_sign = f'{method}\n\n{content_type}\n{date}\n{canon_headers}{resource}'
        signature = base64.b64encode(
            hmac.new(self.access_key_secret.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()
        return f'OSS {self.access_key_id}:{signature}'

    def request(self, method: str, key: str = '', data: Optional[bytes] = None, content_type: str = '', headers: Optional[Dict[str, str]] = None) -> bytes:
        date = self._date()
        resource = self._resource(key)
        headers = dict(headers or {})
        auth = self._auth_header(method, date, resource, content_type=content_type)
        request = Request(self._url(key), method=method, data=data)
        request.add_header('Date', date)
        request.add_header('Authorization', auth)
        if content_type:
            request.add_header('Content-Type', content_type)
        for name, value in headers.items():
            request.add_header(name, value)
        with urlopen(request, timeout=60) as response:
            return response.read()

    def get_json(self, key: str) -> Optional[dict]:
        try:
            data = self.request('GET', key)
        except HTTPError as exc:
            if exc.code == 404:
                return None
            raise
        return json.loads(data.decode('utf-8'))

    def put_bytes(self, key: str, data: bytes, content_type: str, cache_control: str) -> None:
        self.request('PUT', key, data=data, content_type=content_type, headers={'Cache-Control': cache_control})


def load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    values: Dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        raw = line.strip()
        if not raw or raw.startswith('#') or '=' not in raw:
            continue
        key, value = raw.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def load_config() -> Dict[str, str]:
    file_values = load_env_file(SECRETS_ENV)
    return {
        'bucket': os.environ.get('OSS_BUCKET') or file_values.get('OSS_BUCKET', ''),
        'endpoint': os.environ.get('OSS_ENDPOINT') or file_values.get('OSS_ENDPOINT', ''),
        'access_key_id': os.environ.get('OSS_ACCESS_KEY_ID') or file_values.get('OSS_ACCESS_KEY_ID', ''),
        'access_key_secret': os.environ.get('OSS_ACCESS_KEY_SECRET') or file_values.get('OSS_ACCESS_KEY_SECRET', ''),
        'site_url': os.environ.get('SITE_URL', 'https://skillmarket.com.cn').rstrip('/'),
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def guess_type(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    return mime or 'application/octet-stream'


def iter_files(base: Path) -> Iterable[Path]:
    for path in sorted(base.rglob('*')):
        if path.is_file():
            yield path


def production_config(site_url: str) -> bytes:
    payload = {
        'brandName': 'ContextGo',
        'siteUrl': site_url,
        'manifestUrl': './data/skills.json',
        'statsUrl': './data/stats.json',
        'packageBaseUrls': {
            'skillhub': './packages/skillhub/',
            'openclawmp': './packages/openclawmp/',
        },
        'featuredCount': 8,
        'pageSize': 24,
    }
    lines = [
        'window.SKILL_MARKET_CONFIG = ' + json.dumps(payload, ensure_ascii=False, indent=2) + ';',
        '',
    ]
    return '\n'.join(lines).encode('utf-8')


def build_upload_items(site_url: str, include_site: bool, include_packages: bool) -> List[UploadItem]:
    items: List[UploadItem] = []
    if include_site:
        items.append(UploadItem(ROOT / 'market' / 'index.html', 'index.html', 'text/html; charset=utf-8', 'public,max-age=300'))
        items.append(UploadItem(None, 'config.js', 'application/javascript; charset=utf-8', 'public,max-age=300', data=production_config(site_url)))
        for path in iter_files(ROOT / 'market' / 'assets'):
            rel = path.relative_to(ROOT / 'market')
            items.append(UploadItem(path, rel.as_posix(), guess_type(path.name), 'public,max-age=300'))
        for path in iter_files(ROOT / 'market' / 'data'):
            rel = path.relative_to(ROOT / 'market')
            items.append(UploadItem(path, rel.as_posix(), guess_type(path.name), 'public,max-age=300'))
    if include_packages:
        for path in iter_files(ROOT / 'mirror' / 'zips'):
            rel = path.relative_to(ROOT / 'mirror' / 'zips')
            items.append(UploadItem(path, f'packages/skillhub/{rel.as_posix()}', 'application/zip', 'public,max-age=31536000,immutable'))
        for path in iter_files(ROOT / 'openclawmp_mirror' / 'zips'):
            rel = path.relative_to(ROOT / 'openclawmp_mirror' / 'zips')
            items.append(UploadItem(path, f'packages/openclawmp/{rel.as_posix()}', 'application/zip', 'public,max-age=31536000,immutable'))
    return items


def read_item_bytes(item: UploadItem) -> bytes:
    if item.data is not None:
        return item.data
    assert item.local_path is not None
    return item.local_path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description='Deploy static market and package archives to Aliyun OSS')
    parser.add_argument('--site-url', default=None)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--site-only', action='store_true')
    parser.add_argument('--packages-only', action='store_true')
    args = parser.parse_args()

    config = load_config()
    site_url = (args.site_url or config['site_url']).rstrip('/')
    if not all([config['bucket'], config['endpoint'], config['access_key_id'], config['access_key_secret']]):
        print('Missing OSS configuration. Set OSS_BUCKET / OSS_ENDPOINT / OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET.', file=sys.stderr)
        return 1

    include_site = not args.packages_only
    include_packages = not args.site_only
    client = OSSClient(config['bucket'], config['endpoint'], config['access_key_id'], config['access_key_secret'])

    remote_manifest = client.get_json(MANIFEST_KEY) or {'files': {}}
    remote_files: Dict[str, Dict[str, str]] = remote_manifest.get('files', {}) if isinstance(remote_manifest, dict) else {}

    upload_items = build_upload_items(site_url, include_site=include_site, include_packages=include_packages)
    manifest_files: Dict[str, Dict[str, str]] = {}
    changed: List[UploadItem] = []

    for item in upload_items:
        data = read_item_bytes(item)
        sha = sha256_bytes(data)
        size = len(data)
        manifest_files[item.oss_key] = {'sha256': sha, 'size': size, 'content_type': item.content_type}
        previous = remote_files.get(item.oss_key)
        if previous and previous.get('sha256') == sha:
            continue
        changed.append(item)

    print(json.dumps({
        'bucket': config['bucket'],
        'site_url': site_url,
        'total_files': len(upload_items),
        'changed_files': len(changed),
        'site_only': include_site and not include_packages,
        'packages_only': include_packages and not include_site,
    }, ensure_ascii=False, indent=2))

    if args.dry_run:
        for item in changed[:30]:
            print(f'DRY RUN upload: {item.oss_key}')
        if len(changed) > 30:
            print(f'... and {len(changed) - 30} more')
        return 0

    for index, item in enumerate(changed, start=1):
        data = read_item_bytes(item)
        client.put_bytes(item.oss_key, data, content_type=item.content_type, cache_control=item.cache_control)
        if index % 100 == 0 or index == len(changed):
            print(f'uploaded {index}/{len(changed)}')

    deploy_manifest = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'siteUrl': site_url,
        'files': manifest_files,
    }
    client.put_bytes(MANIFEST_KEY, json.dumps(deploy_manifest, ensure_ascii=False, separators=(',', ':')).encode('utf-8'), 'application/json; charset=utf-8', 'public,max-age=60')
    print('deployment_manifest_updated=true')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
