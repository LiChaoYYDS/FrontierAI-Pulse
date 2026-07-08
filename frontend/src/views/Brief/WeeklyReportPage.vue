<script setup lang="ts">
import { onMounted } from 'vue'
import { useWeeklyReportStore } from '@/stores/weeklyReportStore'

const report = useWeeklyReportStore()

// 首次进入时加载（已缓存则直接展示，不重复请求）
onMounted(() => report.load())

function downloadMd() {
  const blob = new Blob([report.rawContent], { type: 'text/markdown' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = `weekly-report-${new Date().toISOString().slice(0, 10)}.md`
  a.click()
}

function downloadHtml() {
  const htmlDoc = `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>AI 周报</title>
<style>body{max-width:800px;margin:40px auto;font-family:sans-serif;line-height:1.8;padding:0 20px}
h1{font-size:22px}h2{font-size:17px;border-bottom:1px solid #eee;padding-bottom:6px}
a{color:#2080f0}ul{padding-left:20px}li{margin:6px 0}
blockquote{margin:8px 0;padding:6px 14px;border-left:3px solid #2080f0;color:#888;background:#f0f7ff}
</style></head><body>${report.html}</body></html>`
  const blob = new Blob([htmlDoc], { type: 'text/html' })
  const a    = document.createElement('a')
  a.href     = URL.createObjectURL(blob)
  a.download = `weekly-report-${new Date().toISOString().slice(0, 10)}.html`
  a.click()
}
</script>

<template>
  <div class="report-page">
    <!-- 页头：标题 + 操作按钮 -->
    <div class="page-header">
      <h2 style="margin: 0">📊 AI 周报</h2>
      <div class="header-actions">
        <n-button
          size="small"
          :disabled="!report.rawContent"
          @click="downloadMd"
        >⬇ 下载 Markdown</n-button>
        <n-button
          size="small"
          :disabled="!report.rawContent"
          @click="downloadHtml"
        >⬇ 下载 HTML</n-button>
        <n-button
          size="small"
          :loading="report.loading"
          :disabled="report.loading"
          @click="report.refresh()"
        >🔄 刷新周报</n-button>
      </div>
    </div>

    <n-spin :show="report.loading" style="margin-top: 24px; min-height: 200px">
      <n-alert v-if="report.error" type="error" style="margin-top: 24px">
        周报加载失败，请检查后端服务是否运行。
      </n-alert>

      <div v-else-if="!report.loading && report.loaded"
           class="markdown-body"
           v-html="report.html"
      />

      <n-empty v-else-if="!report.loading && !report.loaded"
               description="暂无周报内容"
               style="margin-top: 40px"
      />
    </n-spin>
  </div>
</template>

<style scoped>
.report-page   { max-width: 800px; margin: 0 auto; padding-bottom: 48px; }
.page-header   { display: flex; justify-content: space-between; align-items: center; }
.header-actions { display: flex; gap: 8px; align-items: center; }
</style>

<style>
/* markdown 渲染样式（不 scoped，v-html 内部元素不受 scoped 影响） */
.markdown-body { margin-top: 20px; line-height: 1.8; font-size: 15px; }
.markdown-body h1 { font-size: 22px; margin: 0 0 16px; }
.markdown-body h2 { font-size: 17px; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid rgba(128,128,128,0.2); }
.markdown-body ul { padding-left: 20px; margin: 8px 0; }
.markdown-body li { margin: 6px 0; }
.markdown-body a  { color: #2080f0; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body strong { font-weight: 600; }
.markdown-body blockquote { margin: 8px 0; padding: 6px 14px; border-left: 3px solid #2080f0; color: #888; background: rgba(32,128,240,0.04); border-radius: 2px; }
</style>
