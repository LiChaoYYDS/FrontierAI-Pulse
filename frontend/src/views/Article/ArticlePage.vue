<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useArticleStore } from '@/stores/articleStore'
import { useSourceStore } from '@/stores/sourceStore'
import * as api from '@/api'
import type { ArticleParams, Article } from '@/types/article'

const router = useRouter()
const selectedTags = ref<string[]>([])
const selectedSourceId = ref<number | null>(null)
const showUnreadOnly = ref(false)
const sortBy = ref<'time' | 'score'>('score')
const page = ref(1)
const pageSize = ref(10)

const articleStore = useArticleStore()
const sourceStore = useSourceStore()

// ── 收藏/点赞浮动面板 ──────────────────────────────────────────────────────────
const favorites = ref<Article[]>([])
const likes = ref<Article[]>([])
const favLoading = ref(false)
const likeLoading = ref(false)

async function onFavShow(show: boolean) {
  if (show) {
    favLoading.value = true
    try {
      const res = await api.listArticles({ is_favorite: true, page_size: 20, sort_by: 'time' })
      favorites.value = res.items
    } finally {
      favLoading.value = false
    }
  }
}
async function onLikeShow(show: boolean) {
  if (show) {
    likeLoading.value = true
    try {
      const res = await api.listArticles({ is_liked: true, page_size: 20, sort_by: 'time' })
      likes.value = res.items
    } finally {
      likeLoading.value = false
    }
  }
}

// ── 过滤/排序 ──────────────────────────────────────────────────────────────────
const sourceOptions = computed(() => {
  const seen = new Set<string>()
  return sourceStore.sources
    .filter(s => s.is_active)  // 只展示用户在来源页中已启用的来源
    .filter(s => { if (seen.has(s.name)) return false; seen.add(s.name); return true })
    .map(s => ({ label: s.name, value: s.id }))
})
const tagOptions = computed(() => {
  const seen = new Set<string>()
  return sourceStore.allTags
    .filter(t => { if (seen.has(t)) return false; seen.add(t); return true })
    .map(t => ({ label: t, value: t }))
})
const sourceNameMap = computed(() => {
  const m = new Map<number, string>()
  sourceStore.sources.forEach(s => m.set(s.id, s.name))
  return m
})

async function loadArticles() {
  const params: ArticleParams = {
    page: page.value,
    page_size: pageSize.value,
    tags: selectedTags.value.length > 0 ? selectedTags.value : undefined,
    source_id: selectedSourceId.value ?? undefined,
    is_read: showUnreadOnly.value ? false : undefined,
    sort_by: sortBy.value,
  }
  await articleStore.fetchArticles(params)
}

function onFilterChange() { page.value = 1; loadArticles() }
function onPageChange(p: number) { page.value = p; loadArticles() }
function onSortChange(val: 'time' | 'score') { sortBy.value = val; page.value = 1; loadArticles() }

function getTagColor(tag: string) {
  const colors = ['#18a058', '#2080f0', '#f0a020', '#d03050', '#8058f0']
  let hash = 0
  for (let i = 0; i < tag.length; i++) hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function getSourceName(sourceId: number | null, sourceType: string | null): string {
  if (sourceId && sourceNameMap.value.has(sourceId)) return sourceNameMap.value.get(sourceId)!
  const typeMap: Record<string, string> = { rss: 'RSS', arxiv: 'arXiv', website: '网站', github: 'GitHub' }
  return sourceType ? (typeMap[sourceType] || sourceType) : '未知'
}

function getTimeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days} 天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

function scoreType(score: number): 'error' | 'warning' | 'info' {
  if (score >= 80) return 'error'
  if (score >= 60) return 'warning'
  return 'info'
}

async function toggleFavorite(id: number, current: boolean) {
  await articleStore.updateArticle(id, { is_favorite: !current })
  favorites.value = []  // 下次打开面板时刷新
}
async function toggleLike(id: number, current: boolean) {
  await articleStore.updateArticle(id, { is_liked: !current })
  likes.value = []
}

