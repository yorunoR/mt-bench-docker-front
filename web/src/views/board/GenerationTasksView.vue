<template>
  <main style="max-width: 1200px; margin: auto">
    <h1 class="mt-2">回答生成タスク一覧</h1>
    <section class="mt-4">
      <div v-if="fetching">Loading...</div>
      <div v-else-if="error">Oh no... {{ error }}</div>
      <div v-else>
        <table v-if="data" class="w-full">
          <thead>
            <tr>
              <th class="cursor-pointer w-3 py-2" @click="setKey('name')">
                <u :class="{ 'text-primary': sortKey === 'name' }"> 名前 </u>
              </th>
              <th class="cursor-pointer w-3" @click="setKey('modelName')">
                <u :class="{ 'text-primary': sortKey === 'modelName' }"> モデル名 </u>
              </th>
              <th class="cursor-pointer w-1" @click="setKey('createdAt')">
                <u :class="{ 'text-primary': sortKey === 'createdAt' }"> 作成日時 </u>
              </th>
              <th class="cursor-pointer w-1" @click="setKey('status')">
                <u :class="{ 'text-primary': sortKey === 'status' }"> ステータス </u>
              </th>
              <th>メモ</th>
              <th class="w-1">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="generationTask in sortedGenerationTasks" :key="generationTask.id">
              <td class="py-2">
                <span>{{ generationTask.name }}</span>
                <router-link
                  class="pl-2"
                  :to="{ name: 'generationTask', params: { id: generationTask.id } }"
                  >></router-link
                >
              </td>
              <td class="py-2">
                {{ generationTask.modelName }}
              </td>
              <td class="py-2">
                {{ timeFormat(generationTask.createdAt) }}
              </td>
              <td class="py-2">
                {{ generationTask.status }}
              </td>
              <td class="py-2">
                {{ generationTask.description }}
              </td>
              <td>
                <div v-if="generationTask.status === 'Completed'" class="p-1">
                  <u class="cursor-pointer" @click="openCreateEvaluationTask(generationTask.id)">
                    評価する
                  </u>
                </div>
                <div class="p-1">
                  <u
                    class="cursor-pointer"
                    @click="() => clickDeleteGenerationTask(generationTask.id)"
                  >
                    削除
                  </u>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
  <section>
    <Dialog v-model:visible="visible" modal header="評価" class="w-5">
      <div v-if="loading">
        <h2 class="p-2">running...</h2>
        <h1 class="p-2">{{ Math.floor(count / 60) }}:{{ ('00' + (count % 60)).slice(-2) }}</h1>
      </div>
      <div v-else>
        <div class="flex align-items-center gap-3 mb-5">
          <label for="evalName" class="font-semibold w-8rem">評価名</label>
          <InputText
            id="evalName"
            v-model="evalName"
            class="flex-auto"
            autocomplete="off"
            placeholder="一意な名前"
          />
        </div>
        <div class="flex align-items-center gap-3 mb-5">
          <label for="model" class="font-semibold w-8rem">評価モデル</label>
          <span>gpt-4-turbo-preview</span>
        </div>
        <div class="flex align-items-center gap-3 mb-5">
          <label for="workerCount" class="font-semibold w-8rem">同時リクエスト数</label>
          <span>10</span>
        </div>
        <div class="flex justify-content-end gap-2">
          <Button
            type="button"
            label="Cancel"
            severity="secondary"
            @click="visible = false"
          ></Button>
          <Button
            type="button"
            label="Run"
            :disabled="!evalName"
            @click="() => clickEvaluationTask()"
          ></Button>
        </div>
      </div>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount } from 'vue'
import router from '@/router'
import { useQuery, useMutation } from '@urql/vue'
import { graphql } from '@/gql'
import GenerationTasks from '@/doc/query/GenerationTasks'
import CreateEvaluationTask from '@/doc/mutation/CreateEvaluationTask'
import DeleteGenerationTask from '@/doc/mutation/DeleteGenerationTask'
import dayjs from 'dayjs'
import swal from 'sweetalert'
import { useToast } from 'primevue/usetoast'

const toast = useToast()

const sortKey = ref('createdAt')
const sortAsc = ref(false)
const selectedId = ref(null)
const visible = ref(false)
const evalName = ref(null)
const count = ref(0)
const loading = ref(false)

const query = graphql(GenerationTasks)
const { fetching, error, data, executeQuery } = useQuery({ query, requestPolicy: 'network-only' })
const { executeMutation: createEvaluationTask } = useMutation(graphql(CreateEvaluationTask))
const { executeMutation: deleteGenerationTask } = useMutation(graphql(DeleteGenerationTask))

const setKey = (key) => {
  if (sortKey.value == key) {
    if (sortAsc.value) {
      sortAsc.value = false
    } else {
      sortAsc.value = true
    }
  } else {
    sortKey.value = key
    sortAsc.value = false
  }
}

const sortedGenerationTasks = computed(() => {
  if (!data.value) return []
  const generationTasks = Array.from(data.value.currentUser.generationTasks)
  const column = sortKey.value
  if (column != '') {
    generationTasks.sort((a, b) => {
      if (a[column] < b[column]) return sortAsc.value ? -1 : 1
      if (a[column] > b[column]) return sortAsc.value ? 1 : -1
      return a.id < b.id ? 1 : -1
    })
  }
  return generationTasks
})

const timeFormat = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const interval = 60_000 // 60秒
let timeoutId

const executeAndDoubleInterval = () => {
  executeQuery({ requestPolicy: 'network-only' })

  if (
    !data.value ||
    data.value.currentUser.generationTasks.some(
      (generationTask) => generationTask.status == 'Started'
    )
  ) {
    timeoutId = setTimeout(executeAndDoubleInterval, interval)
  }
}

timeoutId = setTimeout(executeAndDoubleInterval, interval)

onBeforeUnmount(() => {
  clearInterval(timeoutId)
  clearInterval(countId)
})

const openCreateEvaluationTask = (id) => {
  selectedId.value = id
  visible.value = true
}
const clickEvaluationTask = async () => {
  loading.value = true
  count.value = 0

  await countDisplay()
  try {
    const result = await createEvaluationTask({
      generationTaskId: selectedId.value,
      evalName: evalName.value,
      model: 'gpt-4-turbo-preview',
      workerCount: 10
    })
    if (result.error) {
      loading.value = false
      toast.add({
        severity: 'error',
        summary: 'Evaluate answers',
        detail: result.error.message
      })
    } else {
      router.push({ name: 'evaluationTasks' })
    }
  } finally {
    clearInterval(countId)
  }
}

let countId
const countDisplay = async () => {
  countId = setInterval(() => {
    ++count.value
  }, 1000)
}

const clickDeleteGenerationTask = async (id) => {
  const value = await swal({
    title: '評価タスク削除',
    text: '戻せません',
    icon: 'warning',
    buttons: {
      cancelbutton: { text: 'キャンセル', value: 'cancel' },
      yesbutton: { text: 'OK', value: 'ok' }
    }
  })

  if (value === 'ok') {
    await deleteGenerationTask({ id })
  }
}
</script>

<style scoped>
table {
  border-collapse: collapse; /* セルの線を重ねる */
}
td,
th {
  border: 1px solid;
}
</style>
