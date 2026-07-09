<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { use }                from 'echarts/core'
import { LineChart, BarChart, FunnelChart, PieChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart            from 'vue-echarts'
import * as api          from '@/api'
import type { DashboardData } from '@/types/dashboard'

use([LineChart, BarChart, FunnelChart, PieChart,
     GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

const data    = ref<DashboardData | null>(null)
const loading = ref(true)
const days    = ref(30)

async function load() {
  loading.value = true
  try {
    data.value = await api.getDashboardSummary(days.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ── 总览卡片 ───────────────────────────────────────────────────────────────────
const overviewCards = computed(() => {
  const o = data.value?.overview
  if (!o) return []
  return [
    { label: '总文章数',   value: o.total_articles,        icon: '📄', color: '#2080f0' },
    { label: '今日新增',   value: o.today_new,              icon: '🆕', color: '#18a058' },
    { label: '活跃来源',   value: o.total_sources,          icon: '📡', color: '#8058f0' },
    { label: '知识节点',   value: o.total_knowledge_nodes,  icon: '🧠', color: '#f0a020' },
    { label: '标签种类',   value: o.total_unique_tags,      icon: '🏷', color: '#0ea5e9' },
    { label: '已读文章',   value: o.read_count,             icon: '✅', color: '#14b8a6' },
    { label: '收藏文章',   value: o.favorite_count,         icon: '⭐', color: '#d03050' },
  ]
})

// ── 内容增长趋势 ───────────────────────────────────────────────────────────────
const growthOption = computed(() => {
  const trend = data.value?.growth_trend
  if (!trend?.length) return {}
  return {
    tooltip: { trigger: 'axis' },
    grid:    { left: 40, right: 16, top: 16, bottom: 30 },
    xAxis:   { type: 'category', data: trend.map(d => d.date), axisLabel: { fontSize: 11 } },
    yAxis:   { type: 'value', minInterval: 1, axisLabel: { fontSize: 11 } },
    series: [{
      type: 'line', data: trend.map(d => d.count),
      smooth: true, areaStyle: { opacity: 0.15 },
      itemStyle: { color: '#2080f0' }, lineStyle: { color: '#2080f0', width: 2 },
    }],
  }
})

// ── 阅读漏斗 ──────────────────────────────────────────────────────────────────
const funnelOption = computed(() => {
  const f = data.value?.funnel
  if (!f) return {}
  const steps = [
    { name: '文章新增', value: f.total_articles },
    { name: 'AI 处理',  value: f.ai_processed   },
    { name: '用户已读', value: f.user_read       },
    { name: '用户收藏', value: f.user_favorite   },
    { name: '产生洞察', value: f.has_insight     },
  ]
  const palette = ['#2080f0', '#18a058', '#f0a020', '#d03050', '#8058f0']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 篇' },
    series: [{
      type: 'funnel', width: '55%', left: '5%', top: 8, bottom: 8,
      gap: 4, sort: 'descending',
      minSize: '8%',   // 最小宽度，保证小步骤仍可见
      label: {
        show: true,
        position: 'right',   // 标签显示在漏斗右侧，不被遮挡
        fontSize: 12,
        formatter: (p: any) => `${p.name}  ${p.value} 篇`,
      },
      labelLine: { length: 8, lineStyle: { width: 1 } },
      data: steps.map((s, i) => ({ ...s, itemStyle: { color: palette[i] } })),
    }],
  }
})

// ── 来源贡献排行 ───────────────────────────────────────────────────────────────
const sourceOption = computed(() => {
  const s = data.value?.top_sources
  if (!s?.length) return {}
  const names  = s.map(x => x.source_name).reverse()
  const counts = s.map(x => x.article_count).reverse()
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid:    { left: 88, right: 40, top: 8, bottom: 8 },
    xAxis:   { type: 'value', axisLabel: { fontSize: 11 } },
    yAxis:   { type: 'category', data: names, axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar', data: counts, barMaxWidth: 20,
      itemStyle: { color: '#2080f0', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right', fontSize: 11 },
    }],
  }
})

// ── 标签内容分布 ───────────────────────────────────────────────────────────────
const tagOption = computed(() => {
  const t = data.value?.tag_distribution
  if (!t?.length) return {}
  const palette = ['#2080f0', '#18a058', '#f0a020', '#d03050', '#8058f0',
                   '#0ea5e9', '#f97316', '#84cc16', '#ec4899', '#14b8a6']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}篇 ({d}%)' },
    legend:  { orient: 'vertical', right: 8, top: 'center', textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['38%', '66%'], center: ['38%', '50%'],
      data: t.map((x, i) => ({
        name: x.tag, value: x.count,
        itemStyle: { color: palette[i % palette.length] },
      })),
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
    }],
  }
})
</script>

<template>
  <div class="dashboard-page">

    <!-- 页头 -->
    <div class="page-header">
      <h2 style="margin:0">📊 学习仪表盘</h2>
      <n-space align="center">
        <!-- 趋势窗口切换 -->
        <n-radio-group v-model:value="days" size="small" @update:value="load">
          <n-radio-button :value="7">7天</n-radio-button>
          <n-radio-button :value="30">30天</n-radio-button>
          <n-radio-button :value="90">90天</n-radio-button>
        </n-radio-group>
      </n-space>
    </div>

    <n-spin :show="loading" style="margin-top:20px;min-height:300px">
      <template v-if="data">

        <!-- ① 数据总览 -->
        <div class="overview-grid">
          <n-card v-for="card in overviewCards" :key="card.label"
                  size="small" class="stat-card">
            <div class="stat-icon">{{ card.icon }}</div>
            <div class="stat-value" :style="{ color: card.color }">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </n-card>
        </div>

        <!-- ② 内容增长趋势 -->
        <n-card title="📈 内容增长趋势" size="small" style="margin-top:16px">
          <VChart v-if="growthOption.series" :option="growthOption"
                  style="height:180px" autoresize />
          <n-empty v-else description="暂无数据" style="height:180px;display:flex;align-items:center;justify-content:center"/>
        </n-card>

        <!-- ③ 阅读漏斗 + ④ AI 命中率 -->
        <div class="row-2col" style="margin-top:16px">

          <n-card title="🔽 阅读漏斗" size="small">
            <VChart v-if="funnelOption.series" :option="funnelOption"
                    style="height:220px" autoresize />
            <n-empty v-else description="暂无数据" style="height:220px;display:flex;align-items:center;justify-content:center"/>
          </n-card>

          <n-card title="🎯 AI 推荐命中率" size="small">
            <div class="accuracy-block">
              <div class="accuracy-item">
                <div class="accuracy-label">高分文章被读率
                  <span class="accuracy-hint">（评分≥80 的文章中，实际读了多少）</span>
                </div>
                <n-progress
                  type="line"
                  :percentage="data.ai_accuracy.read_rate"
                  :indicator-placement="'inside'"
                  :color="'#18a058'"
                  :rail-color="'rgba(24,160,88,0.15)'"
                  style="margin-top:8px"
                />
                <div class="accuracy-numbers">
                  {{ data.ai_accuracy.high_score_read }} / {{ data.ai_accuracy.high_score_total }} 篇
                  <strong style="color:#18a058;margin-left:6px">{{ data.ai_accuracy.read_rate }}%</strong>
                </div>
              </div>
              <div class="accuracy-item" style="margin-top:20px">
                <div class="accuracy-label">已读文章高分占比
                  <span class="accuracy-hint">（读过的文章中，AI 早就打了高分的占多少）</span>
                </div>
                <n-progress
                  type="line"
                  :percentage="data.ai_accuracy.quality_rate"
                  :indicator-placement="'inside'"
                  :color="'#2080f0'"
                  :rail-color="'rgba(32,128,240,0.15)'"
                  style="margin-top:8px"
                />
                <div class="accuracy-numbers">
                  {{ data.ai_accuracy.read_high_score }} / {{ data.ai_accuracy.read_total }} 篇
                  <strong style="color:#2080f0;margin-left:6px">{{ data.ai_accuracy.quality_rate }}%</strong>
                </div>
              </div>
            </div>
          </n-card>
        </div>

        <!-- ⑤ 来源排行 + ⑥ 标签分布 -->
        <div class="row-2col" style="margin-top:16px">

          <n-card title="📡 来源贡献排行 Top 10" size="small">
            <VChart v-if="sourceOption.series" :option="sourceOption"
                    style="height:260px" autoresize />
            <n-empty v-else description="暂无数据" style="height:260px;display:flex;align-items:center;justify-content:center"/>
          </n-card>

          <n-card title="🏷 内容标签分布 Top 10" size="small">
            <VChart v-if="tagOption.series" :option="tagOption"
                    style="height:260px" autoresize />
            <n-empty v-else description="暂无数据" style="height:260px;display:flex;align-items:center;justify-content:center"/>
          </n-card>
        </div>

      </template>
    </n-spin>
  </div>
</template>

<style scoped>
.dashboard-page { max-width: 960px; margin: 0 auto; padding-bottom: 48px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }

/* 总览网格 */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 10px;
  margin-top: 20px;
}
@media (max-width: 900px) { .overview-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 560px) { .overview-grid { grid-template-columns: repeat(2, 1fr); } }

.stat-card { text-align: center; }
.stat-icon  { font-size: 20px; margin-bottom: 6px; }
.stat-value { font-size: 24px; font-weight: 700; line-height: 1.1; }
.stat-label { font-size: 11px; color: var(--text-3); margin-top: 6px; }

/* 双列布局 */
.row-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 680px) { .row-2col { grid-template-columns: 1fr; } }

/* AI 命中率 */
.accuracy-block { padding: 8px 4px; }
.accuracy-item  { }
.accuracy-label {
  font-size: 13px; font-weight: 500;
  display: flex; flex-direction: column; gap: 2px;
}
.accuracy-hint  { font-size: 11px; color: var(--text-3); font-weight: 400; }
.accuracy-numbers { font-size: 12px; color: var(--text-2); margin-top: 4px; }
</style>
