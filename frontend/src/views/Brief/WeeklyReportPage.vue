<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { use }                 from 'echarts/core'
import { BarChart, PieChart }  from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import { CanvasRenderer }    from 'echarts/renderers'
import VChart                from 'vue-echarts'
import { useWeeklyReportStore } from '@/stores/weeklyReportStore'
import type { TrendItem }       from '@/types/report'

// 注册 ECharts 模块
use([BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer])

const report = useWeeklyReportStore()

// 首次进入：有缓存直接展示，无缓存则请求
onMounted(() => report.load())

// ── 趋势箭头 ─────────────────────────────────────────────────────────────────
function trendIcon(item: TrendItem): string {
  if (item.direction === 'up_strong') return '↑↑'
  if (item.direction === 'up')        return '↑'
  if (item.direction === 'down')      return '↓'
  return '→'
}
function trendClass(item: TrendItem): string {
  if (item.direction === 'up_strong' || item.direction === 'up') return 'trend-up'
  if (item.direction === 'down') return 'trend-down'
  return 'trend-stable'
}
function changeLabel(change: number): string {
  if (change > 0) return `+${change}`
  return String(change)
}

// ── 难度估算 ─────────────────────────────────────────────────────────────────
function difficultyLabel(minutes: number): string {
  if (minutes <= 5)  return '入门'
  if (minutes <= 15) return '进阶'
  return '硬核'
}
function difficultyType(minutes: number): 'success' | 'warning' | 'error' {
  if (minutes <= 5)  return 'success'
  if (minutes <= 15) return 'warning'
  return 'error'
}

// ── ECharts：每日阅读量柱状图 ─────────────────────────────────────────────────
const dailyReadsOption = computed(() => {
  const d = report.data
  if (!d?.daily_reads?.length) return {}
  return {
    tooltip: { trigger: 'axis', formatter: (p: any) => `${p[0].name}<br/>已读 ${p[0].value} 篇` },
    grid:    { left: 40, right: 16, top: 16, bottom: 30 },
    xAxis: {
      type: 'category',
      data: d.daily_reads.map(r => r.date),
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { fontSize: 11 } },
    series: [{
      type: 'bar',
      data: d.daily_reads.map(r => r.count),
      itemStyle: { color: '#2080f0', borderRadius: [3, 3, 0, 0] },
      barMaxWidth: 32,
    }],
  }
})

// ── ECharts：兴趣分布饼图 ─────────────────────────────────────────────────────
const tagDistOption = computed(() => {
  const d = report.data
  if (!d?.tag_distribution?.length) return {}
  const palette = ['#2080f0', '#18a058', '#f0a020', '#d03050', '#8058f0',
                   '#0ea5e9', '#f97316', '#84cc16', '#ec4899', '#14b8a6']
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}篇 ({d}%)' },
    legend: { orient: 'vertical', right: 8, top: 'center', textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['38%', '50%'],
      data: d.tag_distribution.slice(0, 8).map((t, i) => ({
        name:  t.tag,
        value: t.count,
        itemStyle: { color: palette[i % palette.length] },
      })),
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
    }],
  }
})

