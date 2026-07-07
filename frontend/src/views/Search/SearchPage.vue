<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSourceStore } from '@/stores/sourceStore'
import * as api from '@/api'
import type { Article } from '@/types/article'
import type { SearchParams } from '@/api'

const router = useRouter()
const sourceStore = useSourceStore()

const sourceNameMap = computed(() => {
  const m = new Map<number, string>()
  sourceStore.sources.forEach(s => m.set(s.id, s.name))
  return m
})

function getSourceName(sourceId: number | null, sourceType: string | null): string {
  if (sourceId && sourceNameMap.value.has(sourceId)) return sourceNameMap.value.get(sourceId)!
  const typeMap: Record<string, string> = { rss: 'RSS', arxiv: 'arXiv', website: '网站', github: 'GitHub' }
  return sourceType ? (typeMap[sourceType] || sourceType) : '未知'
}

const q = ref('')
const selectedTags = ref<string[]>([])
const selectedSourceId = ref<number | null>(null)
const dateFrom = ref<string | null>(null)
const dateTo = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(20)

const articles = ref<Article[]>([])
const total = ref(0)
const loading = ref(false)
const suggestions = ref<string[]>([])

const sourceOptions = computed(() => {
  const seen = new Set<string>()
  return sourceStore.sources
    .filter(s => { if (seen.has(s.name)) return false; seen.add(s.name); return true })
    .map(s => ({ label: s.name, value: s.id }))
})
const tagOptions = computed(() =>
  sourceStore.allTags.map(t => ({ label: t, value: t }))
)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

let debounceTimer: ReturnType<typeof setTimeout>

watch(q, (val) => {
  clearTimeout(debounceTimer)
  if (val.length >= 1) {
    debounceTimer = setTimeout(() => fetchSuggestions(val), 200)
  } else {
    suggestions.value = []
  }
  debounceTimer = setTimeout(() => { page.value = 1; doSearch() }, 300)
})

async function fetchSuggestions(keyword: string) {
  try {
    const res = await api.searchSuggest(keyword)
    suggestions.value = res.suggestions.filter(s => !selectedTags.value.includes(s))
  } catch { /* ignore */ }
}

async function doSearch() {
  loading.value = true
  try {
    const params: SearchParams = {
      q: q.value || undefined,
      tags: selectedTags.value.length ? selectedTags.value : undefined,
      source_id: selectedSourceId.value ?? undefined,
      date_from: dateFrom.value ?? undefined,
      date_to: dateTo.value ?? undefined,
      page: page.value,
      page_size: pageSize.value,
    }
    const res = await api.searchArticles(params)
    articles.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onFilterChange() { page.value = 1; doSearch() }
function onPageChange(p: number) { page.value = p; doSearch() }

// 关键词高亮：在文本中将 q 包裹 <mark>
function highlight(text: string | null, keyword: string): string {
  if (!text || !keyword) return text ?? ''
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(escaped, 'gi'), m => `<mark>${m}</mark>`)
}

function getTimeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diff / 86400000)
  if (days < 1) return '今天'
  if (days < 7) return `${days} 天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => sourceStore.loadSources())
</script>

<template>
  <div class="search-page">
    <h2 style="margin: 0 0 16px">🔍 搜索</h2>

    <!-- 搜索框 + 建议 -->
    <n-input-group>
      <n-auto-complete
        v-model:value="q"
        :options="suggestions.map(s => ({ label: s, value: s }))"
        placeholder="搜索文章标题、摘要、内容..."
        clearable
        style="flex: 1"
        @select="(v: string) => { selectedTags.value.push(v); q = ''; suggestions.value = []; onFilterChange() }"
      />
    </n-input-group>

    <!-- 过滤面板 -->
    <n-card size="small" :bordered="true" style="margin-top: 12px">
      <div class="filter-row">
        <span class="filter-label">来源：</span>
        <n-select v-model:value="selectedSourceId" :options="sourceOptions"
          placeholder="全部来源" clearable style="width: 160px" @update:value="onFilterChange" />
        <span class="filter-label">标签：</span>
        <n-select v-model:value="selectedTags" :options="tagOptions"
          multiple clearable filterable placeholder="选择标签" style="width: 200px"
          @update:value="onFilterChange" />
        <span class="filter-label">日期：</span>
        <n-date-picker v-model:value="dateFrom" type="date" placeholder="开始"
          clearable style="width: 130px" @update:value="onFilterChange" />
        <span style="color:#888; font-size:13px">—</span>
        <n-date-picker v-model:value="dateTo" type="date" placeholder="结束"
          clearable style="width: 130px" @update:value="onFilterChange" />
      </div>
    </n-card>

    <!-- 结果数 -->
    <div v-if="total > 0" style="margin: 12px 0; font-size: 13px; color: #888">
      共找到 {{ total }} 条结果
    </div>

    <n-spin :show="loading" style="margin-top: 8px">
      <n-empty v-if="!loading && articles.length === 0 && (q || selectedTags.length)"
        description="没有找到匹配的文章" style="margin-top: 40px" />

      <div v-else>
        <n-card v-for="article in articles" :key="article.id"
          size="small" :bordered="true" style="margin-top: 12px"
          class="result-card" @click="router.push(`/articles/${article.id}`)">
          <div class="result-title" v-html="highlight(article.title, q)" />
          <div class="result-meta">
            <n-tag size="tiny" :bordered="false">{{ getSourceName(article.source_id, article.source_type) }}</n-tag>
            <span style="font-size:12px; color:#888">{{ getTimeAgo(article.published_at) }}</span>
            <n-tag v-for="tag in (article.tags ?? []).slice(0, 3)" :key="tag" size="tiny">{{ tag }}</n-tag>
          </div>
          <p class="result-summary"
            v-html="highlight(article.summary || article.content?.slice(0, 150) || '', q)" />
        </n-card>
      </div>
    </n-spin>

    <div v-if="total > pageSize" class="pagination">
      <n-pagination v-model:page="page" :page-count="totalPages"
        :page-size="pageSize" :item-count="total" @update:page="onPageChange" />
    </div>
  </div>
</template>

<style scoped>
.search-page { max-width: 900px; margin: 0 auto; padding-bottom: 48px; }
.filter-row { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; }
.filter-label { font-size: 13px; color: #888; white-space: nowrap; }
.result-card { cursor: pointer; transition: box-shadow 0.15s; }
.result-card:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
.result-title { font-size: 15px; font-weight: 600; line-height: 1.4; }
.result-meta { display: flex; align-items: center; gap: 8px; margin: 6px 0; flex-wrap: wrap; }
.result-summary { font-size: 13px; color: #666; line-height: 1.6; margin: 4px 0 0; }
.pagination { display: flex; justify-content: center; margin-top: 24px; }
</style>

<style>
mark { background: #fff3cd; color: inherit; border-radius: 2px; padding: 0 1px; }
</style>
