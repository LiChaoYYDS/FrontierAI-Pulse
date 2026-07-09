<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import * as api from '@/api'
import type { Article, ArticleResponse } from '@/types/article'

const router  = useRouter()
const message = useMessage()

const articles   = ref<Article[]>([])
const total      = ref(0)
const loading    = ref(false)
const searching  = ref(false)
const page       = ref(1)
const pageSize   = ref(20)
const searchText = ref('')

// ── 按日期分组 ─────────────────────────────────────────────────────────────────
const groupedHistory = computed(() => {
  const groups: { label: string; date: string; items: Article[] }[] = []
  const map = new Map<string, Article[]>()

  for (const a of articles.value) {
    const d  = a.read_at ? new Date(a.read_at) : new Date(a.created_at ?? '')
    const key = d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(a)
  }

  const today     = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(today.getDate() - 1)
  const todayKey     = today.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  const yesterdayKey = yesterday.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })

  for (const [key, items] of map) {
    let label = key
    if (key === todayKey)     label = '今天'
    else if (key === yesterdayKey) label = '昨天'
    else {
      const d = new Date(key.replace(/\//g, '-'))
      label = `${d.getMonth() + 1}月${d.getDate()}日（${['周日','周一','周二','周三','周四','周五','周六'][d.getDay()]}）`
    }
    groups.push({ label, date: key, items })
  }
  return groups
})

// ── 读取历史 ──────────────────────────────────────────────────────────────────
async function loadHistory() {
  loading.value = true
  try {
    const res = await api.getHistory({ page: page.value, page_size: pageSize.value, q: searchText.value })
    articles.value = (res as any).items ?? []
    total.value    = (res as any).total ?? 0
  } catch {
    message.error('加载历史记录失败')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  loadHistory()
}

function onPageChange(p: number) {
  page.value = p
  loadHistory()
}

// ── 删除操作 ──────────────────────────────────────────────────────────────────
async function handleDelete(id: number) {
  try {
    await api.deleteHistoryItem(id)
    articles.value = articles.value.filter(a => a.id !== id)
    total.value--
    message.success('已从历史记录中删除')
  } catch {
    message.error('删除失败')
  }
}

async function handleClearAll() {
  try {
    await api.clearAllHistory()
    articles.value = []
    total.value = 0
    message.success('历史记录已清空')
  } catch {
    message.error('清空失败')
  }
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────
function formatTime(dateStr: string | null): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

onMounted(loadHistory)
</script>

<template>
  <div class="history-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2 style="margin: 0">📖 浏览历史</h2>
        <span style="font-size: 13px; color: #888; margin-top: 4px; display: block">
          记录最近30天内阅读过的文章
        </span>
      </div>
      <n-space align="center">
        <n-input
          v-model:value="searchText"
          placeholder="搜索标题…"
          clearable
          style="width: 220px"
          @update:value="onSearch"
        >
          <template #prefix>🔍</template>
        </n-input>
        <n-popconfirm v-if="total > 0" @positive-click="handleClearAll">
          <template #trigger>
            <n-button size="small" type="error" secondary>🗑 清除全部</n-button>
          </template>
          确认清除全部历史记录？此操作不可撤销。
        </n-popconfirm>
      </n-space>
    </div>

    <!-- 历史列表 -->
    <n-spin :show="loading" style="margin-top: 20px; min-height: 200px">
      <n-empty v-if="!loading && articles.length === 0"
               description="暂无浏览历史" style="margin-top: 60px" />

      <div v-else>
        <!-- 按日期分组 -->
        <div v-for="group in groupedHistory" :key="group.date" class="date-group">
          <div class="date-label">{{ group.label }}</div>
          <n-card :bordered="true" size="small" style="margin-bottom: 4px">
            <div v-for="article in group.items" :key="article.id" class="history-row">
              <span class="read-time">{{ formatTime(article.read_at) }}</span>
              <span class="history-title" @click="router.push(`/articles/${article.id}`)">
                {{ article.title }}
              </span>
              <n-button
                size="tiny" quaternary type="error"
                class="delete-btn"
                @click.stop="handleDelete(article.id)"
              >✕</n-button>
            </div>
          </n-card>
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="pagination">
          <n-pagination
            v-model:page="page"
            :page-count="Math.ceil(total / pageSize)"
            :page-size="pageSize"
            :item-count="total"
            @update:page="onPageChange"
          />
        </div>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.history-page { max-width: 800px; margin: 0 auto; }
.page-header  { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px; }

.date-group  { margin-bottom: 20px; }
.date-label  {
  font-size: 12px; font-weight: 600; color: var(--text-3);
  letter-spacing: 0.04em; text-transform: uppercase;
  margin-bottom: 6px; padding-left: 4px;
}

.history-row {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 4px; border-radius: 5px;
  transition: background 0.12s;
}
.history-row:hover { background: var(--surface-2); }
.history-row:hover .delete-btn { opacity: 1; }

.read-time {
  font-size: 12px; color: var(--text-3);
  width: 42px; flex-shrink: 0; font-variant-numeric: tabular-nums;
}
.history-title {
  flex: 1; min-width: 0;
  font-size: 14px; color: var(--text-1);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  cursor: pointer; transition: color 0.12s;
}
.history-title:hover { color: var(--accent); }

.delete-btn  { opacity: 0; transition: opacity 0.15s; flex-shrink: 0; }

.pagination  { display: flex; justify-content: center; margin-top: 24px; padding-bottom: 40px; }
</style>
