<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useSourceStore } from '@/stores/sourceStore'
import * as api from '@/api'

const message     = useMessage()
const sourceStore = useSourceStore()
const fetchingId  = ref<number | null>(null)

const typeIcon: Record<string, string> = {
  rss: '📰', arxiv: '🎓', website: '🌐', github: '🐙',
}

// ── 添加来源 Modal ────────────────────────────────────────────────────────────
const showAddModal = ref(false)
const addForm = reactive({ name: '', url: '', type: 'rss', description: '' })
const typeOptions = [
  { label: '📰 RSS',    value: 'rss'     },
  { label: '🌐 网站',   value: 'website' },
  { label: '🐙 GitHub', value: 'github'  },
  { label: '🎓 arXiv',  value: 'arxiv'   },
]
const addLoading = ref(false)

function openAddModal() {
  addForm.name = ''
  addForm.url  = ''
  addForm.type = 'rss'
  addForm.description = ''
  showAddModal.value = true
}

async function submitAdd() {
  if (!addForm.name.trim() || !addForm.url.trim()) {
    message.warning('名称和 URL 为必填项')
    return
  }
  addLoading.value = true
  try {
    await sourceStore.addCustomSource({
      name:        addForm.name.trim(),
      url:         addForm.url.trim(),
      type:        addForm.type,
      description: addForm.description.trim() || undefined,
    })
    message.success(`「${addForm.name}」已添加`)
    showAddModal.value = false
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    message.error(detail === '该来源 URL 已存在' ? 'URL 已存在，请勿重复添加' : '添加失败')
  } finally {
    addLoading.value = false
  }
}

// ── 来源操作 ──────────────────────────────────────────────────────────────────
async function handleToggle(id: number, active: boolean) {
  try {
    await sourceStore.toggleSource(id, active)
  } catch {
    message.error('操作失败')
  }
}

async function handleFetch(id: number, name: string) {
  fetchingId.value = id
  try {
    const res = await api.fetchSource(id)
    message.success(`「${name}」抓取完成，新增 ${res.new_articles} 篇`)
  } catch {
    message.error('抓取失败')
  } finally {
    fetchingId.value = null
  }
}

async function handleDelete(id: number, name: string) {
  try {
    await sourceStore.removeSource(id)
    message.success(`「${name}」已删除`)
  } catch {
    message.error('删除失败')
  }
}

onMounted(() => sourceStore.loadSources())
</script>

<template>
  <div class="source-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2 style="margin: 0">📡 资讯来源</h2>
        <span style="font-size: 13px; color: #888; margin-top: 4px; display: block">
          管理资讯订阅来源，系统将自动定时抓取已启用的来源
        </span>
      </div>
      <n-button type="primary" size="small" @click="openAddModal">+ 添加来源</n-button>
    </div>

    <!-- 来源列表 -->
    <n-card :bordered="true" style="margin-top: 20px">
      <n-spin :show="sourceStore.loading">
        <n-empty v-if="!sourceStore.loading && sourceStore.sources.length === 0"
                 description="暂无来源，点击「添加来源」开始订阅"
                 style="padding: 32px 0" />

        <div class="source-list">
          <div v-for="s in sourceStore.sources" :key="s.id"
               class="source-row" :class="{ disabled: !s.is_active }">
            <span class="source-icon">{{ typeIcon[s.type] || '📄' }}</span>
            <div class="source-info">
              <span class="source-name">{{ s.name }}</span>
              <span class="source-desc">{{ s.description || s.url }}</span>
            </div>
            <n-tag size="small" :type="s.is_active ? 'success' : 'default'" :bordered="false">
              {{ s.is_active ? '已启用' : '已禁用' }}
            </n-tag>
            <n-button size="tiny" quaternary
              :type="s.is_active ? 'default' : 'primary'"
              @click="handleToggle(s.id, s.is_active)">
              {{ s.is_active ? '禁用' : '启用' }}
            </n-button>
            <n-button v-if="s.is_active" size="tiny" quaternary type="primary"
              :loading="fetchingId === s.id"
              @click="handleFetch(s.id, s.name)">
              立即抓取
            </n-button>
            <n-popconfirm @positive-click="handleDelete(s.id, s.name)">
              <template #trigger>
                <n-button size="tiny" quaternary type="error">删除</n-button>
              </template>
              确认删除「{{ s.name }}」？关联文章不会被删除。
            </n-popconfirm>
          </div>
        </div>
      </n-spin>
    </n-card>

    <!-- 添加来源 Modal -->
    <n-modal v-model:show="showAddModal" preset="card"
             title="+ 添加来源" style="width: 480px">
      <n-form label-placement="left" label-width="60px" style="margin-top: 8px">
        <n-form-item label="名称" required>
          <n-input v-model:value="addForm.name" placeholder="如：CSDN" />
        </n-form-item>
        <n-form-item label="URL" required>
          <n-input v-model:value="addForm.url"
            placeholder="如：https://blog.csdn.net/rss/list" />
        </n-form-item>
        <n-form-item label="类型">
          <n-select v-model:value="addForm.type" :options="typeOptions" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="addForm.description" placeholder="可选" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" :loading="addLoading" @click="submitAdd">添加</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.source-page  { max-width: 800px; }
.page-header  { display: flex; justify-content: space-between; align-items: flex-start; }
.source-list  { display: flex; flex-direction: column; gap: 2px; }
.source-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 8px; border-radius: 6px; transition: background 0.15s;
}
.source-row:hover  { background: rgba(128, 128, 128, 0.06); }
.source-row.disabled { opacity: 0.45; }
.source-icon  { font-size: 18px; flex-shrink: 0; }
.source-info  { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.source-name  { font-size: 14px; font-weight: 500; }
.source-desc  { font-size: 12px; color: #888; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
