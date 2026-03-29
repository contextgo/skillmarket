const config = window.SKILL_MARKET_CONFIG || {};
const VIEW_LABELS = {
  curated: "精选技能",
  full: "精选技能",
};

const state = {
  allItems: [],
  filteredItems: [],
  visibleCount: config.pageSize || 24,
  selectedView: config.defaultView || "curated",
  selectedCategory: "all",
  selectedIndustry: "all",
  searchQuery: "",
  sortBy: "quality",
  categoriesExpanded: false,
  datasets: {
    curated: null,
    full: null,
  },
  statsByView: {
    curated: null,
    full: null,
  },
  industryIndex: [],
  bundles: [],
};

const elements = {
  brandName: document.getElementById("brandName"),
  heroStats: document.getElementById("heroStats"),
  featuredStrip: document.getElementById("featuredStrip"),
  leaderboardList: document.getElementById("leaderboardList"),
  viewToggle: document.getElementById("viewToggle"),
  industryShowcase: document.getElementById("industryShowcase"),
  bundleGrid: document.getElementById("bundleGrid"),
  industryChips: document.getElementById("industryChips"),
  categoryChips: document.getElementById("categoryChips"),
  categoryToggleBtn: document.getElementById("categoryToggleBtn"),
  searchInput: document.getElementById("searchInput"),
  sortSelect: document.getElementById("sortSelect"),
  cardsGrid: document.getElementById("cardsGrid"),
  loadMoreBtn: document.getElementById("loadMoreBtn"),
  resultsHeading: document.getElementById("resultsHeading"),
  resultsMeta: document.getElementById("resultsMeta"),
  resultsPills: document.getElementById("resultsPills"),
  footerMeta: document.getElementById("footerMeta"),
  emptyState: document.getElementById("emptyState"),
  cardTemplate: document.getElementById("cardTemplate"),
  detailDrawer: document.getElementById("detailDrawer"),
  drawerBackdrop: document.getElementById("drawerBackdrop"),
  drawerClose: document.getElementById("drawerClose"),
  drawerContent: document.getElementById("drawerContent"),
};

const formatNumber = (value) => new Intl.NumberFormat("zh-CN").format(Number(value || 0));
const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
const escapeHtml = (value = "") =>
  String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

function buildArchiveUrl(archive) {
  if (!archive) return "";
  const base = (config.packageBaseUrls && config.packageBaseUrls[archive.source]) || "";
  return `${base}${archive.relativePath}`;
}

function getIndustryMeta(industryId) {
  return state.industryIndex.find((item) => item.id === industryId) || null;
}

function getIndustryLabel(industryId) {
  return getIndustryMeta(industryId)?.label || industryId || "未归类";
}

function getCuratedItems() {
  return state.datasets.curated?.items || [];
}

function getCuratedItemById(itemId) {
  return getCuratedItems().find((item) => item.id === itemId) || null;
}

function renderMiniSkillList(skillIds = []) {
  return skillIds
    .map((skillId) => getCuratedItemById(skillId))
    .filter(Boolean)
    .map(
      (item) => `
        <button class="drawer-skill-link" type="button" data-skill-id="${escapeHtml(item.id)}">
          <span>${escapeHtml(item.displayName || item.name)}</span>
          <span>${escapeHtml(item.primaryCapability || "通用能力")}</span>
        </button>
      `,
    )
    .join("");
}

function attachDrawerSkillLinks() {
  elements.drawerContent.querySelectorAll("[data-skill-id]").forEach((node) => {
    node.addEventListener("click", () => {
      const item = getCuratedItemById(node.getAttribute("data-skill-id"));
      if (item) openDetails(item);
    });
  });
}

function buildSearchBlob(item) {
  return [
    item.name,
    item.displayName,
    item.author,
    item.description,
    item.primaryCapability,
    ...(item.tags || []),
    ...(item.categories || []),
    ...(item.industries || []),
    ...(item.themes || []),
  ]
    .join(" ")
    .toLowerCase();
}

function summarizeMetrics(item) {
  const metrics = item.metrics || {};
  const installs = (metrics.skillhub_installs || 0) + (metrics.openclawmp_installs || 0);
  const stars = (metrics.skillhub_stars || 0) + (metrics.openclawmp_total_stars || 0) + (metrics.openclawmp_github_stars || 0);
  return [
    item.qualityScore ? { label: `${formatNumber(item.qualityScore)} 推荐度`, alt: true } : null,
    installs ? { label: `${formatNumber(installs)} 使用`, alt: false } : null,
    stars ? { label: `${formatNumber(stars)} 关注`, alt: true } : null,
  ]
    .filter(Boolean)
    .slice(0, 3);
}

