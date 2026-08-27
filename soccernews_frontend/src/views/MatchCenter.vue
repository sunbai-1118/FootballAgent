<template>
  <div class="page-shell football-page">
    <header class="page-header">
      <h1>📊 比赛中心</h1>
      <p>最近完赛与即将开赛</p>
    </header>

    <van-tabs v-model:active="activeTab" sticky>
      <van-tab title="最近比赛">
        <section class="widget-card">
          <!-- 官方 league Widget：last=10 返回最近完赛记录 -->
          <api-league league-id="39" last="10" />
        </section>
      </van-tab>
      <van-tab title="即将开始">
        <section class="widget-card">
          <!-- 官方 league Widget：next=10 返回即将开始的比赛 -->
          <api-league league-id="39" next="10" />
        </section>
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useApiSportsWidget } from '../components/soccer/useApiSportsWidget'

const { mountWidget } = useApiSportsWidget()
const activeTab = ref('recent')

onMounted(() => mountWidget(document.querySelectorAll('api-league')))
</script>
