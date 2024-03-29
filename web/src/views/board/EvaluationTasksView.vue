<template>
  <main style="max-width: 1200px; margin: auto">
    <h1 class="mt-2">評価タスク一覧</h1>
    <section v-if="dataSources1.length > 0 || dataSources2.length > 0" class="mt-6">
      <div class="flex">
        <Chart type="radar" :data="chartData1" :options="chartOptions" class="w-6" />
        <Chart type="radar" :data="chartData2" :options="chartOptions" class="w-6" />
      </div>
    </section>
    <section class="mt-4">
      <div v-if="fetching">Loading...</div>
      <div v-else-if="error">Oh no... {{ error }}</div>
      <div v-else>
        <table v-if="data" class="w-full">
          <thead>
            <tr>
              <th class="w-1 py-2">選択</th>
              <th class="cursor-pointer w-3 py-2" @click="setKey('name')">
                <u :class="{ 'text-primary': sortKey === 'name' }"> 名前 </u>
              </th>
              <th class="cursor-pointer w-1" @click="setKey('createdAt')">
                <u :class="{ 'text-primary': sortKey === 'createdAt' }"> 作成日時 </u>
              </th>
              <th class="cursor-pointer w-1" @click="setKey('status')">
                <u :class="{ 'text-primary': sortKey === 'status' }"> ステータス </u>
              </th>
              <th>点数</th>
              <th class="w-1">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="evaluationTask in sortedEvaluationTasks" :key="evaluationTask.id">
              <th class="py-2">
                <div v-if="evaluationTask.points !== {}">
                  <Checkbox
                    v-model="dataSources1"
                    :value="{ name: evaluationTask.name, points: evaluationTask.points }"
                    @change="() => (chartData1 = setChartData(dataSources1))"
                  />
                  <Checkbox
                    v-model="dataSources2"
                    class="ml-2"
                    :value="{ name: evaluationTask.name, points: evaluationTask.points }"
                    @change="() => (chartData2 = setChartData(dataSources2))"
                  />
                </div>
              </th>
              <td class="py-2">
                <span>{{ evaluationTask.name }}</span>
                <router-link
                  class="pl-2"
                  :to="{ name: 'evaluationTask', params: { id: evaluationTask.id } }"
                  >></router-link
                >
              </td>
              <td class="py-2">
                {{ timeFormat(evaluationTask.createdAt) }}
              </td>
              <td class="py-2">
                {{ evaluationTask.status }}
              </td>
              <td class="py-2">
                <div>{{ evaluationTask.points }}</div>
                <div class="mt-2">AVG: {{ avg(evaluationTask.points) }}</div>
              </td>
              <td>
                <div
                  v-if="evaluationTask.status === 'Completed' && isEmpty(evaluationTask.points)"
                  class="p-1"
                >
                  <u
                    v-if="!loading"
                    class="cursor-pointer"
                    @click="() => clickUpdateEvaluationTask(evaluationTask.id)"
                  >
                    集計する
                  </u>
                </div>
                <div class="p-1">
                  <u
                    class="cursor-pointer"
                    @click="() => clickDeleteEvaluationTask(evaluationTask.id)"
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
</template>

<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted } from 'vue'
import { useQuery, useMutation } from '@urql/vue'
import { graphql } from '@/gql'
import EvaluationTasks from '@/doc/query/EvaluationTasks'
import UpdateEvaluationTask from '@/doc/mutation/UpdateEvaluationTask'
import DeleteEvaluationTask from '@/doc/mutation/DeleteEvaluationTask'
import dayjs from 'dayjs'
import swal from 'sweetalert'

const sortKey = ref('createdAt')
const sortAsc = ref(false)
const loading = ref(false)
const dataSources1 = ref([])
const dataSources2 = ref([])

const query = graphql(EvaluationTasks)
const { fetching, error, data, executeQuery } = useQuery({ query, requestPolicy: 'network-only' })
const { executeMutation: updateEvaluationTask } = useMutation(graphql(UpdateEvaluationTask))
const { executeMutation: deleteEvaluationTask } = useMutation(graphql(DeleteEvaluationTask))

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

const sortedEvaluationTasks = computed(() => {
  if (!data.value) return []
  const evaluationTasks = Array.from(data.value.currentUser.evaluationTasks)
  const column = sortKey.value
  if (column != '') {
    evaluationTasks.sort((a, b) => {
      if (a[column] < b[column]) return sortAsc.value ? -1 : 1
      if (a[column] > b[column]) return sortAsc.value ? 1 : -1
      return a.id < b.id ? 1 : -1
    })
  }
  return evaluationTasks
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
    data.value.currentUser.evaluationTasks.some(
      (evaluationTask) => evaluationTask.status == 'Started'
    )
  ) {
    timeoutId = setTimeout(executeAndDoubleInterval, interval)
  }
}

timeoutId = setTimeout(executeAndDoubleInterval, interval)

onBeforeUnmount(() => {
  clearInterval(timeoutId)
})

const clickUpdateEvaluationTask = async (id) => {
  loading.value = true
  try {
    await updateEvaluationTask({ id })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  chartOptions.value = setChartOptions()
})

const chartData1 = ref()
const chartData2 = ref()
const chartOptions = ref()

const setChartData = (dataSources) => {
  if (dataSources.length > 0) {
    const labels = Object.keys(dataSources[0].points).sort()
    const datasets = dataSources.map((dataSource) => {
      const data = labels.map((label) => dataSource.points[label])
      return {
        label: dataSource.name,
        data
      }
    })
    return { labels, datasets }
  } else {
    return { labels: [], datasets: [] }
  }
}
const setChartOptions = () => {
  const documentStyle = getComputedStyle(document.documentElement)
  const textColor = documentStyle.getPropertyValue('--text-color')
  const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary')

  return {
    plugins: {
      legend: {
        labels: {
          color: textColor
        }
      }
    },
    scales: {
      r: {
        grid: {
          color: textColorSecondary
        },
        suggestedMin: 0,
        suggestedMax: 10
      }
    },
    elements: {
      line: {
        fill: false // これにより塗りつぶしが無効になります
      }
    }
  }
}

const isEmpty = (obj) => {
  return Object.keys(obj).length === 0
}
const avg = (obj) => {
  const len = Object.keys(obj).length
  if (len < 1) return 0
  return Object.values(obj).reduce((sum, element) => sum + element, 0) / len
}

const clickDeleteEvaluationTask = async (id) => {
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
    await deleteEvaluationTask({ id })
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
