<template>
  <div class="app" :class="{ 'has-tab-bar': showTabBar }">
    <router-view v-slot="{ Component }">
      <template v-if="$route.meta.keepAlive">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </template>
      <template v-else>
        <component :is="Component" />
      </template>
    </router-view>
    <TabBar v-if="showTabBar" />
  </div>
</template>

<script setup>
import TabBar from './components/TabBar.vue'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const showTabBar = computed(() => !['Login', 'Register'].includes(route.name))
</script>

<style>
.app.has-tab-bar {
  padding-bottom: calc(56px + env(safe-area-inset-bottom));
}
</style>
