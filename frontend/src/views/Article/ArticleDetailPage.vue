<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import * as api from '@/api'
import type { Article } from '@/types/article'
import type { CloneTask } from '@/api'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const article = ref<Article | null>(null)
const loading = ref(true)
const processing = ref(false)
const savingNotes = ref(false)
const notesText = ref('')

const id = Number(route.params.id)

// ── Git Clone ──────────────────────────────────────────────────────────────────
const GITHUB_REPO = /^https?:\/\/github\.com\/([^/]+)\/([^/]+?)(?:\.git)?\/?$/
const isGithubRepo = computed(() => article.value ? GITHUB_REPO.test(article.value.url) : false)

const showCloneModal = ref(false)
const cloneUsername = ref('')
const cloneToken = ref('')
const cloneTask = ref<api.CloneTask | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function startClone() {
  if (!article.value) return
  cloneTask.value = { status: 'running', progress: 0, message: '正在启动...' }
  try {
    const task = await api.startClone(article.value.url, cloneUsername.value, cloneToken.value)
    if (task.error) { message.error(task.error); cloneTask.value = null; return }
    cloneTask.value = task
    pollTimer = setInterval(async () => {
      if (!cloneTask.value?.task_id) return
      const status = await api.getCloneStatus(cloneTask.value.task_id)
      cloneTask.value = status
      if (status.status === 'done' || status.status === 'failed') {
        clearInterval(pollTimer!); pollTimer = null
        if (status.status === 'done') message.success(`克隆完成！保存到 ${status.target}`)
        else message.error(status.message)
      }
    }, 1000)
  } catch (e: any) {
    cloneTask.value = null
    message.error('启动失败：' + (e?.message ?? ''))
  }
}

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })

onMounted(async () => {
  try {
    article.value = await api.getArticle(id)
    notesText.value = article.value.notes || ''
    if (!article.value.is_read) {
      article.value = await api.updateArticle(id, { is_read: true })
    }
  } catch {
    message.error('文章不存在')
    router.push('/articles')
  } finally {
    loading.value = false
  }
})

async function toggle(field: 'is_read' | 'is_favorite' | 'is_liked') {
  if (!article.value) return
  const updated = await api.updateArticle(id, { [field]: !article.value[field] })
  article.value = updated
}

async function saveNotes() {
  if (!article.value) return
  savingNotes.value = true
  try {
    const updated = await api.updateArticle(id, { notes: notesText.value || null })
    article.value = updated
    message.success('笔记已保存')
  } finally {
    savingNotes.value = false
  }
}

async function triggerProcess() {
  processing.value = true
  try {
    await api.processArticle(id)
    article.value = await api.getArticle(id)
    message.success('AI 处理完成')
  } catch {
    message.error('处理失败')
  } finally {
    processing.value = false
  }
}

function scoreColor(score: number) {
  if (score >= 80) return '#d03050'
  if (score >= 60) return '#f0a020'
  return '#2080f0'
}
</script>

