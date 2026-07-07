<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import * as api from '@/api'

const router = useRouter()
const html = ref('')
const rawContent = ref('')
const loading = ref(true)

marked.use({ renderer: { link(token) { return `<a href="${token.href}" target="_blank" rel="noopener">${token.text}</a>` } } })

onMounted(async () => {
  try {
    const res = await api.getWeeklyReport()
    rawContent.value = res.content
    html.value = await marked(res.content)
  } finally {
    loading.value = false
  }
})

function downloadMd() {
  const blob = new Blob([rawContent.value], { type: 'text/markdown' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `weekly-report-${new Date().toISOString().slice(0,10)}.md`
  a.click()
}

function downloadHtml() {
  const htmlDoc = `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>AI 周报</title>
<style>body{max-width:800px;margin:40px auto;font-family:sans-serif;line-height:1.8;padding:0 20px}
h1{font-size:22px}h2{font-size:17px;border-bottom:1px solid #eee;padding-bottom:6px}
a{color:#2080f0}ul{padding-left:20px}li{margin:6px 0}
blockquote{margin:8px 0;padding:6px 14px;border-left:3px solid #2080f0;color:#888;background:#f0f7ff}</style>
</head><body>${html.value}</body></html>`
  const blob = new Blob([htmlDoc], { type: 'text/html' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `weekly-report-${new Date().toISOString().slice(0,10)}.html`
  a.click()
}
</script>

<template>
  <div class="report-page">
    <div class="page-header">
      <n-button text @click="router.back()">← 返回</n-button>
      <h2 style="margin: 0">📊 AI 周报</h2>
      <n-button size="small" :disabled="!rawContent" @click="downloadMd">⬇ 下载 Markdown</n-button>
      <n-button size="small" :disabled="!rawContent" @click="downloadHtml">⬇ 下载 HTML</n-button>
    </div>

    <n-spin :show="loading" style="margin-top: 24px; min-height: 200px">
      <div v-if="!loading" class="markdown-body" v-html="html" />
    </n-spin>
  </div>
</template>

<style scoped>
.report-page { max-width: 800px; margin: 0 auto; padding-bottom: 48px; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
</style>

<style>
.markdown-body { margin-top: 20px; line-height: 1.8; font-size: 15px; }
.markdown-body h1 { font-size: 22px; margin: 0 0 16px; }
.markdown-body h2 { font-size: 17px; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid rgba(128,128,128,0.2); }
.markdown-body ul { padding-left: 20px; margin: 8px 0; }
.markdown-body li { margin: 6px 0; }
.markdown-body a { color: #2080f0; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body strong { font-weight: 600; }
.markdown-body blockquote { margin: 8px 0; padding: 6px 14px; border-left: 3px solid #2080f0; color: #888; background: rgba(32,128,240,0.04); border-radius: 2px; }
</style>