function getDisplayIndustry(item) {
  return item.industries?.[0] ? getIndustryLabel(item.industries[0]) : item.categories?.[0] || "未归类";
}

function normalizeItems(items) {
  return (items || []).map((item) => ({
    ...item,
    searchBlob: buildSearchBlob(item),
  }));
}

function applyFilters() {
  const query = state.searchQuery.trim().toLowerCase();
  state.filteredItems = state.allItems.filter((item) => {
    if (state.selectedIndustry !== "all" && !(item.industries || []).includes(state.selectedIndustry)) return false;
    if (state.selectedCategory !== "all" && !(item.categories || []).includes(state.selectedCategory)) return false;
    if (query && !item.searchBlob.includes(query)) return false;
    return true;
  });

  const sorters = {
    quality: (a, b) => (b.qualityScore || 0) - (a.qualityScore || 0) || (b.popularity || 0) - (a.popularity || 0),
    popularity: (a, b) => (b.popularity || 0) - (a.popularity || 0),
    installs: (a, b) =>
      ((b.metrics?.skillhub_installs || 0) + (b.metrics?.openclawmp_installs || 0)) -
      ((a.metrics?.skillhub_installs || 0) + (a.metrics?.openclawmp_installs || 0)),
    stars: (a, b) =>
      ((b.metrics?.skillhub_stars || 0) + (b.metrics?.openclawmp_total_stars || 0)) -
      ((a.metrics?.skillhub_stars || 0) + (a.metrics?.openclawmp_total_stars || 0)),
    name: (a, b) => (a.displayName || a.name || "").localeCompare(b.displayName || b.name || "", "zh-CN"),
    updated: (a, b) => (b.version || "").localeCompare(a.version || "", "zh-CN"),
  };

  state.filteredItems.sort(sorters[state.sortBy] || sorters.quality);
  renderResults();
}

function createChip(label, value, group, activeValue) {
  const button = document.createElement("button");
  button.className = `chip${value === activeValue ? " active" : ""}`;
  button.textContent = label;
  button.addEventListener("click", () => {
    if (group === "category") state.selectedCategory = value;
    if (group === "industry") state.selectedIndustry = value;
    state.visibleCount = config.pageSize || 24;
    renderFilters();
    applyFilters();
  });
  return button;
}

function renderViewToggle() {
  if (!elements.viewToggle) return;
  elements.viewToggle.classList.add("hidden");
}

function renderFilters() {
  const industryCounts = new Map();
  state.allItems.forEach((item) => {
    (item.industries || []).forEach((industryId) => {
      industryCounts.set(industryId, (industryCounts.get(industryId) || 0) + 1);
    });
  });
  const industryIds = ["all", ...state.industryIndex.filter((item) => industryCounts.get(item.id)).map((item) => item.id)];
  elements.industryChips.replaceChildren(
    ...industryIds.map((industryId) =>
      createChip(
        industryId === "all" ? "全部行业" : `${getIndustryLabel(industryId)} · ${formatNumber(industryCounts.get(industryId) || 0)}`,
        industryId,
        "industry",
        state.selectedIndustry,
      ),
    ),
  );

  const categoryCounts = new Map();
  state.allItems.forEach((item) => {
    (item.categories || []).forEach((category) => {
      if (!category) return;
      categoryCounts.set(category, (categoryCounts.get(category) || 0) + 1);
    });
  });
  const ordered = [...categoryCounts.entries()].sort((a, b) => b[1] - a[1]).map(([name]) => name);
  const visibleCategories = state.categoriesExpanded ? ordered : ordered.slice(0, 8);
  const categoryValues = ["all", ...visibleCategories];
  elements.categoryChips.replaceChildren(
    ...categoryValues.map((category) =>
      createChip(category === "all" ? "全部分类" : category, category, "category", state.selectedCategory),
    ),
  );
  if (ordered.length > 8) {
    elements.categoryToggleBtn.classList.remove("hidden");
    elements.categoryToggleBtn.textContent = state.categoriesExpanded ? "收起" : "展开更多";
  } else {
    elements.categoryToggleBtn.classList.add("hidden");
  }
}

