<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import * as api from '@/api'
import type { KnowledgeNode } from '@/types/knowledge'
import type { AskResponse, EmbedStatus, ChatMsg } from '@/types/rag'
import type { Article } from '@/types/article'

const router = useRouter()
const message = useMessage()

const activeTab = ref<'chat' | 'browser'>('chat')

// ── RAG 对话 ───────────────────────────────────────────────────────────────────
const messages = ref<ChatMsg[]>([{
  role: 'assistant',
  content: '你好！我是你的个人知识助手（混合检索版）。\n\n你可以问我：\n• 我收藏过哪些 RAG 相关的文章？\n• 最近 AI Agent 有什么进展？\n• Transformer 是什么技术？',
}])
const inputText = ref('')
const chatLoading = ref(false)
const chatContainer = ref<HTMLElement>()

const LAYER_BADGE: Record<string, { type: 'info'|'success'|'warning', icon: string }> = {
  personal: { type: 'success', icon: '⭐' },
  curated:  { type: 'warning', icon: '🔥' },
  general:  { type: 'info',    icon: '📚' },
}

async function sendQuestion() {
  const q = inputText.value.trim()
  if (!q || chatLoading.value) return
  inputText.value = ''
  messages.value.push({ role: 'user', content: q })
  chatLoading.value = true
  await scrollToBottom()
  try {
    // 取最近6条历史（跳过第一条欢迎语）传给后端
    const history = messages.value
      .slice(1, -1)  // 去掉首条欢迎消息和刚加入的当前问题
      .slice(-6)     // 最多6条
      .map(m => ({ role: m.role, content: m.content }))

    const res: AskResponse = await api.askKnowledge(q, history)
    messages.value.push({
      role: 'assistant',
      content: res.answer,
      layer: res.layer,
      layer_desc: res.layer_desc,
      sources: res.sources,
    })
  } catch {
    messages.value.push({ role: 'assistant', content: '抱歉，查询失败，请稍后重试。' })
  } finally {
    chatLoading.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (chatContainer.value)
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
}

// ── Embedding 覆盖率 ────────────────────────────────────────────────────────────
const embedStatus = ref<EmbedStatus | null>(null)
const embedLoading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function loadEmbedStatus() {
  try { embedStatus.value = await api.getEmbedStatus() }
  catch { /* 静默失败 */ }
}

async function triggerEmbed() {
  embedLoading.value = true
  try {
    await api.triggerEmbedAll()
    message.success('向量化任务已启动，正在后台处理…')
    // 每 3 秒轮询一次进度，任务结束后停止
    pollTimer = setInterval(async () => {
      await loadEmbedStatus()
      if (embedStatus.value && !embedStatus.value.job_running) {
        clearInterval(pollTimer!)
        pollTimer = null
        message.success(`向量化完成！覆盖率 ${embedStatus.value.coverage_pct}%`)
      }
    }, 3000)
  } catch { message.error('启动失败') }
  finally { embedLoading.value = false }
}

// ── 概念浏览器 ─────────────────────────────────────────────────────────────────
const nodes = ref<KnowledgeNode[]>([])
const selectedNode = ref<KnowledgeNode | null>(null)
const nodeArticles = ref<Article[]>([])
const nodesLoading = ref(true)
const nodeArticlesLoading = ref(false)
const extracting = ref(false)

const TYPE_COLOR: Record<string, string> = {
  concept: '#2080f0', model: '#18a058', framework: '#f0a020', paper: '#d03050',
}
const TYPE_LABEL: Record<string, string> = {
  concept: '概念', model: '模型', framework: '框架', paper: '论文',
}

const grouped = computed(() => {
  const map: Record<string, KnowledgeNode[]> = {}
  for (const n of nodes.value) {
    if (!map[n.type]) map[n.type] = []
    map[n.type].push(n)
  }
  return map
})

async function loadNodes() {
  nodesLoading.value = true
  try { nodes.value = await api.getKnowledgeNodes() }
  finally { nodesLoading.value = false }
}

async function selectNode(node: KnowledgeNode) {
  selectedNode.value = node
  nodeArticlesLoading.value = true
  try { nodeArticles.value = await api.getNodeArticles(node.id) }
  finally { nodeArticlesLoading.value = false }
}

async function doExtract() {
  extracting.value = true
  try {
    const res = await api.extractKnowledge(50)
    message.success(`提取完成：处理 ${res.processed} 篇，新增 ${res.nodes_added} 个节点`)
    await loadNodes()
  } catch { message.error('提取失败') }
  finally { extracting.value = false }
}

function getTimeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const days = Math.floor((Date.now() - new Date(dateStr).getTime()) / 86400000)
  if (days < 1) return '今天'
  if (days < 7) return `${days} 天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadNodes()
  loadEmbedStatus()
})
</script>

<template>
  <div class="knowledge-page">
    <div class="page-header">
      <h2 style="margin: 0">🧠 个人知识库</h2>
      <n-space>
        <n-button v-if="activeTab === 'browser'" type="primary" size="small"
          :loading="extracting" @click="doExtract">🤖 提取实体</n-button>
        <n-button type="default" size="small"
          :loading="embedLoading || embedStatus?.job_running"
          @click="triggerEmbed">
          ⚡ 生成向量
        </n-button>
      </n-space>
    </div>

    <!-- Embedding 覆盖率提示栏 -->
    <div v-if="embedStatus" class="embed-status-bar">
      <span class="embed-label">向量覆盖率</span>
      <n-progress
        type="line"
        :percentage="embedStatus.coverage_pct"
        :indicator-placement="'inside'"
        :status="embedStatus.coverage_pct >= 80 ? 'success' : embedStatus.coverage_pct >= 40 ? 'warning' : 'error'"
        style="flex:1; min-width: 120px; max-width: 220px"
      />
      <span class="embed-count">{{ embedStatus.embedded }}/{{ embedStatus.total }} 篇</span>
      <n-tag v-if="embedStatus.job_running" type="info" size="tiny" round>
        处理中…
      </n-tag>
      <n-tag v-else-if="embedStatus.coverage_pct < 100" type="warning" size="tiny" round>
        {{ embedStatus.pending }} 篇待向量化
      </n-tag>
    </div>

    <!-- Tab 切换 -->
    <n-tabs v-model:value="activeTab" type="line" style="margin-top: 12px">
      <n-tab name="chat">💬 智能问答</n-tab>
      <n-tab name="browser">📚 概念浏览</n-tab>
    </n-tabs>

    <!-- 对话面板 -->
    <div v-if="activeTab === 'chat'" class="chat-container">
      <div ref="chatContainer" class="chat-messages">
        <div v-for="(msg, i) in messages" :key="i"
          :class="['chat-bubble', msg.role]">
          <div class="bubble-avatar">{{ msg.role === 'user' ? '👤' : '🤖' }}</div>
          <div class="bubble-body">
            <!-- 检索层标签 -->
            <div v-if="msg.layer_desc" class="bubble-meta">
              <n-tag size="tiny" :type="LAYER_BADGE[msg.layer ?? 'general']?.type ?? 'info'" round>
                {{ LAYER_BADGE[msg.layer ?? 'general']?.icon }} 检索自：{{ msg.layer_desc }}
              </n-tag>
            </div>
            <div class="bubble-text" style="white-space: pre-wrap">{{ msg.content }}</div>
            <!-- 来源文章 -->
            <div v-if="msg.sources?.length" class="bubble-sources">
              <div style="font-size: 12px; color: #888; margin-bottom: 4px">📎 来源文章</div>
              <div v-for="(a, idx) in msg.sources" :key="a.id" class="source-item"
                @click="router.push(`/articles/${a.id}`)">
                <span><b style="color:#2080f0">[{{ idx + 1 }}]</b> {{ a.title }}</span>
                <span style="color: #aaa; font-size: 11px; white-space: nowrap">{{ getTimeAgo(a.published_at) }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="chatLoading" class="chat-bubble assistant">
          <div class="bubble-avatar">🤖</div>
          <div class="bubble-body"><n-spin size="small" /></div>
        </div>
      </div>
      <div class="chat-input">
        <n-input v-model:value="inputText"
          placeholder="问我任何问题，例如：我收藏过哪些关于RAG的文章？"
          @keydown.enter.exact.prevent="sendQuestion"
          :disabled="chatLoading" />
        <n-button type="primary" :loading="chatLoading"
          :disabled="!inputText.trim()" @click="sendQuestion">发送</n-button>
      </div>
    </div>

    <!-- 概念浏览面板 -->
    <n-spin v-if="activeTab === 'browser'" :show="nodesLoading" style="margin-top: 12px">
      <n-empty v-if="!nodesLoading && nodes.length === 0"
        description="暂无概念数据，点击「提取实体」开始构建" style="margin-top: 60px" />
      <div v-else class="browser">
        <div class="concept-panel">
          <div v-for="(group, type) in grouped" :key="type" class="concept-group">
            <div class="group-header">
              <span :style="{ color: TYPE_COLOR[type], fontWeight: 600 }">
                {{ TYPE_LABEL[type] ?? type }}
              </span>
              <n-tag size="tiny" :color="{ color: TYPE_COLOR[type]+'20', textColor: TYPE_COLOR[type] }">
                {{ group.length }}
              </n-tag>
            </div>
            <div v-for="node in group" :key="node.id" class="concept-item"
              :class="{ active: selectedNode?.id === node.id }"
              @click="selectNode(node)">
              <span class="concept-name">{{ node.name }}</span>
              <n-tag size="tiny" :bordered="false" style="color: #aaa">{{ node.value ?? 0 }} 篇</n-tag>
            </div>
          </div>
        </div>
        <div class="article-panel">
          <div v-if="!selectedNode" class="empty-hint">
            <div style="font-size: 40px; margin-bottom: 12px">👈</div>
            <div style="color: #888">从左侧选择一个技术概念</div>
          </div>
          <template v-else>
            <div class="article-panel-title">
              <n-tag size="small" :color="{ color: TYPE_COLOR[selectedNode.type]+'20', textColor: TYPE_COLOR[selectedNode.type] }">
                {{ TYPE_LABEL[selectedNode.type] ?? selectedNode.type }}
              </n-tag>
              <span style="font-weight: 600; font-size: 16px">{{ selectedNode.name }}</span>
              <span style="color: #888; font-size: 13px">共 {{ nodeArticles.length }} 篇</span>
            </div>
            <n-spin :show="nodeArticlesLoading">
              <n-empty v-if="!nodeArticlesLoading && nodeArticles.length === 0"
                description="暂无关联文章" style="padding: 40px 0" />
              <div v-else class="article-list">
                <div v-for="article in nodeArticles" :key="article.id" class="article-item"
                  @click="router.push(`/articles/${article.id}`)">
                  <div class="article-title">{{ article.title }}</div>
                  <div class="article-meta">
                    <span>{{ article.source_type }}</span>
                    <span>{{ getTimeAgo(article.published_at) }}</span>
                  </div>
                  <p v-if="article.summary" class="article-summary">{{ article.summary }}</p>
                </div>
              </div>
            </n-spin>
          </template>
        </div>
      </div>
    </n-spin>
  </div>
</template>

<style scoped>
.knowledge-page { max-width: 1100px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }

/* Embedding 覆盖率状态栏 */
.embed-status-bar {
  display: flex; align-items: center; gap: 10px;
  margin-top: 12px; padding: 8px 14px;
  background: rgba(128,128,128,0.05);
  border: 1px solid rgba(128,128,128,0.15);
  border-radius: 8px; flex-wrap: wrap;
}
.embed-label { font-size: 12px; color: #888; white-space: nowrap; }
.embed-count { font-size: 12px; color: #666; white-space: nowrap; }

/* 对话样式 */
.chat-container { display: flex; flex-direction: column; height: 560px; margin-top: 8px; border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; overflow: hidden; }
.chat-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.chat-bubble { display: flex; gap: 10px; }
.chat-bubble.user { flex-direction: row-reverse; }
.bubble-avatar { font-size: 22px; flex-shrink: 0; margin-top: 2px; }
.bubble-body { max-width: 75%; display: flex; flex-direction: column; gap: 4px; }
.chat-bubble.user .bubble-body { align-items: flex-end; }
.bubble-meta { display: flex; }
.chat-bubble.user .bubble-meta { justify-content: flex-end; }
.bubble-text { padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.6; }
.chat-bubble.assistant .bubble-text { background: rgba(32,128,240,0.07); border-radius: 4px 12px 12px 12px; }
.chat-bubble.user .bubble-text { background: #2080f0; color: #fff; border-radius: 12px 4px 12px 12px; }
.bubble-sources { margin-top: 4px; padding: 8px 10px; background: rgba(128,128,128,0.06); border-radius: 6px; }
.source-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; cursor: pointer; font-size: 13px; gap: 8px; }
.source-item:hover { color: #2080f0; }
.source-item span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-input { display: flex; gap: 8px; padding: 12px; border-top: 1px solid rgba(128,128,128,0.15); }
.chat-input .n-input { flex: 1; }

/* 概念浏览器样式 */
.browser { display: grid; grid-template-columns: 260px 1fr; gap: 16px; }
.concept-panel { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; overflow-y: auto; max-height: 560px; padding: 8px 0; }
.concept-group { margin-bottom: 4px; }
.group-header { display: flex; justify-content: space-between; align-items: center; padding: 6px 14px; font-size: 12px; }
.concept-item { display: flex; justify-content: space-between; align-items: center; padding: 7px 14px; cursor: pointer; transition: background 0.12s; border-radius: 4px; margin: 1px 4px; }
.concept-item:hover { background: rgba(128,128,128,0.08); }
.concept-item.active { background: rgba(32,128,240,0.1); }
.concept-name { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.article-panel { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; padding: 16px; min-height: 400px; }
.empty-hint { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 300px; }
.article-panel-title { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.article-list { display: flex; flex-direction: column; gap: 12px; }
.article-item { padding: 12px; border: 1px solid rgba(128,128,128,0.15); border-radius: 6px; cursor: pointer; transition: box-shadow 0.15s; }
.article-item:hover { box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
.article-title { font-size: 14px; font-weight: 600; line-height: 1.4; margin-bottom: 4px; }
.article-meta { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #888; margin-bottom: 6px; }
.article-summary { font-size: 13px; color: #666; line-height: 1.6; margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
</style>
