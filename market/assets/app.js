const config = window.SKILL_MARKET_CONFIG || {};
const state = {
  allItems: [],
  filteredItems: [],
  visibleCount: config.pageSize || 24,
  selectedSource: 'all',
  selectedCategory: 'all',
  searchQuery: '',
  sortBy: 'popularity',
  categoriesExpanded: false,
};

const elements = {
  brandName: document.getElementById('brandName'),
  heroStats: document.getElementById('heroStats'),
  featuredStrip: document.getElementById('featuredStrip'),
  leaderboardList: document.getElementById('leaderboardList'),
  sourceChips: document.getElementById('sourceChips'),
  categoryChips: document.getElementById('categoryChips'),
  categoryToggleBtn: document.getElementById('categoryToggleBtn'),
  searchInput: document.getElementById('searchInput'),
  sortSelect: document.getElementById('sortSelect'),
  cardsGrid: document.getElementById('cardsGrid'),
  loadMoreBtn: document.getElementById('loadMoreBtn'),
  resultsHeading: document.getElementById('resultsHeading'),
  resultsMeta: document.getElementById('resultsMeta'),
  resultsPills: document.getElementById('resultsPills'),
  footerMeta: document.getElementById('footerMeta'),
  emptyState: document.getElementById('emptyState'),
  cardTemplate: document.getElementById('cardTemplate'),
  detailDrawer: document.getElementById('detailDrawer'),
  drawerBackdrop: document.getElementById('drawerBackdrop'),
  drawerClose: document.getElementById('drawerClose'),
  drawerContent: document.getElementById('drawerContent'),
};

const formatNumber = (value) => new Intl.NumberFormat('zh-CN').format(Number(value || 0));
const escapeHtml = (value = '') => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#39;');

function buildArchiveUrl(archive) {
  if (!archive) return '';
  const base = (config.packageBaseUrls && config.packageBaseUrls[archive.source]) || '';
  return `${base}${archive.relativePath}`;
}

function summarizeMetrics(item) {
  const metrics = item.metrics || {};
  return [
    metrics.skillhub_downloads ? { label: `${formatNumber(metrics.skillhub_downloads)} 下载`, alt: false } : null,
    metrics.skillhub_installs ? { label: `${formatNumber(metrics.skillhub_installs)} 安装`, alt: true } : null,
    metrics.openclawmp_installs ? { label: `${formatNumber(metrics.openclawmp_installs)} 安装`, alt: true } : null,
    metrics.skillhub_stars ? { label: `${formatNumber(metrics.skillhub_stars)} 收藏`, alt: false } : null,
    metrics.openclawmp_total_stars ? { label: `${formatNumber(metrics.openclawmp_total_stars)} 星标`, alt: false } : null,
  ].filter(Boolean).slice(0, 3);
}

function buildSearchBlob(item) {
  return [
    item.name,
    item.displayName,
    item.author,
    item.description,
    ...(item.tags || []),
    ...(item.categories || []),
    ...(item.sources || []),
  ].join(' ').toLowerCase();
}

function applyFilters() {
  const query = state.searchQuery.trim().toLowerCase();
  state.filteredItems = state.allItems.filter((item) => {
    if (state.selectedSource !== 'all' && !(item.sources || []).includes(state.selectedSource)) return false;
    if (state.selectedCategory !== 'all' && !(item.categories || []).includes(state.selectedCategory)) return false;
    if (query && !item.searchBlob.includes(query)) return false;
    return true;
  });

  const sorters = {
    popularity: (a, b) => (b.popularity || 0) - (a.popularity || 0),
    downloads: (a, b) => (b.metrics?.skillhub_downloads || 0) - (a.metrics?.skillhub_downloads || 0),
    installs: (a, b) => ((b.metrics?.skillhub_installs || 0) + (b.metrics?.openclawmp_installs || 0)) - ((a.metrics?.skillhub_installs || 0) + (a.metrics?.openclawmp_installs || 0)),
    stars: (a, b) => ((b.metrics?.skillhub_stars || 0) + (b.metrics?.openclawmp_total_stars || 0)) - ((a.metrics?.skillhub_stars || 0) + (a.metrics?.openclawmp_total_stars || 0)),
    name: (a, b) => a.displayName.localeCompare(b.displayName, 'zh-CN'),
    updated: (a, b) => (b.version || '').localeCompare(a.version || '', 'zh-CN'),
  };

  state.filteredItems.sort(sorters[state.sortBy] || sorters.popularity);
  renderResults();
}

function createChip(label, value, group, activeValue) {
  const button = document.createElement('button');
  button.className = `chip${value === activeValue ? ' active' : ''}`;
  button.textContent = label;
  button.addEventListener('click', () => {
    if (group === 'source') state.selectedSource = value;
    if (group === 'category') state.selectedCategory = value;
    state.visibleCount = config.pageSize || 24;
    renderFilters();
    applyFilters();
  });
  return button;
}