function renderHero(statsPayload) {
  const cards = [
    { label: "策展收录", value: formatNumber(statsPayload?.total || state.allItems.length), hint: "当前市场中重点保留的能力" },
    { label: "行业专题", value: formatNumber(state.industryIndex.length || 0), hint: "按真实场景组织的行业入口" },
    { label: "组合方案", value: formatNumber(state.bundles.length || 0), hint: "围绕任务链整理出的推荐组合" },
    { label: "能力主题", value: formatNumber(statsPayload?.clusterCount || 0), hint: "相似功能会被收敛成更清晰的能力主题" },
  ];

  elements.heroStats.innerHTML = cards
    .map(
      (item) => `
      <article class="hero-stat-card">
        <div class="label">${escapeHtml(item.label)}</div>
        <div class="value">${escapeHtml(item.value)}</div>
        <div class="hint">${escapeHtml(item.hint)}</div>
      </article>
    `,
    )
    .join("");

  elements.footerMeta.textContent = `当前策展收录 ${formatNumber(statsPayload?.total || state.allItems.length)} 个技能，按场景组织。`;
}

function renderIndustries() {
  if (!elements.industryShowcase) return;
  elements.industryShowcase.innerHTML = state.industryIndex
    .map((industry) => {
      const active = state.selectedIndustry === industry.id;
      return `
        <article class="industry-card${active ? " active" : ""}" data-industry-id="${escapeHtml(industry.id)}">
          <div class="industry-card-topline">
            <div class="eyebrow">${escapeHtml(industry.label)}</div>
            <div class="industry-count">${escapeHtml(formatNumber(industry.count))}</div>
          </div>
          <h3>${escapeHtml(industry.label)}</h3>
          <p>${escapeHtml(industry.summary)}</p>
          <div class="industry-problem-list">
            ${(industry.problems || []).slice(0, 2).map((problem) => `<div class="mini-note">${escapeHtml(problem)}</div>`).join("")}
          </div>
          <div class="tag-list">
            ${(industry.topThemes || []).map((theme) => `<span class="tag-pill">${escapeHtml(theme)}</span>`).join("")}
          </div>
          <div class="industry-actions">
            <button class="secondary-btn small-industry-detail-btn" type="button">查看方案</button>
            <button class="ghost-btn small-industry-btn" type="button">按此行业筛选</button>
          </div>
        </article>
      `;
    })
    .join("");

  elements.industryShowcase.querySelectorAll(".industry-card").forEach((node) => {
    node.addEventListener("click", (event) => {
      const industryId = node.getAttribute("data-industry-id");
      if (!industryId) return;
      if (event.target instanceof HTMLElement && !event.target.closest("button")) {
        applyIndustrySelection(industryId);
      }
    });
    const actionButton = node.querySelector(".small-industry-btn");
    actionButton?.addEventListener("click", () => {
      const industryId = node.getAttribute("data-industry-id");
      if (industryId) applyIndustrySelection(industryId);
    });
    node.querySelector(".small-industry-detail-btn")?.addEventListener("click", () => {
      const industryId = node.getAttribute("data-industry-id");
      if (industryId) openIndustrySolution(industryId);
    });
  });
}

