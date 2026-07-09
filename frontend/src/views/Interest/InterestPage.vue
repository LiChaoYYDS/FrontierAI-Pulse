<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { useInterestStore } from '@/stores/interestStore'

const message = useMessage()
const store = useInterestStore()

const customInput = ref('')
const saving = ref(false)

// 当前已选（合并预设选中 + 自定义）
const selectedList = computed(() => [...store.selected])

// 自定义标签：已选但不在预设中的
const customTags = computed(() =>
  [...store.selected].filter(t => !store.presets.includes(t))
)

onMounted(() => store.load())

async function toggle(tag: string) {
  const next = new Set(store.selected)
  next.has(tag) ? next.delete(tag) : next.add(tag)
  await doSave([...next])
}

async function addCustom() {
  const tag = customInput.value.trim()
  if (!tag) return
  if (store.selected.has(tag)) { message.warning('已存在'); return }
  await doSave([...store.selected, tag])
  customInput.value = ''
}

async function removeTag(tag: string) {
  const next = [...store.selected].filter(t => t !== tag)
  await doSave(next)
}

async function doSave(interests: string[]) {
  saving.value = true
  try {
    await store.save(interests)
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="interest-page">
    <div class="page-header">
      <h2 style="margin: 0">🎯 兴趣标签</h2>
      <span style="font-size: 13px; color: #888">点击标签选中/取消，AI 将根据兴趣为文章评分</span>
    </div>

    <!-- 预设标签 -->
    <n-card title="预设技术领域" :bordered="true" style="margin-top: 20px">
      <n-space size="small" style="flex-wrap: wrap">
        <n-tag
          v-for="tag in store.presets"
          :key="tag"
          :type="store.selected.has(tag) ? 'primary' : 'default'"
          style="cursor: pointer; user-select: none"
          :bordered="!store.selected.has(tag)"
          @click="toggle(tag)"
        >
          {{ store.selected.has(tag) ? '✓ ' : '' }}{{ tag }}
        </n-tag>
      </n-space>
    </n-card>

    <!-- 自定义标签 -->
    <n-card title="自定义标签" :bordered="true" style="margin-top: 16px">
      <n-input-group>
        <n-input v-model:value="customInput" placeholder="输入自定义标签，回车添加"
          style="max-width: 300px" @keydown.enter="addCustom" />
        <n-button type="primary" @click="addCustom">添加</n-button>
      </n-input-group>
      <n-space v-if="customTags.length > 0" size="small" style="margin-top: 12px">
        <n-tag
          v-for="tag in customTags"
          :key="tag"
          type="success"
          closable
          @close="removeTag(tag)"
        >{{ tag }}</n-tag>
      </n-space>
    </n-card>

    <!-- 已选汇总 -->
    <n-card v-if="selectedList.length > 0" :bordered="true" style="margin-top: 16px">
      <template #header>
        <span>已选 {{ selectedList.length }} 个</span>
      </template>
      <n-space size="small" style="flex-wrap: wrap">
        <n-tag
          v-for="tag in selectedList"
          :key="tag"
          type="primary"
          closable
          @close="removeTag(tag)"
        >{{ tag }}</n-tag>
      </n-space>
    </n-card>
  </div>
</template>

<style scoped>
.interest-page { max-width: 800px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
</style>
