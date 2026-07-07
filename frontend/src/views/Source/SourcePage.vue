<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useSourceStore } from '@/stores/sourceStore'
import type { PresetSource } from '@/types/source'
import * as api from '@/api'

const message = useMessage()
const sourceStore = useSourceStore()
const fetchingKey = ref<string | null>(null)

const typeIcon: Record<string, string> = {
  rss: '📰', arxiv: '🎓', website: '🌐', github: '🐙', twitter: '🐦',
}
const categoryColor: Record<string, 'info' | 'success'> = { zh: 'success', en: 'info' }
const categoryLabel: Record<string, string> = { zh: '中文', en: '英文' }

const zhSources = computed(() => sourceStore.presets.filter(s => s.category === 'zh'))
const enSources = computed(() => sourceStore.presets.filter(s => s.category === 'en'))

onMounted(() => sourceStore.loadPresets())

async function toggle(key: string) {
  try {
    await sourceStore.toggleSource(key)
  } catch {
    message.error('保存失败')
  }
}

async function handleFetch(preset: PresetSource) {
  fetchingKey.value = preset.key
  try {
    await sourceStore.loadSources()
    const source = sourceStore.sources.find(s => s.url === preset.url)
    if (!source) { message.warning('请先启用该来源并等待同步'); return }
    const res = await api.fetchSource(source.id)
    message.success(`「${preset.name}」抓取完成，新增 ${res.new_articles} 篇`)
  } catch {
    message.error('抓取失败')
  } finally {
    fetchingKey.value = null
  }
}
</script>

<template>
  <div class="source-page">
    <div class="page-header">
      <div>
        <h2 style="margin: 0">📡 资讯来源</h2>
        <span style="font-size: 13px; color: #888; margin-top: 4px; display: block">
          勾选需要订阅的来源，系统将自动定时抓取
        </span>
      </div>
      <n-space>
        <n-button size="small" @click="sourceStore.selectAll">全选</n-button>
        <n-button size="small" @click="sourceStore.selectNone">全不选</n-button>
      </n-space>
    </div>

    <n-card title="🇨🇳 中文来源" :bordered="true" style="margin-top: 20px">
      <div class="source-list">
        <div v-for="preset in zhSources" :key="preset.key" class="source-row"
          :class="{ disabled: !sourceStore.enabledKeys.has(preset.key) }">
          <n-checkbox :checked="sourceStore.enabledKeys.has(preset.key)"
            @update:checked="() => toggle(preset.key)" />
          <span class="source-icon">{{ typeIcon[preset.type] || '📄' }}</span>
          <div class="source-info">
            <span class="source-name">{{ preset.name }}</span>
            <span class="source-desc">{{ preset.description }}</span>
          </div>
          <n-tag :type="categoryColor[preset.category]" size="small" style="flex-shrink: 0">
            {{ categoryLabel[preset.category] }}
          </n-tag>
          <n-button v-if="sourceStore.enabledKeys.has(preset.key)" size="tiny" quaternary type="primary"
            :loading="fetchingKey === preset.key" @click="handleFetch(preset)">
            立即抓取
          </n-button>
        </div>
      </div>
    </n-card>

    <n-card title="🌍 英文来源" :bordered="true" style="margin-top: 16px">
      <div class="source-list">
        <div v-for="preset in enSources" :key="preset.key" class="source-row"
          :class="{ disabled: !sourceStore.enabledKeys.has(preset.key) }">
          <n-checkbox :checked="sourceStore.enabledKeys.has(preset.key)"
            @update:checked="() => toggle(preset.key)" />
          <span class="source-icon">{{ typeIcon[preset.type] || '📄' }}</span>
          <div class="source-info">
            <span class="source-name">{{ preset.name }}</span>
            <span class="source-desc">{{ preset.description }}</span>
          </div>
          <n-tag :type="categoryColor[preset.category]" size="small" style="flex-shrink: 0">
            {{ categoryLabel[preset.category] }}
          </n-tag>
          <n-button v-if="sourceStore.enabledKeys.has(preset.key)" size="tiny" quaternary type="primary"
            :loading="fetchingKey === preset.key" @click="handleFetch(preset)">
            立即抓取
          </n-button>
        </div>
      </div>
    </n-card>
  </div>
</template>

<style scoped>
.source-page { max-width: 800px; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; }
.source-list { display: flex; flex-direction: column; gap: 2px; }
.source-row {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 8px; border-radius: 6px; transition: background 0.15s;
}
.source-row:hover { background: rgba(128, 128, 128, 0.06); }
.source-row.disabled { opacity: 0.45; }
.source-icon { font-size: 18px; flex-shrink: 0; }
.source-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.source-name { font-size: 14px; font-weight: 500; }
.source-desc { font-size: 12px; color: #888; }
</style>