function renderBundles() {
  if (!elements.bundleGrid) return;
  const itemMap = new Map((state.datasets.curated?.items || []).map((item) => [item.id, item]));
  elements.bundleGrid.innerHTML = state.bundles
    .map((bundle) => {
      const topIndustry = bundle.industries?.[0];
      const representativeSkill = itemMap.get(bundle.skillIds?.[0] || "");
      return `
        <article class="bundle-card" data-bundle-id="${escapeHtml(bundle.id)}">
          <div class="bundle-card-topline">
            <div class="eyebrow">组合包</div>
            ${topIndustry ? `<span class="source-pill">${escapeHtml(getIndustryLabel(topIndustry))}</span>` : ""}
          </div>
          <h3>${escapeHtml(bundle.title)}</h3>
          <p>${escapeHtml(bundle.summary)}</p>
          ${bundle.forTeams ? `<div class="mini-note">${escapeHtml(`适用团队：${bundle.forTeams}`)}</div>` : ""}
          <div class="bundle-steps">
            ${(bundle.steps || [])
              .map(
                (step, index) => `
                  <div class="bundle-step">
                    <div class="bundle-step-index">${index + 1}</div>
                    <div>
                      <div class="bundle-step-title">${escapeHtml(step.label)}</div>
                      <div class="bundle-step-meta">${escapeHtml((step.themes || []).join(" / "))}</div>
                    </div>
                  </div>
                `,
              )
              .join("")}
          </div>
          <div class="bundle-actions">
            ${topIndustry ? '<button class="ghost-btn bundle-filter-btn" type="button">按行业浏览</button>' : ""}
            <button class="secondary-btn bundle-solution-btn" type="button">查看组合详情</button>
            ${
              representativeSkill
                ? `<button class="secondary-btn bundle-detail-btn" type="button">${escapeHtml(
                    `查看 ${representativeSkill.displayName || representativeSkill.name}`,
                  )}</button>`
                : ""
            }
          </div>
        </article>
      `;
    })
    .join("");

  elements.bundleGrid.querySelectorAll(".bundle-card").forEach((node, index) => {
    const bundle = state.bundles[index];
    if (!bundle) return;
    node.querySelector(".bundle-filter-btn")?.addEventListener("click", () => {
      if (bundle.industries?.[0]) applyIndustrySelection(bundle.industries[0]);
    });
    node.querySelector(".bundle-solution-btn")?.addEventListener("click", () => {
      openBundleSolution(bundle.id);
    });
    node.querySelector(".bundle-detail-btn")?.addEventListener("click", () => {
      const item = getCuratedItemById(bundle.skillIds?.[0]);
      if (item) openDetails(item);
    });
  });
}

function renderFeatured() {
  const featured = state.allItems.slice(0, config.featuredCount || 8);
  const topThree = featured.slice(0, 3);
  const gridItems = featured.slice(3);

  elements.leaderboardList.innerHTML = topThree
    .map((item, index) => {
      const metrics = summarizeMetrics(item);
      const primaryArchive = item.archives?.[0];
      const downloadHref = primaryArchive ? buildArchiveUrl(primaryArchive) : "";
      const downloadLabel = primaryArchive ? "获取技能包" : "暂无下载";
      return `
        <article class="leaderboard-item" data-featured-id="${escapeHtml(item.id)}">
          <div class="leaderboard-rank">${index + 1}</div>
          <div class="leaderboard-body">
            <div class="source-badges"><span class="source-pill">${escapeHtml(item.primaryCapability || "策展能力")}</span></div>
            <div class="leaderboard-title">${escapeHtml(item.displayName || item.name)}</div>
            <div class="leaderboard-desc">${escapeHtml(item.description || "暂无描述")}</div>
            <div class="feature-metrics">${metrics
              .map((metric) => `<span class="metric-pill${metric.alt ? " alt" : ""}">${escapeHtml(metric.label)}</span>`)
              .join("")}</div>
            <div class="leaderboard-actions">
              <button class="ghost-btn leaderboard-detail-btn" type="button">查看详情</button>
              ${downloadHref ? `<a class="primary-btn small" target="_blank" rel="noreferrer" href="${escapeHtml(downloadHref)}">${escapeHtml(downloadLabel)}</a>` : ""}
            </div>
          </div>
        </article>
      `;
    })
    .join("");

  elements.leaderboardList.querySelectorAll(".leaderboard-item").forEach((node, index) => {
    const item = topThree[index];
    if (!item) return;
    node.addEventListener("click", (event) => {
      if (event.target instanceof HTMLElement && event.target.closest("a, button")) return;
      openDetails(item);
    });
    node.querySelector(".leaderboard-detail-btn")?.addEventListener("click", () => openDetails(item));
  });

  elements.featuredStrip.innerHTML = gridItems
    .map(
      (item, index) => `
        <article class="feature-card" data-feature-id="${escapeHtml(item.id)}">
          <div>
            <div class="feature-topline">
              <div class="feature-rank">TOP ${index + 4}</div>
              <div class="source-badges"><span class="source-pill">${escapeHtml(getDisplayIndustry(item))}</span></div>
            </div>
            <div class="title">${escapeHtml(item.displayName || item.name)}</div>
            <div class="desc">${escapeHtml(item.description || "暂无描述")}</div>
            <div class="feature-metrics">${summarizeMetrics(item)
              .map((metric) => `<span class="metric-pill${metric.alt ? " alt" : ""}">${escapeHtml(metric.label)}</span>`)
              .join("")}</div>
          </div>
          <div class="footer">
            <span>${escapeHtml(getDisplayIndustry(item))}</span>
            <span>${escapeHtml(item.primaryCapability || "通用能力")}</span>
          </div>
        </article>
      `,
    )
    .join("");

  elements.featuredStrip.querySelectorAll(".feature-card").forEach((node, index) => {
    const item = gridItems[index];
    node.addEventListener("click", () => {
      if (item) openDetails(item);
    });
  });
}

