<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '@/api'
import type { DashboardSummary } from '@/api'

const router = useRouter()
const summary = ref<DashboardSummary | null>(null)
const loading = ref(true)

const cards = [
  { key: 'total_articles', label: '总文章数',  icon: '📄', color: '#2080f0' },
  { key: 'today_new',      label: '今日新增',  icon: '🆕', color: '#18a058' },
  { key: 'read_count',     label: '已读文章',  icon: '✅', color: '#f0a020' },
  { key: 'favorite_count', label: '收藏文章',  icon: '⭐', color: '#d03050' },
  { key: 'active_sources', label: '活跃来源',  icon: '📡', color: '#8058f0' },
  { key: 'avg_score',      label: '平均匹配度', icon: '🎯', color: '#0ea5e9', suffix: '%' },
]

onMounted(async () => {
  try {
    summary.value = await api.getDashboardSummary()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2 style="margin: 0">📊 学习仪表盘</h2>
      <n-button type="primary" @click="router.push('/weekly-report')">
        📝 查看 AI 周报
      </n-button>
    </div>

    <n-spin :show="loading" style="margin-top: 24px; min-height: 180px">
      <div v-if="summary" class="cards-grid">
        <n-card v-for="card in cards" :key="card.key" size="small" class="stat-card">
          <div class="stat-icon">{{ card.icon }}</div>
          <div class="stat-value" :style="{ color: card.color }">
            {{ (summary as any)[card.key] ?? '-' }}{{ card.suffix ?? '' }}
          </div>
          <div class="stat-label">{{ card.label }}</div>
        </n-card>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.dashboard-page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
.cards-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat-card { text-align: center; }
.stat-icon { font-size: 24px; margin-bottom: 8px; }
.stat-value { font-size: 30px; font-weight: 700; line-height: 1; }
.stat-label { font-size: 12px; color: #888; margin-top: 8px; }
@media (max-width: 600px) {
  .cards-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
