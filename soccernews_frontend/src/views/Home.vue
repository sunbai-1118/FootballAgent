<template>
  <div class="home page-shell">
    <van-nav-bar>
      <template #left>
        <div class="nav-brand">
          <span class="brand-mark">⚽</span>
          <span class="brand-name">足球头条</span>
        </div>
      </template>
      <template #right>
        <van-icon name="apps-o" size="19" @click="goToCategory" />
      </template>
    </van-nav-bar>

    <section class="hero-band">
      <p class="hero-kicker">MATCH DAY</p>
      <h1 class="hero-title">绿茵资讯<br>一屏掌握</h1>
      <p class="hero-desc">联赛动态 · 球队情报 · AI 战术问答</p>
    </section>

    <div class="category-tabs">
      <van-tabs v-model:active="activeTab" sticky swipeable animated line-width="28px">
        <van-tab
          v-for="(category, index) in displayCategories"
          :key="category.id"
          :title="getCategoryTranslation(category.name)"
        >
          <van-pull-refresh v-model="newsStore.refreshing" @refresh="onRefresh">
            <van-list
              v-model:loading="newsStore.loading"
              :finished="newsStore.finished"
              finished-text="没有更多了"
              loading-text="加载中..."
              @load="onLoad"
            >
              <news-item
                v-for="item in newsStore.newsList"
                :key="item.id"
                :news="item"
              />
              <van-empty v-if="!newsStore.loading && !newsStore.newsList.length" description="暂无赛事资讯" />
            </van-list>
          </van-pull-refresh>
        </van-tab>
      </van-tabs>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useNewsStore } from '../store/modules/news'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import NewsItem from '../components/NewsItem.vue'

const newsStore = useNewsStore()
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const activeTab = ref(0)
const routeCategoryHandled = ref(false)

const displayCategories = computed(() => {
  return newsStore.categories.filter(category => category.name !== '更多')
})

watch(activeTab, (index) => {
  const category = displayCategories.value[index]
  if (category) newsStore.changeCategory(category.id)
})

onMounted(async () => {
  await newsStore.getCategories()
  const categoryId = Number(route.query.categoryId)

  if (categoryId && !routeCategoryHandled.value) {
    const index = displayCategories.value.findIndex(item => item.id === categoryId)
    if (index >= 0) activeTab.value = index
    routeCategoryHandled.value = true
    return
  }

  if (!newsStore.newsList.length) newsStore.getNewsList()
})

const getCategoryTranslation = (name) => {
  const categoryMap = {
    推荐: 'recommended',
    英超: 'premierLeague',
    西甲: 'laLiga',
    意甲: 'serieA',
    德甲: 'bundesliga',
    法甲: 'ligue1',
    中超: 'csl',
    欧冠: 'championsLeague',
    世界杯: 'worldCup',
    更多: 'more'
  }
  return categoryMap[name] ? t(`home.categories.${categoryMap[name]}`) : name
}

const goToCategory = () => router.push('/category')
const onRefresh = () => newsStore.getNewsList(true)
const onLoad = () => newsStore.getNewsList()
</script>

<style scoped>
.home {
  background: var(--background-color);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-mark {
  width: 36px;
  height: 36px;
  font-size: 16px;
}

.brand-name {
  color: var(--white);
  font-size: var(--font-md);
  font-weight: 750;
  letter-spacing: .5px;
}

:deep(.van-nav-bar__right) {
  padding-right: 18px;
}

.hero-kicker,
.hero-title,
.hero-desc {
  position: relative;
  z-index: 2;
}

.hero-kicker {
  margin-bottom: 8px;
  font-size: var(--font-xs);
  letter-spacing: 4px;
  color: var(--grass-300);
}

.hero-title {
  font-size: var(--font-xl);
  line-height: 1.25;
  font-weight: 800;
}

.hero-desc {
  max-width: 250px;
  margin-top: 10px;
  font-size: var(--font-sm);
  opacity: .78;
}

.category-tabs {
  position: relative;
  z-index: 3;
  margin-top: -16px;
}

.category-tabs :deep(.van-tabs__content--animated) {
  overflow: visible !important;
}

.category-tabs :deep(.van-tabs) {
  border-radius: var(--radius) var(--radius) 0 0;
  overflow: hidden;
  background: var(--card-bg);
  box-shadow: var(--shadow-sm);
}

.category-tabs :deep(.van-tab--active) {
  color: var(--pitch-700);
  font-weight: 700;
}
</style>