function renderCard(item) {
  const fragment = elements.cardTemplate.content.firstElementChild.cloneNode(true);
  const firstLetter = (item.displayName || item.name || "?").trim().slice(0, 1).toUpperCase();
  fragment.querySelector(".skill-avatar").textContent = firstLetter;
  fragment.querySelector(".card-title").textContent = item.displayName || item.name;
  fragment.querySelector(".card-version").textContent = `v${item.version}`;
  fragment.querySelector(".card-meta").innerHTML = `<strong>${escapeHtml(item.author || "匿名作者")}</strong> · ${escapeHtml(
    item.primaryCapability || "通用能力",
  )}`;
  fragment.querySelector(".card-description").textContent = item.description || "暂无描述";
  fragment.querySelector(".card-category").textContent = getDisplayIndustry(item);
  fragment.querySelector(".source-badges").innerHTML = `<span class="source-pill">${escapeHtml(
    item.selectionReason || item.primaryCapability || "精选收录",
  )}</span>`;
  fragment.querySelector(".tag-list").innerHTML = [
    ...(item.industries || []).slice(0, 2).map((industryId) => `<span class="tag-pill">${escapeHtml(getIndustryLabel(industryId))}</span>`),
    ...(item.themes || []).slice(0, 2).map((theme) => `<span class="tag-pill">${escapeHtml(theme)}</span>`),
  ].join("");
  fragment.querySelector(".metric-row").innerHTML = summarizeMetrics(item)
    .map((metric) => `<span class="metric-pill${metric.alt ? " alt" : ""}">${escapeHtml(metric.label)}</span>`)
    .join("");

  const primaryArchive = item.archives?.[0];
  const downloadBtn = fragment.querySelector(".download-btn");
  if (primaryArchive) {
    downloadBtn.href = buildArchiveUrl(primaryArchive);
    downloadBtn.textContent = "获取技能包";
  } else {
    downloadBtn.removeAttribute("href");
    downloadBtn.classList.add("hidden");
  }

  fragment.querySelector(".details-btn").addEventListener("click", () => openDetails(item));
  return fragment;
}

function renderResults() {
  const total = state.filteredItems.length;
  const showing = Math.min(state.visibleCount, total);
  elements.resultsHeading.textContent = `策展技能库 · ${formatNumber(total)} 个技能`;
  elements.resultsMeta.textContent = `当前显示 ${formatNumber(showing)} 个，行业：${
    state.selectedIndustry === "all" ? "全部" : getIndustryLabel(state.selectedIndustry)
  }，分类：${state.selectedCategory === "all" ? "全部" : state.selectedCategory}`;

  const pills = [
    { label: `行业：${state.selectedIndustry === "all" ? "全部" : getIndustryLabel(state.selectedIndustry)}`, alt: false },
    { label: `排序：${elements.sortSelect.options[elements.sortSelect.selectedIndex]?.text || "推荐度"}`, alt: true },
    { label: `当前显示 ${formatNumber(showing)} / ${formatNumber(total)}`, alt: false },
  ];
  elements.resultsPills.innerHTML = pills
    .map((pill) => `<span class="metric-pill${pill.alt ? " alt" : ""}">${escapeHtml(pill.label)}</span>`)
    .join("");

  if (!total) {
    elements.cardsGrid.innerHTML = "";
    elements.emptyState.classList.remove("hidden");
    elements.loadMoreBtn.classList.add("hidden");
    return;
  }

  elements.emptyState.classList.add("hidden");
  const visibleItems = state.filteredItems.slice(0, showing);
  const fragment = document.createDocumentFragment();
  visibleItems.forEach((item) => fragment.appendChild(renderCard(item)));
  elements.cardsGrid.replaceChildren(fragment);

  if (showing < total) {
    elements.loadMoreBtn.classList.remove("hidden");
    elements.loadMoreBtn.textContent = `继续加载（剩余 ${formatNumber(total - showing)}）`;
  } else {
    elements.loadMoreBtn.classList.add("hidden");
  }
}

