<template>
  <van-tabbar v-model="active" route>
    <van-tabbar-item to="/home" icon="wap-nav">{{ $t('nav.home') }}</van-tabbar-item>
    <van-tabbar-item to="/football" icon="chart-trending-o">数据</van-tabbar-item>
    <van-tabbar-item to="/aichat" icon="chat-o">AI助手</van-tabbar-item>
    <van-tabbar-item to="/my" icon="user-o">{{ $t('nav.my') }}</van-tabbar-item>
  </van-tabbar>
</template>

<script setup>
import { ref } from 'vue'

const active = ref(0)
</script>
