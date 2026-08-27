<template>
  <div class="category">
    <van-nav-bar 
      :title="$t('common.allCategories')" 
      :left-text="$t('common.back')"
      left-arrow
      @click-left="onClickLeft"
      sticky
    />
    
    <div class="category-container">
      <van-grid :column-num="3" :border="false">
        <van-grid-item 
          v-for="category in displayCategories" 
          :key="category.id"
          :text="getCategoryTranslation(category.name)"
          icon="newspaper-o"
          @click="goToCategoryNews(category.id)"
        />
      </van-grid>
    </div>
    
  </div>
</template>

<script setup>
import { useNewsStore } from '../store/modules/news'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'

const newsStore = useNewsStore()
const router = useRouter()
const { t } = useI18n()

// 计算属性：显示的分类（只显示非"更多"分类）
const displayCategories = computed(() => {
  return newsStore.categories.filter(category => category.name !== '更多');
})

// 返回上一页
const onClickLeft = () => {
  router.back()
}

// 跳转到对应分类的新闻列表
const goToCategoryNews = (categoryId) => {
  // 先切换分类
  newsStore.changeCategory(categoryId)
  
  // 使用路由参数传递分类ID
  router.push({
    path: '/home',
    query: { categoryId: categoryId }
  })
}

// 获取分类名称的翻译
const getCategoryTranslation = (categoryName) => {
  const categoryMap = {
    '推荐': 'recommended',
    '英超': 'premierLeague',
    '西甲': 'laLiga',
    '意甲': 'serieA',
    '德甲': 'bundesliga',
    '法甲': 'ligue1',
    '中超': 'csl',
    '欧冠': 'championsLeague',
    '世界杯': 'worldCup',
    '更多': 'more'
  };
  
  const key = categoryMap[categoryName];
  return key ? t(`home.categories.${key}`) : categoryName;
}
</script>

<style scoped>
.category {
  padding-bottom: 50px;
  background-color: var(--background-color);
  min-height: 100vh;
}

.category-container {
  padding: 0;
  background-color: var(--card-bg);
  margin-top: 12px;
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}

:deep(.van-grid-item__content) {
  background-color: var(--secondary-color);
  border-radius: var(--radius);
  padding: 14px 0;
}

:deep(.van-grid-item__icon) {
  font-size: var(--font-xl);
  color: var(--pitch-700);
}

:deep(.van-grid-item__text) {
  margin-top: 8px;
  color: var(--text-color);
  font-size: 14px;
}
</style>
