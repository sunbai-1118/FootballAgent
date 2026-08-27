<template>
  <div class="page-shell football-page">
    <header class="page-header">
      <p>今日赛程与实时比分</p>
    </header>

    <section class="widget-card">
      <!-- 官方 games Widget：date=today 展示今日比赛，live=all 聚合实时比分 -->
      <api-games date="today" live="all" />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useApiSportsWidget } from '../components/soccer/useApiSportsWidget'

const { mountWidget } = useApiSportsWidget()
const widgetRoot = ref(null)

onMounted(() => mountWidget(document.querySelectorAll('api-games')))
</script>
