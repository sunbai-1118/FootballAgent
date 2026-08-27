<template>
  <div class="login-page">
    <van-nav-bar title="用户登录" left-arrow @click-left="router.back()" sticky />

    <section class="hero-band auth-hero">
      <div class="auth-brand">
        <span class="brand-mark">⚽</span>
        <p class="kicker">FOOTBALL HEADLINES</p>
        <h2>欢迎回来</h2>
        <p class="sub">同步你的绿茵动态与 AI 问答</p>
      </div>
    </section>

    <van-form @submit="onSubmit" class="form-card section-card">
      <van-field
        v-model="username"
        name="username"
        label="用户名"
        placeholder="请输入用户名"
        :rules="[{ required: true, message: '请填写用户名' }]"
      />
      <van-field
        v-model="password"
        type="password"
        name="password"
        label="密码"
        placeholder="请输入密码"
        :rules="[{ required: true, message: '请填写密码' }]"
      />

      <van-button round block type="primary" native-type="submit" size="large" class="submit-btn">登录</van-button>
      <p class="register-link">还没有账号？<span @click="goToRegister">立即注册</span></p>
    </van-form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { showLoadingToast, showToast } from 'vant';
import { useUserStore } from '../store/user';

const router = useRouter();
const userStore = useUserStore();
const username = ref('');
const password = ref('');

const onSubmit = async () => {
  showLoadingToast({ message: '登录中...', forbidClick: true, duration: 0 });
  try {
    const result = await userStore.login({ username: username.value, password: password.value });
    showToast(result.success ? { type: 'success', message: result.message } : { type: 'fail', message: result.message });
    if (result.success) router.push('/');
  } catch (error) {
    showToast({ type: 'fail', message: '登录失败，请稍后再试' });
  }
};

const goToRegister = () => router.push('/register');
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background-color: var(--background-color);
}

.auth-hero {
  min-height: 205px;
}

.auth-brand {
  position: relative;
  z-index: 2;
}

.brand-mark {
  margin-bottom: 14px;
}

.kicker {
  font-size: 10px;
  letter-spacing: 3px;
  color: var(--grass-300);
}

.auth-brand h2 {
  margin: 4px 0;
  color: var(--white);
  font-size: var(--font-xl);
}

.sub {
  color: rgba(255, 255, 255, .74);
  font-size: 13px;
}

.form-card {
  width: calc(100% - 32px);
  margin: -28px auto 0;
  position: relative;
  z-index: 2;
}

.submit-btn {
  margin-top: 24px;
}

.register-link {
  padding-bottom: 6px;
  text-align: center;
  font-size: 13px;
  color: var(--text-color-light);
}

.register-link span {
  color: var(--pitch-700);
  font-weight: 650;
}
</style>
