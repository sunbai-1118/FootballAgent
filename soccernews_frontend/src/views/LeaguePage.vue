<template>
  <div class="page-shell football-page">
    <header class="page-header">
      <h1>🏆 联赛积分榜</h1>
      <p>五大联赛实时排名</p>
    </header>

    <section class="league-picker">
      <button
        v-for="league in leagues"
        :key="league.id"
        :class="{ active: leagueId === league.id }"
        @click="leagueId = league.id"
      >
        {{ league.name }}
      </button>
    </section>

    <section class="widget-card">
      <!-- 官方 standings Widget：league + season 由后端代理转发到 API-Football -->
      <api-standings :league="leagueId" season="2024" />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useApiSportsWidget } from '../components/soccer/useApiSportsWidget'

const { mountWidget } = useApiSportsWidget()
const widgetRoot = ref(null)
const leagueId = ref(39)
const leagues = [
  { id: 39, name: '英超' },
  { id: 140, name: '西甲' },
  { id: 135, name: '意甲' },
  { id: 78, name: '德甲' },
  { id: 61, name: '法甲' }
]

watch(leagueId, async () => {
  await mountWidget(document.querySelectorAll('api-standings'))
})

onMounted(() => mountWidget(document.querySelectorAll('api-standings')))
</script>