function toggleTagFilter(tag: string) {
  const idx = selectedTags.value.indexOf(tag)
  if (idx >= 0) selectedTags.value.splice(idx, 1)
  else selectedTags.value.push(tag)
  page.value = 1
  loadArticles()
}

onMounted(async () => {
  await Promise.all([loadArticles(), sourceStore.loadSources()])
})
</script>

<template>
  <div class="page-layout">
  <div class="feed-page">

    <!-- 吸顶标题栏 -->
    <div class="feed-header">
      <h2 style="margin: 0">📰 前沿资讯 Feed</h2>
      <div style="display: flex; align-items: center; gap: 8px">
        <n-tag v-if="articleStore.total > 0" type="info" round>共 {{ articleStore.total }} 篇</n-tag>

        <!-- 收藏浮动面板 -->
        <n-popover trigger="click" placement="bottom-end" :width="330" @update:show="onFavShow">
          <template #trigger>
            <n-button size="small" secondary>
              ⭐ 收藏{{ favorites.length > 0 ? ` (${favorites.length})` : '' }}
            </n-button>
          </template>
          <div class="pop-panel">
            <div class="pop-title-bar">⭐ 我的收藏</div>
            <n-spin :show="favLoading" style="min-height: 60px">
              <n-empty v-if="!favLoading && favorites.length === 0"
                description="还没有收藏的文章" style="padding: 20px 0" />
              <div v-else>
                <div v-for="a in favorites" :key="a.id" class="pop-item"
                  @click="router.push(`/articles/${a.id}`)">
                  <div class="pop-item-title">{{ a.title }}</div>
                  <div class="pop-item-meta">
                    {{ getSourceName(a.source_id, a.source_type) }} · {{ getTimeAgo(a.published_at) }}
                  </div>
                </div>
              </div>
            </n-spin>
          </div>
        </n-popover>

        <!-- 点赞浮动面板 -->
        <n-popover trigger="click" placement="bottom-end" :width="330" @update:show="onLikeShow">
          <template #trigger>
            <n-button size="small" secondary>
              👍 点赞{{ likes.length > 0 ? ` (${likes.length})` : '' }}
            </n-button>
          </template>
          <div class="pop-panel">
            <div class="pop-title-bar">👍 我的点赞</div>
            <n-spin :show="likeLoading" style="min-height: 60px">
              <n-empty v-if="!likeLoading && likes.length === 0"
                description="还没有点赞的文章" style="padding: 20px 0" />
              <div v-else>
                <div v-for="a in likes" :key="a.id" class="pop-item"
                  @click="router.push(`/articles/${a.id}`)">
                  <div class="pop-item-title">{{ a.title }}</div>
                  <div class="pop-item-meta">
                    {{ getSourceName(a.source_id, a.source_type) }} · {{ getTimeAgo(a.published_at) }}
                  </div>
                </div>
              </div>
            </n-spin>
          </div>
        </n-popover>
      </div>
    </div>

    <!-- 过滤栏 -->
    <n-card :bordered="true" style="margin-top: 12px">
      <div class="filter-row">
        <span class="filter-label">来源：</span>
        <n-select v-model:value="selectedSourceId" :options="sourceOptions" placeholder="全部来源"
          clearable style="width: 180px" @update:value="onFilterChange" />
        <span class="filter-label">标签：</span>
        <n-select v-model:value="selectedTags" :options="tagOptions" multiple clearable filterable
          placeholder="选择标签" style="width: 180px" @update:value="onFilterChange()" />
        <n-checkbox v-model:checked="showUnreadOnly" @update:checked="onFilterChange">仅未读</n-checkbox>
        <div style="margin-left: auto">
          <n-radio-group :value="sortBy" @update:value="onSortChange" size="small">
            <n-radio-button value="time">按时间</n-radio-button>
            <n-radio-button value="score">按相关度</n-radio-button>
          </n-radio-group>
        </div>
      </div>
    </n-card>

    <n-empty v-if="!articleStore.loading && articleStore.articles.length === 0"
      description="没有符合条件的文章" style="margin-top: 60px" />

    <n-spin :show="articleStore.loading">
      <div class="article-list">
        <n-card v-for="article in articleStore.articles" :key="article.id"
          class="article-card" :class="{ 'is-read': article.is_read }"
          :bordered="true" size="small" style="margin-top: 16px">
          <div class="card-header">
            <div class="card-title-area">
              <span v-if="!article.is_read" class="unread-dot" />
              <h3 class="article-title" :class="{ 'read-title': article.is_read }"
                @click="router.push(`/articles/${article.id}`)">
                {{ article.title }}
              </h3>
            </div>
            <n-tag v-if="article.importance_score > 50" :type="scoreType(article.importance_score)"
              size="small" round style="flex-shrink: 0">
              匹配度 {{ article.importance_score }}%
            </n-tag>
          </div>

          <div class="card-meta">
            <n-space size="small" align="center">
              <n-tag size="tiny" :bordered="false">{{ getSourceName(article.source_id, article.source_type) }}</n-tag>
              <span class="meta-time">{{ getTimeAgo(article.published_at) }}</span>
              <span v-if="article.is_read" style="font-size: 12px; color: #18a058">✓ 已读</span>
            </n-space>
          </div>

          <p class="article-summary">{{
            article.summary ||
            (article.content ? article.content.slice(0, 200) + (article.content.length > 200 ? '…' : '') : '暂无摘要')
          }}</p>

          <div class="card-footer">
            <n-space size="small">
              <n-tag v-for="tag in (article.tags ?? [])" :key="tag" size="small"
                :color="{ color: getTagColor(tag) + '20', textColor: getTagColor(tag), borderColor: getTagColor(tag) + '40' }">
                {{ tag }}
              </n-tag>
            </n-space>
            <n-space size="small">
              <n-button quaternary circle size="small"
                :type="article.is_favorite ? 'warning' : 'default'"
                @click="toggleFavorite(article.id, article.is_favorite)">
                {{ article.is_favorite ? '⭐' : '☆' }}
              </n-button>
              <n-button quaternary circle size="small"
                :type="article.is_liked ? 'primary' : 'default'"
                @click="toggleLike(article.id, article.is_liked)">
                {{ article.is_liked ? '👍' : '👍🏻' }}
              </n-button>
            </n-space>
          </div>
        </n-card>
      </div>
    </n-spin>

    <div class="pagination">
      <n-pagination v-model:page="page"
        :page-count="Math.max(1, Math.ceil(articleStore.total / pageSize))"
        :page-size="pageSize" :item-count="articleStore.total"
        @update:page="onPageChange" />
    </div>
  </div>