function openDetails(item) {
  const metrics = item.metrics || {};
  const archiveLinks = (item.archives || [])
    .map(
      (archive) => `
      <a class="primary-btn small" target="_blank" rel="noreferrer" href="${escapeHtml(buildArchiveUrl(archive))}">获取技能包</a>
    `,
    )
    .join("");
  const industries = (item.industries || []).map(getIndustryLabel);

  elements.drawerContent.innerHTML = `
    <div class="drawer-header">
      <div class="source-badges"><span class="source-pill">${escapeHtml(item.primaryCapability || "策展能力")}</span></div>
      <h3>${escapeHtml(item.displayName || item.name)}</h3>
      <p class="drawer-summary">${escapeHtml(item.description || "暂无描述")}</p>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">策展说明</div>
      <div class="metric-row">
        <span class="metric-pill alt">能力：${escapeHtml(item.primaryCapability || "通用能力")}</span>
        ${item.qualityScore ? `<span class="metric-pill">推荐度：${escapeHtml(formatNumber(item.qualityScore))}</span>` : ""}
        ${item.selectionReason ? `<span class="metric-pill alt">入选理由：${escapeHtml(item.selectionReason)}</span>` : ""}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">基础信息</div>
      <div class="metric-row">
        <span class="metric-pill alt">作者：${escapeHtml(item.author || "未知")}</span>
        <span class="metric-pill">版本：${escapeHtml(item.version)}</span>
        <span class="metric-pill alt">行业：${escapeHtml(industries.join(" / ") || "未归类")}</span>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">热度参考</div>
      <div class="metric-row">
        <span class="metric-pill">使用参考：${formatNumber((metrics.skillhub_installs || 0) + (metrics.openclawmp_installs || 0))}</span>
        <span class="metric-pill alt">关注参考：${formatNumber((metrics.skillhub_stars || 0) + (metrics.openclawmp_total_stars || 0) + (metrics.openclawmp_github_stars || 0))}</span>
        <span class="metric-pill">下载参考：${formatNumber(metrics.skillhub_downloads || 0)}</span>
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">主题、标签与分类</div>
      <div class="tag-list">
        ${industries.map((industry) => `<span class="tag-pill">${escapeHtml(industry)}</span>`).join("")}
        ${(item.categories || []).map((category) => `<span class="tag-pill">${escapeHtml(category)}</span>`).join("")}
        ${(item.themes || []).map((theme) => `<span class="tag-pill">${escapeHtml(theme)}</span>`).join("")}
        ${(item.tags || []).map((tag) => `<span class="tag-pill">${escapeHtml(tag)}</span>`).join("")}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">下载与跳转</div>
      <div class="drawer-links">
        ${archiveLinks}
        ${item.homepage ? `<a class="secondary-btn" target="_blank" rel="noreferrer" href="${escapeHtml(item.homepage)}">查看介绍页</a>` : ""}
        ${item.readmeUrl ? `<a class="secondary-btn" target="_blank" rel="noreferrer" href="${escapeHtml(item.readmeUrl)}">查看 README</a>` : ""}
      </div>
    </div>

    ${
      item.installCommand
        ? `
      <div class="drawer-section">
        <div class="drawer-section-title">安装命令</div>
        <pre class="drawer-code">${escapeHtml(item.installCommand)}</pre>
      </div>
    `
        : ""
    }
  `;
  elements.detailDrawer.classList.remove("hidden");
  elements.detailDrawer.setAttribute("aria-hidden", "false");
}