// ── 复制为 Markdown ───────────────────────────────────────────────────────────
function copyAsMarkdown() {
  const d = report.data
  if (!d) return
  const lines: string[] = [
    `# 📊 AI 周报  ${d.period}`,
    '',
    `> 本周新增 **${d.overview.total_articles}** 篇 · 已读 **${d.overview.read_count}** 篇 · 预计 **${d.overview.read_minutes}** 分钟 · **${d.overview.knowledge_points}** 个知识点`,
    '',
    '## 🔥 本周热点',
    ...d.top_trends.map(t => `- ${trendIcon(t)} **${t.tag}** ${t.count}篇 (${changeLabel(t.change)}) — ${t.summary}`),
    '',
    '## 📚 精选文章',
    ...d.curated_articles.map(a => `- [${a.title}](${a.url})\n  ${a.summary}\n  ${a.tags.map(t => `#${t}`).join(' ')}`),
    '',
    '## 💡 洞见摘录',
    ...d.insights.map(i => `> **${i.title}**\n> ${i.insight}`),
    '',
    '## ✅ 行动清单',
    ...d.action_items.map((a, idx) => `${idx + 1}. **${a.title}**（${a.time_estimate}）\n   ${a.detail}`),
    '',
    '## 👀 下周关注',
    ...d.next_week_focus.map(f => `- ${f}`),
  ]
  navigator.clipboard.writeText(lines.join('\n'))
}

// ── 下载 Markdown ─────────────────────────────────────────────────────────────
function downloadMd() {
  const d = report.data
  if (!d) return
  const lines: string[] = [
    `# 📊 AI 周报  ${d.period}`,
    '',
    `> 本周新增 **${d.overview.total_articles}** 篇 · 已读 **${d.overview.read_count}** 篇 · 预计 **${d.overview.read_minutes}** 分钟 · **${d.overview.knowledge_points}** 个知识点`,
    '',
    '## 🔥 本周热点',
    ...d.top_trends.map(t => `- ${trendIcon(t)} **${t.tag}** ${t.count}篇 (${changeLabel(t.change)}) — ${t.summary}`),
    '',
    '## 📚 精选文章',
    ...d.curated_articles.map(a => `- [${a.title}](${a.url})\n  > ${a.summary}`),
    '',
    '## 💡 洞见摘录',
    ...d.insights.map(i => `> **${i.title}**\n> ${i.insight}`),
    '',
    '## ✅ 行动清单',
    ...d.action_items.map((a, idx) => `${idx + 1}. **${a.title}**（${a.time_estimate}）\n   ${a.detail}`),
    '',
    '## 👀 下周关注',
    ...d.next_week_focus.map(f => `- ${f}`),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = `weekly-report-${new Date().toISOString().slice(0, 10)}.md`
  a.click()
}
</script>

<template>
  <div class="report-page">

    <!-- ── 页头 ─────────────────────────────────────────────────────────────── -->
    <div class="page-header">
      <div class="header-title">
        <span class="header-emoji">📊</span>
        <div>
          <h2 style="margin:0;font-size:18px">AI 周报</h2>
          <span v-if="report.data" class="period-text">{{ report.data.period }}</span>
        </div>
      </div>
      <div class="header-actions">
        <n-button size="small" :disabled="!report.data" @click="copyAsMarkdown">📋 复制 Markdown</n-button>
        <n-button size="small" :disabled="!report.data" @click="downloadMd">⬇ 下载</n-button>
        <n-button size="small" :loading="report.loading" :disabled="report.loading" @click="report.refresh()">
          🔄 刷新周报
        </n-button>
      </div>
    </div>

    <!-- ── 加载 / 错误状态 ────────────────────────────────────────────────── -->
    <n-spin :show="report.loading" style="margin-top:24px;min-height:300px">
      <n-alert v-if="report.error" type="error" style="margin-top:24px">
        周报加载失败，请检查后端服务是否运行。
      </n-alert>

      <template v-else-if="report.data">

        <!-- ── 第一行：概览 + 每日阅读趋势 ──────────────────────────────── -->
        <div class="row-2col" style="margin-top:20px">

          <!-- 概览卡片组 -->
          <n-card title="📋 本周概览" size="small" class="card-flex">
            <div class="overview-grid">
              <div class="overview-item">
                <div class="ov-value">{{ report.data.overview.total_articles }}</div>
                <div class="ov-label">新增文章</div>
              </div>
              <div class="overview-item">
                <div class="ov-value">{{ report.data.overview.read_count }}</div>
                <div class="ov-label">已读文章</div>
              </div>
              <div class="overview-item">
                <div class="ov-value">{{ report.data.overview.read_minutes }}<span class="ov-unit">min</span></div>
                <div class="ov-label">阅读时长</div>
              </div>
              <div class="overview-item">
                <div class="ov-value">{{ report.data.overview.knowledge_points }}</div>
                <div class="ov-label">知识点</div>
              </div>
            </div>
          </n-card>

          <!-- 每日阅读柱状图 -->
          <n-card title="📅 阅读趋势（本周已读）" size="small" class="card-flex">
            <VChart v-if="dailyReadsOption.series" :option="dailyReadsOption" style="height:140px" autoresize />
            <n-empty v-else description="暂无数据" style="height:140px;display:flex;align-items:center;justify-content:center" />
          </n-card>
        </div>

        <!-- ── 第二行：热点 Top 5 ────────────────────────────────────────── -->
        <n-card title="🔥 本周热点 Top 5" size="small" style="margin-top:16px">
          <div v-if="report.data.top_trends.length" class="trends-list">
            <div v-for="(item, idx) in report.data.top_trends" :key="item.tag" class="trend-item">
              <span class="trend-rank">{{ idx + 1 }}</span>
              <span :class="['trend-arrow', trendClass(item)]">{{ trendIcon(item) }}</span>
              <span class="trend-tag">{{ item.tag }}</span>
              <n-tag size="small" :bordered="false" style="margin-left:6px;font-size:11px">
                {{ item.count }}篇
              </n-tag>
              <n-tag
                size="small"
                :bordered="false"
                :type="item.direction.startsWith('up') ? 'success' : item.direction === 'down' ? 'error' : 'default'"
                style="margin-left:4px;font-size:11px"
              >
                {{ changeLabel(item.change) }}
              </n-tag>
              <span class="trend-summary">{{ item.summary }}</span>
            </div>
          </div>
          <n-empty v-else description="本周暂无热点数据" />
        </n-card>

        <!-- ── 第三行：精选文章 ────────────────────────────────────────────── -->
        <n-card title="📚 为你精选" size="small" style="margin-top:16px">
          <div class="articles-grid">
            <div v-for="article in report.data.curated_articles" :key="article.id" class="article-card">
              <a :href="article.url" target="_blank" rel="noopener" class="article-title">
                {{ article.title }}
              </a>
              <p class="article-summary">{{ article.summary }}</p>
              <div class="article-footer">
                <div class="article-tags">
                  <n-tag v-for="tag in article.tags.slice(0, 3)" :key="tag"
                         size="small" :bordered="false" style="font-size:11px;margin-right:4px">
                    #{{ tag }}
                  </n-tag>
                </div>
                <div class="article-meta">
                  <n-tag size="small" :type="difficultyType(article.read_minutes)" :bordered="false" style="font-size:11px">
                    {{ difficultyLabel(article.read_minutes) }}
                  </n-tag>
                  <span class="read-time">⏱ {{ article.read_minutes }}min</span>
                  <span class="score-badge">{{ article.score }}%</span>
                </div>
              </div>
            </div>
          </div>
        </n-card>

        <!-- ── 第四行：洞见 + 行动清单 ───────────────────────────────────── -->
        <div class="row-2col" style="margin-top:16px">

          <!-- 洞见摘录 -->
          <n-card title="💡 本周洞见" size="small" class="card-flex">
            <div v-if="report.data.insights.length" class="insights-list">
              <div v-for="item in report.data.insights" :key="item.url" class="insight-item">
                <a :href="item.url" target="_blank" rel="noopener" class="insight-title">
                  {{ item.title }}
                </a>
                <p class="insight-text">{{ item.insight }}</p>
              </div>
            </div>
            <n-empty v-else description="暂无洞见内容" />
          </n-card>

          <!-- 行动清单 -->
          <n-card title="✅ 学习建议 & 行动清单" size="small" class="card-flex">
            <div v-if="report.data.action_items.length" class="actions-list">
              <div v-for="(item, idx) in report.data.action_items" :key="idx" class="action-item">
                <div class="action-header">
                  <span class="action-index">{{ idx + 1 }}</span>
                  <span class="action-title">{{ item.title }}</span>
                  <n-tag size="small" :bordered="false" type="info" style="font-size:11px;margin-left:auto">
                    {{ item.time_estimate }}
                  </n-tag>
                </div>
                <p class="action-detail">{{ item.detail }}</p>
                <a v-if="item.reference_url" :href="item.reference_url"
                   target="_blank" rel="noopener" class="action-ref">
                  → 参考文章
                </a>
              </div>
            </div>
          </n-card>
        </div>

        <!-- ── 第五行：下周关注 + 兴趣分布 ───────────────────────────────── -->
        <div class="row-2col" style="margin-top:16px">

          <!-- 下周关注 -->
          <n-card title="👀 下周关注 & 潜在机会" size="small" class="card-flex">
            <ul class="focus-list">
              <li v-for="(focus, idx) in report.data.next_week_focus" :key="idx" class="focus-item">
                {{ focus }}
              </li>
            </ul>
          </n-card>

          <!-- 兴趣分布饼图 -->
          <n-card title="🎯 兴趣分布" size="small" class="card-flex">
            <VChart v-if="tagDistOption.series" :option="tagDistOption" style="height:200px" autoresize />
            <n-empty v-else description="暂无数据" style="height:200px;display:flex;align-items:center;justify-content:center" />
          </n-card>
        </div>

      </template>

      <n-empty v-else-if="!report.loading && !report.loaded"
               description="暂无周报内容，点击右上角「刷新周报」生成"
               style="margin-top:60px" />
    </n-spin>
  </div>
</template>

<style scoped>
/* ── 页面容器 ────────────────────────────────────────────────────────────── */
.report-page { max-width: 960px; margin: 0 auto; padding-bottom: 48px; }

/* ── 页头 ──────────────────────────────────────────────────────────────── */
.page-header   { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.header-title  { display: flex; align-items: center; gap: 10px; }
.header-emoji  { font-size: 28px; }
.period-text   { font-size: 12px; color: var(--text-3); }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }

/* ── 双列布局 ────────────────────────────────────────────────────────────── */
.row-2col   { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.card-flex  { min-height: 180px; }
@media (max-width: 680px) {
  .row-2col { grid-template-columns: 1fr; }
}

/* ── 概览 ────────────────────────────────────────────────────────────────── */
.overview-grid  { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 8px 0; }
.overview-item  { text-align: center; }
.ov-value       { font-size: 28px; font-weight: 700; color: var(--accent); line-height: 1; }
.ov-unit        { font-size: 14px; font-weight: 400; margin-left: 2px; }
.ov-label       { font-size: 12px; color: var(--text-3); margin-top: 4px; }

/* ── 热点趋势 ────────────────────────────────────────────────────────────── */
.trends-list  { display: flex; flex-direction: column; gap: 10px; }
.trend-item   { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
.trend-rank   { width: 18px; font-size: 12px; color: var(--text-3); flex-shrink: 0; }
.trend-arrow  { font-size: 15px; font-weight: 700; width: 22px; flex-shrink: 0; }
.trend-up     { color: #18a058; }
.trend-down   { color: #d03050; }
.trend-stable { color: var(--text-3); }
.trend-tag    { font-weight: 600; font-size: 14px; }
.trend-summary { font-size: 13px; color: var(--text-2); flex: 1; min-width: 160px; }

/* ── 精选文章 ────────────────────────────────────────────────────────────── */
.articles-grid  { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.article-card   {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.article-card:hover { border-color: var(--accent); box-shadow: 0 2px 8px rgba(32,128,240,0.1); }
.article-title  { font-size: 13.5px; font-weight: 600; color: var(--accent); text-decoration: none; line-height: 1.4; }
.article-title:hover { text-decoration: underline; }
.article-summary { font-size: 12.5px; color: var(--text-2); line-height: 1.6; margin: 0;
                   display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.article-footer { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px; margin-top: auto; }
.article-tags   { display: flex; flex-wrap: wrap; gap: 3px; }
.article-meta   { display: flex; align-items: center; gap: 6px; }
.read-time      { font-size: 11px; color: var(--text-3); }
.score-badge    { font-size: 11px; font-weight: 600; color: var(--accent); }

/* ── 洞见 ────────────────────────────────────────────────────────────────── */
.insights-list  { display: flex; flex-direction: column; gap: 14px; }
.insight-item   { border-left: 3px solid var(--accent); padding-left: 10px; }
.insight-title  { font-size: 13px; font-weight: 600; color: var(--accent); text-decoration: none; }
.insight-title:hover { text-decoration: underline; }
.insight-text   { font-size: 12.5px; color: var(--text-2); margin: 4px 0 0; line-height: 1.6;
                  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }

/* ── 行动清单 ────────────────────────────────────────────────────────────── */
.actions-list   { display: flex; flex-direction: column; gap: 14px; }
.action-item    { background: var(--surface-2); border-radius: 8px; padding: 10px 12px; }
.action-header  { display: flex; align-items: center; gap: 8px; }
.action-index   { width: 20px; height: 20px; border-radius: 50%; background: var(--accent);
                  color: #fff; font-size: 11px; font-weight: 700;
                  display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.action-title   { font-weight: 600; font-size: 13.5px; }
.action-detail  { font-size: 12.5px; color: var(--text-2); margin: 6px 0 0; line-height: 1.6; }
.action-ref     { font-size: 12px; color: var(--accent); text-decoration: none; display: inline-block; margin-top: 4px; }
.action-ref:hover { text-decoration: underline; }

/* ── 下周关注 ────────────────────────────────────────────────────────────── */
.focus-list  { padding-left: 0; list-style: none; display: flex; flex-direction: column; gap: 10px; }
.focus-item  {
  font-size: 13.5px;
  padding: 8px 12px;
  border-radius: 6px;
  background: var(--surface-2);
  border-left: 3px solid var(--accent);
}
</style>