<template>
  <div class="detail-page">
    <n-spin :show="loading">
      <template v-if="article">
        <!-- 顶部操作栏 -->
        <div class="top-bar">
          <n-button text @click="router.back()">← 返回</n-button>
          <n-space>
            <n-button size="small" :type="article.is_read ? 'default' : 'primary'"
              @click="toggle('is_read')">
              {{ article.is_read ? '已读' : '标记已读' }}
            </n-button>
            <n-button size="small" :type="article.is_favorite ? 'warning' : 'default'"
              @click="toggle('is_favorite')">
              {{ article.is_favorite ? '⭐ 已收藏' : '☆ 收藏' }}
            </n-button>
            <n-button size="small" :type="article.is_liked ? 'primary' : 'default'"
              @click="toggle('is_liked')">
              {{ article.is_liked ? '👍 已点赞' : '👍🏻 点赞' }}
            </n-button>
            <n-button size="small" tag="a" :href="article.url" target="_blank">原文链接 ↗</n-button>
            <!-- GitHub项目克隆按钮（仅GitHub仓库URL显示） -->
            <n-button v-if="isGithubRepo" size="small" type="success"
              @click="showCloneModal = true; cloneTask = null">
              ⬇ 克隆到本地
            </n-button>
          </n-space>
        </div>

        <!-- 标题 -->
        <h1 class="title">{{ article.title }}</h1>

        <!-- 元信息 -->
        <div class="meta">
          <n-tag size="small" :bordered="false">{{ article.source_type || '未知来源' }}</n-tag>
          <span v-if="article.published_at" class="meta-time">
            {{ new Date(article.published_at).toLocaleDateString('zh-CN') }}
          </span>
          <n-tag size="small" :type="article.process_status === 'done' ? 'success' : 'default'">
            {{ article.process_status === 'done' ? 'AI已处理' : article.process_status === 'processing' ? '处理中' : '待处理' }}
          </n-tag>
        </div>

        <!-- 评分 + AI处理按钮 -->
        <div class="score-row">
          <div v-if="article.importance_score > 0" class="score-block">
            <n-progress type="circle" :percentage="article.importance_score" :color="scoreColor(article.importance_score)"
              :rail-color="scoreColor(article.importance_score) + '30'" style="width: 64px">
              <span style="font-size: 14px; font-weight: 600">{{ article.importance_score }}</span>
            </n-progress>
            <span style="font-size: 13px; color: #888; margin-top: 4px">相关度评分</span>
          </div>
          <n-button v-if="article.process_status !== 'done'" size="small" type="primary"
            :loading="processing" @click="triggerProcess">
            🤖 AI 处理
          </n-button>
        </div>

        <!-- AI 摘要 -->
        <n-card v-if="article.summary" title="📝 AI 摘要" :bordered="true" style="margin-top: 20px">
          <p style="margin: 0; line-height: 1.8">{{ article.summary }}</p>
        </n-card>

        <!-- 正文 -->
        <n-card v-if="article.content" title="📄 正文" :bordered="true" style="margin-top: 16px">
          <p style="margin: 0; line-height: 1.9; white-space: pre-wrap; font-size: 14px">{{ article.content }}</p>
        </n-card>

        <!-- 标签 -->
        <div v-if="(article.tags ?? []).length > 0" style="margin-top: 16px">
          <n-space size="small">
            <n-tag v-for="tag in article.tags" :key="tag" size="small">{{ tag }}</n-tag>
          </n-space>
        </div>

        <!-- AI 洞察 -->
        <n-card v-if="article.insight" title="💡 个人关联洞察" :bordered="true" style="margin-top: 16px">
          <p style="margin: 0; line-height: 1.8; color: #555">{{ article.insight }}</p>
        </n-card>

        <!-- 个人笔记 -->
        <n-card title="✏️ 个人笔记" :bordered="true" style="margin-top: 16px">
          <n-input v-model:value="notesText" type="textarea" :rows="4"
            placeholder="记录你的想法..." style="margin-bottom: 8px" />
          <n-button size="small" type="primary" :loading="savingNotes" @click="saveNotes">
            保存笔记
          </n-button>
        </n-card>
      </template>
    </n-spin>

    <!-- Git 克隆弹窗 -->
    <n-modal v-model:show="showCloneModal" preset="card" title="⬇ 克隆项目到本地"
      style="max-width: 480px; width: 90vw">
      <div v-if="!cloneTask || cloneTask.status === 'idle'">
        <p style="color: #888; font-size: 13px; margin: 0 0 16px">
          仓库：<code>{{ article?.url }}</code>
        </p>
        <n-form-item label="GitHub 用户名（私有仓库必填）">
          <n-input v-model:value="cloneUsername" placeholder="your-username" clearable />
        </n-form-item>
        <n-form-item label="Personal Access Token（私有仓库必填）">
          <n-input v-model:value="cloneToken" type="password" placeholder="ghp_xxxx" clearable show-password-on="click" />
        </n-form-item>
        <p style="font-size: 12px; color: #aaa">
          保存路径：Documents/github-projects/{{ article?.url.split('/').slice(-1)[0] }}
        </p>
      </div>

      <!-- 克隆进度 -->
      <div v-else style="padding: 8px 0">
        <div style="margin-bottom: 12px; font-size: 13px">
          <n-tag :type="cloneTask.status === 'done' ? 'success' : cloneTask.status === 'failed' ? 'error' : 'info'" size="small">
            {{ cloneTask.status === 'done' ? '完成' : cloneTask.status === 'failed' ? '失败' : '进行中' }}
          </n-tag>
          <span style="margin-left: 8px; color: #888">{{ cloneTask.message }}</span>
        </div>
        <n-progress
          :percentage="cloneTask.progress"
          :status="cloneTask.status === 'done' ? 'success' : cloneTask.status === 'failed' ? 'error' : 'default'"
          :processing="cloneTask.status === 'running'"
        />
        <p v-if="cloneTask.target && cloneTask.status === 'done'" style="font-size: 12px; color: #18a058; margin-top: 8px">
          ✓ 已保存到：{{ cloneTask.target }}
        </p>
      </div>

      <template #footer>
        <n-space justify="end">
          <n-button @click="showCloneModal = false">关闭</n-button>
          <n-button v-if="!cloneTask || cloneTask.status === 'idle'" type="primary"
            @click="startClone">开始克隆</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.detail-page { max-width: 800px; margin: 0 auto; padding-bottom: 48px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.title { font-size: 22px; font-weight: 700; line-height: 1.4; margin: 0 0 12px; }
.meta { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.meta-time { font-size: 13px; color: #888; }
.score-row { display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }
.score-block { display: flex; flex-direction: column; align-items: center; }
</style>