function openIndustrySolution(industryId) {
  const industry = getIndustryMeta(industryId);
  if (!industry) return;
  const relatedBundles = state.bundles.filter((bundle) => (bundle.industries || []).includes(industryId));
  elements.drawerContent.innerHTML = `
    <div class="drawer-header">
      <div class="source-badges"><span class="source-pill">行业方案</span></div>
      <h3>${escapeHtml(industry.label)}</h3>
      <p class="drawer-summary">${escapeHtml(industry.summary)}</p>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">典型问题</div>
      <div class="drawer-list">
        ${(industry.problems || []).map((problem) => `<div class="drawer-list-item">${escapeHtml(problem)}</div>`).join("")}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">适用场景</div>
      <div class="drawer-list">
        ${(industry.useCases || []).map((item) => `<div class="drawer-list-item">${escapeHtml(item)}</div>`).join("")}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">推荐流程</div>
      <div class="drawer-list">
        ${(industry.workflow || []).map((step, index) => `<div class="drawer-list-item">${escapeHtml(`${index + 1}. ${step}`)}</div>`).join("")}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-section-title">预期结果</div>
      <div class="tag-list">
        ${(industry.outcomes || []).map((item) => `<span class="tag-pill">${escapeHtml(item)}</span>`).join("")}
      </div>
    </div>

    ${
      relatedBundles.length
        ? `
      <div class="drawer-section">
        <div class="drawer-section-title">推荐组合</div>
        <div class="drawer-list">
          ${relatedBundles
            .map(
              (bundle) => `
                <button class="drawer-list-item drawer-action-link" type="button" data-bundle-id="${escapeHtml(bundle.id)}">
                  ${escapeHtml(bundle.title)} · ${escapeHtml(bundle.summary)}
                </button>
              `,
            )
            .join("")}
        </div>
      </div>
    `
        : ""
    }

    <div class="drawer-section">
      <div class="drawer-section-title">推荐技能</div>
      <div class="drawer-skill-list">
        ${renderMiniSkillList(industry.recommendedSkillIds || industry.topSkillIds || [])}
      </div>
    </div>

    <div class="drawer-section">
      <div class="drawer-links">
        <button class="primary-btn" type="button" data-apply-industry="${escapeHtml(industry.id)}">按该行业浏览</button>
      </div>
    </div>
  `;
  elements.detailDrawer.classList.remove("hidden");
  elements.detailDrawer.setAttribute("aria-hidden", "false");
  elements.drawerContent.querySelectorAll("[data-bundle-id]").forEach((node) => {
    node.addEventListener("click", () => openBundleSolution(node.getAttribute("data-bundle-id")));
  });
  elements.drawerContent.querySelector("[data-apply-industry]")?.addEventListener("click", () => {
    closeDetails();
    applyIndustrySelection(industry.id);
  });
  attachDrawerSkillLinks();
}

function openBundleSolution(bundleId) {
  const bundle = state.bundles.find((entry) => entry.id === bundleId);
  if (!bundle) return;
  elements.drawerContent.innerHTML = `
    <div class="drawer-header">
      <div class="source-badges">
        <span class="source-pill">组合方案</span>
        ${(bundle.industries || []).map((industryId) => `<span class="source-pill">${escapeHtml(getIndustryLabel(industryId))}</span>`).join("")}
      </div>
      <h3>${escapeHtml(bundle.title)}</h3>
      <p class="drawer-summary">${escapeHtml(bundle.summary)}</p>
    </div>

    ${
      bundle.forTeams
        ? `
      <div class="drawer-section">
        <div class="drawer-section-title">适用团队</div>
        <div class="metric-row"><span class="metric-pill alt">${escapeHtml(bundle.forTeams)}</span></div>
      </div>
    `
        : ""
    }

    ${
      bundle.valuePoints?.length
        ? `
      <div class="drawer-section">
        <div class="drawer-section-title">适合原因</div>
        <div class="drawer-list">
          ${bundle.valuePoints.map((item) => `<div class="drawer-list-item">${escapeHtml(item)}</div>`).join("")}
        </div>
      </div>
    `
        : ""
    }

    <div class="drawer-section">
      <div class="drawer-section-title">组合步骤</div>
      <div class="bundle-steps">
        ${(bundle.steps || [])
          .map(
            (step, index) => `
              <div class="bundle-step">
                <div class="bundle-step-index">${index + 1}</div>
                <div>
                  <div class="bundle-step-title">${escapeHtml(step.label)}</div>
                  <div class="bundle-step-meta">${escapeHtml((step.themes || []).join(" / "))}</div>
                  <div class="drawer-skill-list compact">
                    ${renderMiniSkillList(step.skillIds || [])}
                  </div>
                </div>
              </div>
            `,
          )
          .join("")}
      </div>
    </div>

    ${
      bundle.deliverables?.length
        ? `
      <div class="drawer-section">
        <div class="drawer-section-title">典型交付物</div>
        <div class="tag-list">
          ${bundle.deliverables.map((item) => `<span class="tag-pill">${escapeHtml(item)}</span>`).join("")}
        </div>
      </div>
    `
        : ""
    }

    <div class="drawer-section">
      <div class="drawer-links">
        ${(bundle.industries || [])
          .map(
            (industryId) =>
              `<button class="secondary-btn" type="button" data-open-industry="${escapeHtml(industryId)}">${escapeHtml(
                `查看${getIndustryLabel(industryId)}方案`,
              )}</button>`,
          )
          .join("")}
      </div>
    </div>
  `;
  elements.detailDrawer.classList.remove("hidden");
  elements.detailDrawer.setAttribute("aria-hidden", "false");
  elements.drawerContent.querySelectorAll("[data-open-industry]").forEach((node) => {
    node.addEventListener("click", () => openIndustrySolution(node.getAttribute("data-open-industry")));
  });
  attachDrawerSkillLinks();
}

