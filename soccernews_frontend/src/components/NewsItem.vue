<template>
  <article class="news-item" @click="goToDetail">
    <div class="news-content">
      <h3 class="news-title">{{ news.title }}</h3>
      <p class="news-desc">{{ news.description }}</p>
      <div class="news-info">
        <span><van-icon name="manager-o" /> {{ news.author }}</span>
        <span><van-icon name="clock-o" /> {{ news.publishTime }}</span>
        <span><van-icon name="eye-o" /> {{ formatViews(news.views) }}</span>
      </div>
    </div>
    <div class="news-image">
      <img :src="news.image" :alt="news.title" loading="lazy">
    </div>
  </article>
</template>

<script setup>
import { defineProps } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  news: {
    type: Object,
    required: true
  }
})

const router = useRouter()

const goToDetail = () => {
  router.push(`/news/detail/${props.news.id}`)
}

const formatViews = (value) => {
  const count = Number(value || 0)
  return count >= 10000 ? `${(count / 10000).toFixed(1)}万` : count
}
</script>

<style scoped>
.news-item {
  display: flex;
  margin: 10px 14px;
  padding: 10px 12px;
  border-radius: var(--radius);
  background-color: var(--card-bg);
  box-shadow: var(--shadow-sm);
  transition: transform .18s ease, box-shadow .18s ease;
}

.news-item:active {
  transform: scale(.985);
  box-shadow: var(--shadow-lg);
}

.news-content {
  flex: 1;
  min-width: 0;
  margin-right: 12px;
}

.news-title {
  font-size: var(--font-md);
  font-weight: 650;
  margin: 0 0 8px;
  line-height: 1.4;
  display: -webkit-box;
  overflow: hidden;
  text-overflow: ellipsis;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.news-desc {
  font-size: 13px;
  color: var(--text-color-light);
  margin: 0 0 10px;
  display: -webkit-box;
  overflow: hidden;
  text-overflow: ellipsis;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.news-info {
  font-size: 12px;
  color: var(--text-color-lighter);
  display: flex;
  gap: 8px;
}

.news-image {
  width: 112px;
  height: 84px;
  flex-shrink: 0;
}

.news-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: var(--radius-sm);
}
</style>