<!--  &lt;!&ndash; 右侧栏 &ndash;&gt;-->
<!--  <aside class="feed-sidebar">-->
<!--    &lt;!&ndash; 数据概览 &ndash;&gt;-->
<!--    <div class="sidebar-card">-->
<!--      <div class="sidebar-card-title">📊 当前概览</div>-->
<!--      <div class="stat-grid">-->
<!--        <div class="stat-item">-->
<!--          <div class="stat-val">{{ articleStore.total }}</div>-->
<!--          <div class="stat-lbl">总文章</div>-->
<!--        </div>-->
<!--        <div class="stat-item">-->
<!--          <div class="stat-val" style="color: var(&#45;&#45;accent)">-->
<!--            {{ articleStore.articles.filter(a => !a.is_read).length }}-->
<!--          </div>-->
<!--          <div class="stat-lbl">待阅读</div>-->
<!--        </div>-->
<!--        <div class="stat-item">-->
<!--          <div class="stat-val" style="color: #f59e0b">-->
<!--            {{ articleStore.articles.filter(a => a.is_favorite).length }}-->
<!--          </div>-->
<!--          <div class="stat-lbl">已收藏</div>-->
<!--        </div>-->
<!--      </div>-->
<!--    </div>-->

<!--    &lt;!&ndash; 热门标签 &ndash;&gt;-->
<!--    <div class="sidebar-card" v-if="sourceStore.allTags.length > 0">-->
<!--      <div class="sidebar-card-title">🏷 热门标签</div>-->
<!--      <div class="tag-cloud">-->
<!--        <span-->
<!--          v-for="tag in sourceStore.allTags.slice(0, 12)"-->
<!--          :key="tag"-->
<!--          class="tag-pill"-->
<!--          :class="{ active: selectedTags.includes(tag) }"-->
<!--          @click="toggleTagFilter(tag)"-->
<!--        >{{ tag }}</span>-->
<!--      </div>-->
<!--    </div>-->