function closeDetails() {
  elements.detailDrawer.classList.add("hidden");
  elements.detailDrawer.setAttribute("aria-hidden", "true");
}

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to load ${url}`);
  return response.json();
}

async function ensureViewLoaded(view) {
  if (state.datasets[view]) return;
  const manifestUrl = view === "curated" ? config.manifestUrl : config.fullManifestUrl || "./data/skills.json";
  const statsUrl = view === "curated" ? config.statsUrl : config.fullStatsUrl || "./data/stats.json";
  const [manifest, stats] = await Promise.all([loadJson(manifestUrl), loadJson(statsUrl)]);
  state.datasets[view] = {
    items: normalizeItems(manifest.items || []),
  };
  state.statsByView[view] = stats;
}

function syncCurrentView() {
  state.allItems = state.datasets[state.selectedView]?.items || [];
  state.visibleCount = config.pageSize || 24;
  renderViewToggle();
  renderHero(state.statsByView[state.selectedView]);
  renderFilters();
  renderFeatured();
  renderIndustries();
  renderBundles();
  applyFilters();
}

async function switchView(view) {
  if (view === state.selectedView) return;
  await ensureViewLoaded(view);
  state.selectedView = view;
  syncCurrentView();
}

function applyIndustrySelection(industryId) {
  state.selectedIndustry = industryId;
  state.visibleCount = config.pageSize || 24;
  renderFilters();
  renderIndustries();
  applyFilters();
  document.getElementById("grid")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function bootstrap() {
  if (elements.brandName) {
    elements.brandName.textContent = config.brandName || "ContextGo";
  }

  elements.searchInput.addEventListener("input", (event) => {
    state.searchQuery = event.target.value;
    state.visibleCount = config.pageSize || 24;
    applyFilters();
  });
  elements.sortSelect.addEventListener("change", (event) => {
    state.sortBy = event.target.value;
    applyFilters();
  });
  elements.categoryToggleBtn.addEventListener("click", () => {
    state.categoriesExpanded = !state.categoriesExpanded;
    renderFilters();
  });
  elements.loadMoreBtn.addEventListener("click", () => {
    state.visibleCount += config.pageSize || 24;
    renderResults();
  });
  elements.drawerBackdrop.addEventListener("click", closeDetails);
  elements.drawerClose.addEventListener("click", closeDetails);

  try {
    const [manifest, stats, industryPayload, bundlePayload] = await Promise.all([
      loadJson(config.manifestUrl || "./data/curated_skills.json"),
      loadJson(config.statsUrl || "./data/curated_stats.json"),
      loadJson(config.industryUrl || "./data/industry_index.json"),
      loadJson(config.bundleUrl || "./data/bundles.json"),
    ]);

    state.datasets.curated = {
      items: normalizeItems(manifest.items || []),
    };
    state.statsByView.curated = stats;
    state.industryIndex = industryPayload.industries || [];
    state.bundles = bundlePayload.bundles || [];
    renderViewToggle();
    syncCurrentView();
  } catch (error) {
    elements.resultsHeading.textContent = "载入失败";
    elements.resultsMeta.textContent = error.message;
    elements.heroStats.innerHTML = `<article class="hero-stat-card"><div class="label">错误</div><div class="value">Manifest 未加载</div><div class="hint">${escapeHtml(error.message)}</div></article>`;
  }
}

bootstrap();