function renderFilters() {
  const sources = ['all', 'skillhub', 'openclawmp', 'merged'];
  elements.sourceChips.replaceChildren(...sources.map((source) => createChip(
    source === 'all' ? '全部来源' : source,
    source,
    'source',
    state.selectedSource,
  )));

  const categoryCounts = new Map();
  state.allItems.forEach((item) => {
    (item.categories || []).forEach((category) => {
      if (!category) return;
      categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
    });
  });
  const ordered = [...categoryCounts.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name);
  const visibleCategories = state.categoriesExpanded ? ordered : ordered.slice(0, 8);
  const sortedCategories = ['all', ...visibleCategories];
  elements.categoryChips.replaceChildren(...sortedCategories.map((category) => createChip(
    category === 'all' ? '全部分类' : category,
    category,
    'category',
    state.selectedCategory,
  )));
  if (elements.categoryToggleBtn) {
    if (ordered.length > 8) {
      elements.categoryToggleBtn.classList.remove('hidden');
      elements.categoryToggleBtn.textContent = state.categoriesExpanded ? '收起' : '展开更多';
    } else {
      elements.categoryToggleBtn.classList.add('hidden');
    }
  }
}

function renderHero(statsPayload) {
  const stats = [
    { label: '总技能数', value: formatNumber(statsPayload.total || state.allItems.length), hint: '严格合并后的唯一技能数' },
    { label: '双源重合', value: formatNumber(statsPayload.sources?.merged || 0), hint: '同时出现在两个平台' },
    { label: 'SkillHub 收录', value: formatNumber(statsPayload.sources?.skillhub || 0), hint: '仅来自 SkillHub' },
    { label: 'OpenClawMP 收录', value: formatNumber(statsPayload.sources?.openclawmp || 0), hint: '仅来自 OpenClawMP' },
  ];
  elements.heroStats.innerHTML = stats.map((item) => `
    <article class="hero-stat-card">
      <div class="label">${escapeHtml(item.label)}</div>
      <div class="value">${escapeHtml(item.value)}</div>
      <div class="hint">${escapeHtml(item.hint)}</div>
    </article>
  `).join('');
  elements.footerMeta.textContent = `共 ${formatNumber(statsPayload.total || state.allItems.length)} 个技能，适合静态托管。`;
}

function renderFeatured() {
  const featured = state.allItems.slice(0, config.featuredCount || 8);
  const topThree = featured.slice(0, 3);
  const gridItems = featured.slice(3);

  elements.leaderboardList.innerHTML = topThree.map((item, index) => {
    const metrics = summarizeMetrics(item);
    const primaryArchive = item.archives?.[0];
    const downloadHref = primaryArchive ? buildArchiveUrl(primaryArchive) : '';
    const downloadLabel = primaryArchive ? (primaryArchive.source === 'openclawmp' ? '下载包' : '下载 ZIP') : '暂无下载';
    return `
      <article class="leaderboard-item" data-featured-id="${escapeHtml(item.id)}">
        <div class="leaderboard-rank">${index + 1}</div>
        <div class="leaderboard-body">
          <div class="source-badges">${(item.sources || []).map((source) => `<span class="source-pill">${escapeHtml(source)}</span>`).join('')}</div>
          <div class="leaderboard-title">${escapeHtml(item.displayName)}</div>
          <div class="leaderboard-desc">${escapeHtml(item.description || '暂无描述')}</div>
          <div class="feature-metrics">${metrics.map((metric) => `<span class="metric-pill${metric.alt ? ' alt' : ''}">${escapeHtml(metric.label)}</span>`).join('')}</div>
          <div class="leaderboard-actions">
            <button class="ghost-btn leaderboard-detail-btn" type="button">查看详情</button>
            ${downloadHref ? `<a class="primary-btn small" target="_blank" rel="noreferrer" href="${escapeHtml(downloadHref)}">${escapeHtml(downloadLabel)}</a>` : ''}
          </div>
        </div>
      </article>
    `;
  }).join('');

  elements.leaderboardList.querySelectorAll('.leaderboard-item').forEach((node, index) => {
    const item = topThree[index];
    if (!item) return;
    node.addEventListener('click', (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.closest('a, button')) return;
      openDetails(item);
    });
    const detailButton = node.querySelector('.leaderboard-detail-btn');
    if (detailButton) {
      detailButton.addEventListener('click', () => openDetails(item));
    }
  });

  elements.featuredStrip.innerHTML = gridItems.map((item, index) => {
    const metrics = summarizeMetrics(item);
    return `
      <article class="feature-card">
        <div>
          <div class="feature-topline">
            <div class="feature-rank">TOP ${index + 4}</div>
            <div class="source-badges">${(item.sources || []).map((source) => `<span class="source-pill">${escapeHtml(source)}</span>`).join('')}</div>
          </div>
          <div class="title">${escapeHtml(item.displayName)}</div>
          <div class="desc">${escapeHtml(item.description || '暂无描述')}</div>
          <div class="feature-metrics">${metrics.map((metric) => `<span class="metric-pill${metric.alt ? ' alt' : ''}">${escapeHtml(metric.label)}</span>`).join('')}</div>
        </div>
        <div class="footer">
          <span>${escapeHtml(item.author || '匿名作者')}</span>
          <span>v${escapeHtml(item.version)}</span>
        </div>
      </article>
    `;
  }).join('');
}