<!--    &lt;!&ndash; 快捷筛选 &ndash;&gt;-->
<!--    <div class="sidebar-card">-->
<!--      <div class="sidebar-card-title">⚡ 快捷筛选</div>-->
<!--      <div class="quick-actions">-->
<!--        <button class="qa-btn" :class="{ active: showUnreadOnly }"-->
<!--          @click="showUnreadOnly = !showUnreadOnly; onFilterChange()">-->
<!--          📬 仅未读-->
<!--        </button>-->
<!--        <button class="qa-btn" :class="{ active: sortBy === 'score' }"-->
<!--          @click="onSortChange('score')">-->
<!--          🎯 按相关度-->
<!--        </button>-->
<!--        <button class="qa-btn" :class="{ active: sortBy === 'time' }"-->
<!--          @click="onSortChange('time')">-->
<!--          🕐 按时间-->
<!--        </button>-->
<!--        <button class="qa-btn" v-if="selectedTags.length || selectedSourceId || showUnreadOnly"-->
<!--          @click="selectedTags = []; selectedSourceId = null; showUnreadOnly = false; onFilterChange()">-->
<!--          ✕ 清除筛选-->
<!--        </button>-->
<!--      </div>-->
<!--    </div>-->

<!--    &lt;!&ndash; 来源分布 &ndash;&gt;-->
<!--    <div class="sidebar-card" v-if="sourceStore.sources.length > 0">-->
<!--      <div class="sidebar-card-title">📡 活跃来源</div>-->
<!--      <div class="source-list-small">-->
<!--        <div v-for="s in sourceStore.sources.filter(s => s.is_active).slice(0, 6)"-->
<!--          :key="s.id" class="source-row-small"-->
<!--          :class="{ active: selectedSourceId === s.id }"-->
<!--          @click="selectedSourceId = selectedSourceId === s.id ? null : s.id; onFilterChange()">-->
<!--          <span class="source-dot" />-->
<!--          <span class="source-name-small">{{ s.name }}</span>-->
<!--        </div>-->
<!--      </div>-->
<!--    </div>-->
<!--  </aside>-->
</div>
</template>

<style scoped>
.feed-page { max-width: 860px; margin: 0 auto; }

.feed-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0 12px;
  background: color-mix(in srgb, var(--bg) 90%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
}

.pop-panel { padding: 4px 0; }
.pop-title-bar {
  font-size: 11px; font-weight: 600; padding: 4px 4px 10px;
  color: var(--text-3); letter-spacing: 0.06em; text-transform: uppercase;
}
.pop-item {
  padding: 8px 6px; border-radius: 6px; cursor: pointer;
  transition: background 0.1s; border-bottom: 1px solid var(--border);
}
.pop-item:last-child { border-bottom: none; }
.pop-item:hover { background: var(--surface-2); }
.pop-item-title { font-size: 13px; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-1); }
.pop-item-meta { font-size: 11px; color: var(--text-3); margin-top: 2px; }

