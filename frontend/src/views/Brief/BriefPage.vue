<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useBriefStore } from '@/stores/briefStore'

const router = useRouter()
const brief  = useBriefStore()

// 首次进入时加载（已缓存则直接用，不重复请求）
onMounted(() => brief.load())
</script>

<template>
  <div class="brief-page">
    <div class="page-header">
      <n-button size="small" @click="router.push('/articles')">查看全部文章 →</n-button>

      <!-- 右上角手动刷新按钮 -->
      <n-button
        size="small"
        :loading="brief.loading"
        :disabled="brief.loading"
        @click="brief.refresh()"
      >
        🔄 刷新简报
      </n-button>
    </div>

    <n-spin :show="brief.loading" style="margin-top: 24px">
      <n-alert v-if="brief.error" type="error" style="margin-top: 24px">
        简报加载失败，请检查后端服务是否运行。
      </n-alert>

      <div v-else-if="!brief.loading && brief.loaded" class="markdown-body" v-html="brief.html" />

      <!-- 首次未加载且无错误时的占位（理论上 onMounted 已触发 load） -->
      <n-empty v-else-if="!brief.loading && !brief.loaded" description="暂无简报内容" style="margin-top: 40px" />
    </n-spin>
  </div>
</template>

<style scoped>
.brief-page  { max-width: 800px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
</style>

<style>
/* markdown 渲染样式（不 scoped，因为 v-html 内部元素不受 scoped 影响） */
.markdown-body { line-height: 1.8; font-size: 15px; margin-top: 20px; }
.markdown-body h1 { font-size: 22px; margin: 0 0 16px; }
.markdown-body h2 { font-size: 17px; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid rgba(128,128,128,0.2); }
.markdown-body ul { padding-left: 20px; margin: 8px 0; }
.markdown-body li { margin: 6px 0; }
.markdown-body a  { color: #2080f0; text-decoration: none; }
.markdown-body a:hover { text-decoration: underline; }
.markdown-body blockquote { margin: 8px 0; padding: 6px 14px; border-left: 3px solid #2080f0; color: #888; background: rgba(32,128,240,0.04); border-radius: 2px; }
.markdown-body strong { font-weight: 600; }
</style>