function renderCard(item) {
  const fragment = elements.cardTemplate.content.firstElementChild.cloneNode(true);
  const firstLetter = (item.displayName || item.name || '?').trim().slice(0, 1).toUpperCase();
  fragment.querySelector('.skill-avatar').textContent = firstLetter;
  fragment.querySelector('.card-title').textContent = item.displayName || item.name;
  fragment.querySelector('.card-version').textContent = `v${item.version}`;
  fragment.querySelector('.card-meta').innerHTML = `<strong>${escapeHtml(item.author || '匿名作者')}</strong> · ${(item.sources || []).map(escapeHtml).join(' / ')} · ${escapeHtml(item.version)}`;
  fragment.querySelector('.card-description').textContent = item.description || '暂无描述';
  fragment.querySelector('.card-category').textContent = item.categories?.[0] ? item.categories[0] : '未标注';
  fragment.querySelector('.source-badges').innerHTML = (item.sources || []).map((source) => `<span class="source-pill">${escapeHtml(source)}</span>`).join('');
  fragment.querySelector('.tag-list').innerHTML = (item.tags || []).slice(0, 4).map((tag) => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join('');
  fragment.querySelector('.metric-row').innerHTML = summarizeMetrics(item).map((metric) => `<span class="metric-pill${metric.alt ? ' alt' : ''}">${escapeHtml(metric.label)}</span>`).join('');

  const primaryArchive = item.archives?.[0];
  const downloadBtn = fragment.querySelector('.download-btn');
  if (primaryArchive) {
    downloadBtn.href = buildArchiveUrl(primaryArchive);
    downloadBtn.textContent = primaryArchive.source === 'openclawmp' ? '下载包' : '下载 ZIP';
  } else {
    downloadBtn.removeAttribute('href');
    downloadBtn.classList.add('hidden');
  }

  fragment.querySelector('.details-btn').addEventListener('click', () => openDetails(item));
  return fragment;
}

function renderResults() {
  const total = state.filteredItems.length;
  const showing = Math.min(state.visibleCount, total);
  elements.resultsHeading.textContent = `找到 ${formatNumber(total)} 个技能`;
  elements.resultsMeta.textContent = `当前显示 ${formatNumber(showing)} 个，来源：${state.selectedSource === 'all' ? '全部' : state.selectedSource}，分类：${state.selectedCategory === 'all' ? '全部' : state.selectedCategory}`;
  const pills = [
    { label: `来源：${state.selectedSource === 'all' ? '全部' : state.selectedSource}`, alt: true },
    { label: `分类：${state.selectedCategory === 'all' ? '全部' : state.selectedCategory}`, alt: false },
    { label: `排序：${elements.sortSelect.options[elements.sortSelect.selectedIndex]?.text || '综合热度'}`, alt: true },
    { label: `当前显示 ${formatNumber(showing)} / ${formatNumber(total)}`, alt: false },
  ];
  elements.resultsPills.innerHTML = pills.map((pill) => `<span class="metric-pill${pill.alt ? ' alt' : ''}">${escapeHtml(pill.label)}</span>`).join('');

  if (!total) {
    elements.cardsGrid.innerHTML = '';
    elements.emptyState.classList.remove('hidden');
    elements.loadMoreBtn.classList.add('hidden');
    return;
  }

  elements.emptyState.classList.add('hidden');
  const visibleItems = state.filteredItems.slice(0, showing);
  const fragment = document.createDocumentFragment();
  visibleItems.forEach((item) => fragment.appendChild(renderCard(item)));
  elements.cardsGrid.replaceChildren(fragment);

  if (showing < total) {
    elements.loadMoreBtn.classList.remove('hidden');
    elements.loadMoreBtn.textContent = `继续加载（剩余 ${formatNumber(total - showing)}）`;
  } else {
    elements.loadMoreBtn.classList.add('hidden');
  }
}

function openDetails(item) {
  const metrics = item.metrics || {};
  const archiveLinks = (item.archives || []).map((archive) => `
    <a class="primary-btn small" target="_blank" rel="noreferrer" href="${escapeHtml(buildArchiveUrl(archive))}">${escapeHtml(archive.label)}</a>
  `).join('');

  elements.drawerContent.innerHTML = `
    <div class="drawer-header">
      <div class="source-badges">${(item.sources || []).map((source) => `<span class="source-pill">${escapeHtml(source)}</span>`).join('')}</div>
      <h3>${escapeHtml(item.displayName || item.name)}</h3>
      <p class="drawer-summary">${escapeHtml(item.description || '暂无描述')}</p>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">基础信息</div>
      <div class="metric-row">
        <span class="metric-pill alt">作者：${escapeHtml(item.author || '未知')}</span>
        <span class="metric-pill">版本：${escapeHtml(item.version)}</span>
        <span class="metric-pill alt">热度：${formatNumber(item.popularity || 0)}</span>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">平台指标</div>
      <div class="metric-row">
        <span class="metric-pill">SkillHub 下载：${formatNumber(metrics.skillhub_downloads || 0)}</span>
        <span class="metric-pill alt">SkillHub 安装：${formatNumber(metrics.skillhub_installs || 0)}</span>
        <span class="metric-pill">SkillHub 收藏：${formatNumber(metrics.skillhub_stars || 0)}</span>
        <span class="metric-pill alt">OpenClawMP 安装：${formatNumber(metrics.openclawmp_installs || 0)}</span>
        <span class="metric-pill">OpenClawMP 星标：${formatNumber(metrics.openclawmp_total_stars || 0)}</span>
        <span class="metric-pill alt">GitHub Stars：${formatNumber(metrics.openclawmp_github_stars || 0)}</span>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">标签与分类</div>
      <div class="tag-list">
        ${(item.categories || []).map((category) => `<span class="tag-pill">${escapeHtml(category)}</span>`).join('')}
        ${(item.tags || []).map((tag) => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join('')}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">下载与跳转</div>
      <div class="drawer-links">
        ${archiveLinks}
        ${item.homepage ? `<a class="secondary-btn" target="_blank" rel="noreferrer" href="${escapeHtml(item.homepage)}">打开来源页</a>` : ''}
        ${item.readmeUrl ? `<a class="secondary-btn" target="_blank" rel="noreferrer" href="${escapeHtml(item.readmeUrl)}">查看 README</a>` : ''}
      </div>
    </div>

    ${item.installCommand ? `
      <div class="drawer-section">
        <div class="drawer-section-title">安装命令</div>
        <pre class="drawer-code">${escapeHtml(item.installCommand)}</pre>
      </div>
    ` : ''}
  `;
  elements.detailDrawer.classList.remove('hidden');
  elements.detailDrawer.setAttribute('aria-hidden', 'false');
}

function closeDetails() {
  elements.detailDrawer.classList.add('hidden');
  elements.detailDrawer.setAttribute('aria-hidden', 'true');
}

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to load ${url}`);
  return response.json();
}

async function bootstrap() {
  if (elements.brandName) {
    elements.brandName.textContent = config.brandName || 'Skill Market';
  }
  elements.searchInput.addEventListener('input', (event) => {
    state.searchQuery = event.target.value;
    state.visibleCount = config.pageSize || 24;
    applyFilters();
  });
  elements.sortSelect.addEventListener('change', (event) => {
    state.sortBy = event.target.value;
    applyFilters();
  });
  if (elements.categoryToggleBtn) {
    elements.categoryToggleBtn.addEventListener('click', () => {
      state.categoriesExpanded = !state.categoriesExpanded;
      renderFilters();
    });
  }
  elements.loadMoreBtn.addEventListener('click', () => {
    state.visibleCount += config.pageSize || 24;
    renderResults();
  });
  elements.drawerBackdrop.addEventListener('click', closeDetails);
  elements.drawerClose.addEventListener('click', closeDetails);

  try {
    const [manifest, stats] = await Promise.all([
      loadJson(config.manifestUrl || './data/skills.json'),
      loadJson(config.statsUrl || './data/stats.json'),
    ]);
    state.allItems = (manifest.items || []).map((item) => ({ ...item, searchBlob: buildSearchBlob(item) }));
    renderHero(stats);
    renderFilters();
    renderFeatured();
    applyFilters();
  } catch (error) {
    elements.resultsHeading.textContent = '载入失败';
    elements.resultsMeta.textContent = error.message;
    elements.heroStats.innerHTML = `<article class="hero-stat-card"><div class="label">错误</div><div class="value">Manifest 未加载</div><div class="hint">${escapeHtml(error.message)}</div></article>`;
  }
}

bootstrap();
