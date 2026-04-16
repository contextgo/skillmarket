<p align="center">
  <img src="./market/assets/contextgo-readme-header.png" alt="ContextGo SkillMarket" width="100%">
</p>

<p align="center">
  <img src="./market/assets/contextgo-logo.png" alt="ContextGo Logo" width="108">
</p>

<p align="center">
  <strong>ContextGo SkillMarket</strong><br>
  Skill discovery, mirroring, curation, bundling, and distribution infrastructure for agents.
</p>

<p align="center">
  <a href="./README.md">中文</a> ·
  <a href="https://github.com/contextgo/contextgo">Main ContextGo Repo</a> ·
  <a href="https://github.com/contextgo/skillmarket">GitHub</a>
</p>

---

## What This Is

`skillmarket` is a subproject in the ContextGo product matrix focused on organizing the skill ecosystem for agents.

It is not merely a mirror-script repository, and it is not only a static site export directory. It plays a broader infrastructure role:

- mirroring skills from upstream ecosystems
- generating searchable, curated, and bundle-friendly catalogs
- serving as a distribution entry point for agent products
- providing an open skill supply layer for ContextGo and other agent systems

---

## The Problem It Solves

As agents move from demos into real project work, skill assets quickly run into a few predictable problems:

- skills are scattered across communities, repositories, and temporary links
- quality varies wildly and reuse becomes unreliable
- there is no strong layer for curation, industry indexing, or bundles
- there is no open infrastructure that can serve both products and ecosystems

`skillmarket` exists to close that loop: where skills come from, how they are filtered, and how they are distributed.

---

## Its Role Inside ContextGo

Inside ContextGo, skills are not isolated prompts. They are part of Agent Packages and workflow capability.

`skillmarket` does not run the agent itself. It owns the supply layer:

- upstream mirroring
- structured catalogs
- curated sets
- industry indexes
- bundles
- static market-site output

That is what gives ContextGo assistants, skill bundles, and later ecosystem distribution a stable source.

---

## What The Repository Provides Today

Today the repository already includes two upstream mirror paths:

- `SkillHub`
- `openclawmp`

On top of that data, it builds a usable market output flow:

- full manifests
- curated manifests
- industry indexes
- bundle data
- static site entry
- deployment pipelines

That makes it useful both as an internal supply layer and as a public open-source market infrastructure.

---

## Quick Start

### Mirror SkillHub

```bash
python3 scripts/skillhub_mirror.py --output-root mirror --page-size 100 --page-concurrency 8 --download-concurrency 12
python3 scripts/skillhub_recover_failed.py --output-root mirror
```

Outputs:

- `mirror/catalog/skills_catalog.json`
- `mirror/zips/`
- `mirror/reports/skills_table.csv`
- `mirror/reports/skills_summary.md`

### Mirror openclawmp

```bash
python3 scripts/openclawmp_mirror.py --output-root openclawmp_mirror --type skill --page-limit 100 --download-concurrency 12
```

Outputs:

- `openclawmp_mirror/catalog/skills_catalog.json`
- `openclawmp_mirror/zips/`
- `openclawmp_mirror/reports/skills_table.csv`
- `openclawmp_mirror/reports/skills_summary.md`

### Generate market data

The repository already includes a statically hostable market surface:

- page entry: `market/index.html`
- full manifest: `market/data/skills.json`
- curated manifest: `market/data/curated_skills.json`
- bundle data: `market/data/industry_index.json`, `market/data/bundles.json`
- generator: `scripts/build_market_catalog.py`

---

## Deployment And Sync

The repository already includes automated deployment and sync flows:

- workflow: `.github/workflows/deploy.yml`
- scheduled sync: `.github/workflows/sync-upstreams.yml`
- deploy script: `scripts/deploy_to_oss.py`
- deployment guide: `DEPLOYMENT.md`

The current sync pipeline runs:

- `scripts/skillhub_mirror.py`
- `scripts/skillhub_recover_failed.py`
- `scripts/openclawmp_mirror.py`
- `scripts/build_market_catalog.py`

If the catalog or site data changes, the workflow can commit and deploy the updates automatically.

---

## Why It Is Open-Sourced Separately

The skill ecosystem should not be trapped inside a single product runtime.

`skillmarket` is open-sourced as an independent project because it is fundamentally a distribution layer for agent capability:

- it can serve ContextGo
- it can serve other agent platforms or private skill systems
- it can support both open mirrors and curated operational layers

Once this layer is stable, the cost of building and reusing agents drops significantly.

---

## Relationship To ContextGo

For the full product, see:

- [ContextGo](https://github.com/contextgo/contextgo)
- [Connector](https://github.com/contextgo/connector)
- [ContextGo Releases](https://github.com/contextgo/contextgo-releases)

`skillmarket` owns the skill supply and distribution infrastructure. The user-facing workbench, Context Engine, remote access model, and end-user product experience live in the main repository.