.filter-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 4px 0; }
.filter-label { font-size: 12.5px; color: var(--text-3); white-space: nowrap; }

.article-list { margin-top: 12px; display: flex; flex-direction: column; gap: 2px; }

/* 文章卡片 */
.article-card {
  transition: border-color 0.15s, box-shadow 0.15s !important;
  cursor: default;
}
.article-card:hover {
  box-shadow: var(--shadow-md) !important;
  border-color: var(--border-hov) !important;
}
.article-card.is-read { opacity: 0.48; }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.card-title-area { display: flex; align-items: center; gap: 7px; flex: 1; min-width: 0; }

.unread-dot {
  width: 5px; height: 5px; border-radius: 50%;
  background: var(--accent); flex-shrink: 0;
}

.article-title {
  margin: 0; font-size: 15px; font-weight: 600; line-height: 1.45;
  cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  color: var(--text-1); transition: color 0.12s;
  letter-spacing: -0.015em;
}
.article-title:hover { color: var(--accent); }
.read-title { font-weight: 400; color: var(--text-2); }

.card-meta { margin-top: 6px; display: flex; align-items: center; gap: 8px; }
.meta-time { font-size: 12px; color: var(--text-3); font-variant-numeric: tabular-nums; }

.article-summary { margin: 10px 0 0; font-size: 13.5px; line-height: 1.65; color: var(--text-2); }

.card-footer { margin-top: 14px; display: flex; justify-content: space-between; align-items: center; }
.pagination { display: flex; justify-content: center; margin-top: 32px; padding-bottom: 40px; }

/* ── 双栏布局 ──────────────────────────────────────────────── */
.page-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  max-width: 1240px;
  margin: 0 auto;
}
.feed-page {
  flex: 1;
  min-width: 0;
}

/* ── 右侧边栏 ─────────────────────────────────────────────── */
.feed-sidebar {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 16px;
}

.sidebar-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  transition: border-color 0.15s;
}
.sidebar-card:hover { border-color: var(--border-hov); }
.sidebar-card-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-3);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 12px;
}

/* 统计网格 */
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.stat-item { text-align: center; }
.stat-val { font-size: 22px; font-weight: 700; line-height: 1.2; color: var(--text-1); }
.stat-lbl { font-size: 11px; color: var(--text-3); margin-top: 3px; }

/* 标签云 */
.tag-cloud { display: flex; flex-wrap: wrap; gap: 6px; }
.tag-pill {
  font-size: 11.5px; padding: 3px 9px; border-radius: 99px;
  border: 1px solid var(--border); color: var(--text-2);
  cursor: pointer; transition: all 0.12s; user-select: none;
  background: transparent;
}
.tag-pill:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.tag-pill.active { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); font-weight: 500; }

/* 快捷按钮 */
.quick-actions { display: flex; flex-direction: column; gap: 6px; }
.qa-btn {
  width: 100%; text-align: left; padding: 7px 10px;
  border-radius: 7px; border: 1px solid var(--border);
  background: transparent; color: var(--text-2);
  font-size: 13px; cursor: pointer; transition: all 0.12s;
}
.qa-btn:hover { background: var(--surface-2); color: var(--text-1); border-color: var(--border-hov); }
.qa-btn.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); }

/* 来源列表 */
.source-list-small { display: flex; flex-direction: column; gap: 4px; }
.source-row-small {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 6px; border-radius: 6px; cursor: pointer;
  transition: background 0.1s;
}
.source-row-small:hover { background: var(--surface-2); }
.source-row-small.active { background: var(--accent-soft); }
.source-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--text-3); flex-shrink: 0; transition: background 0.1s;
}
.source-row-small.active .source-dot { background: var(--accent); }
.source-name-small { font-size: 13px; color: var(--text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-row-small.active .source-name-small { color: var(--accent); }

@media (max-width: 960px) {
  .feed-sidebar { display: none; }
  .feed-page { max-width: 100%; }
}
</style>
