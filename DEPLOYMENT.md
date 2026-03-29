# Deployment

## Current status

- OSS bucket connectivity: verified
- Site files uploaded once to OSS root: verified
- GitHub Actions auto-deploy workflow: `.github/workflows/deploy.yml`
- Deploy script: `scripts/deploy_to_oss.py`

## What gets deployed

### Site files

These local files are uploaded to OSS root:

- `market/index.html` -> `index.html`
- generated production `config.js` -> `config.js`
- `market/assets/*` -> `assets/*`
- `market/data/*` -> `data/*`

### Package files

These local archives are uploaded under versioned prefixes:

- `mirror/zips/*` -> `packages/skillhub/*`
- `openclawmp_mirror/zips/*` -> `packages/openclawmp/*`

The deploy script keeps a remote manifest at `.deploy-manifest.json` and skips unchanged files on later runs.

## GitHub Secrets

Add these repository secrets in GitHub:

- `OSS_BUCKET` = `skillmarket`
- `OSS_ENDPOINT` = `https://oss-cn-beijing.aliyuncs.com`
- `OSS_ACCESS_KEY_ID` = your OSS AccessKey ID
- `OSS_ACCESS_KEY_SECRET` = your OSS AccessKey Secret
- `SITE_URL` = `https://www.skillmarket.com.cn`

## Workflow trigger

This workflow runs on:

- push to `main`
- manual trigger via `workflow_dispatch`

## Upstream sync automation

Repository now includes a separate sync workflow:

- workflow: `.github/workflows/sync-upstreams.yml`
- trigger:
  - scheduled daily at `02:20 UTC`
  - manual trigger via `workflow_dispatch`

It does the following:

- refreshes `mirror/`
- recovers missing SkillHub archives
- refreshes `openclawmp_mirror/`
- rebuilds `market/data/*`
- commits changes to `main` when upstream data changed
- directly deploys updated site and package files to OSS in the same workflow

This avoids relying on a second workflow trigger from a bot-authored push.

## Local commands

### Dry run site only

```bash
python3 scripts/deploy_to_oss.py --site-only --dry-run --site-url https://www.skillmarket.com.cn
```

### Real site deploy

```bash
python3 scripts/deploy_to_oss.py --site-only --site-url https://www.skillmarket.com.cn
```

### Full deploy

```bash
python3 scripts/deploy_to_oss.py --site-url https://www.skillmarket.com.cn
```

## Notes

- First full deploy may take a while because package archives are large.
- Later deploys are incremental because unchanged files are skipped.
- If the website should be publicly accessible without signed URLs, make sure OSS/CDN/domain routing is configured accordingly.
