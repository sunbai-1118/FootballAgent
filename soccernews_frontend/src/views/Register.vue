<template>
  <div class="register-page">
    <van-nav-bar title="用户注册" left-arrow @click-left="router.back()" sticky />

    <section class="hero-band auth-hero">
      <div class="auth-brand">
        <span class="brand-mark">⚽</span>
        <p class="kicker">JOIN THE SQUAD</p>
        <h2>创建球迷账号</h2>
        <p class="sub">收藏赛报、追踪历史、与 AI 聊球</p>
      </div>
    </section>

    <van-form @submit="onSubmit" class="form-card section-card">
      <van-field v-model="username" label="用户名" placeholder="请输入用户名" :rules="[{ required: true, message: '请填写用户名' }]" />
      <van-field v-model="password" type="password" label="密码" placeholder="请输入密码" :rules="[{ required: true, message: '请填写密码' }]" />
      <van-field
        v-model="confirmPassword"
        type="password"
        label="确认密码"
        placeholder="请再次输入密码"
        :rules="[{ required: true, message: '请确认密码' }, { validator: validatePassword, message: '两次密码不一致' }]"
      />
      <van-button round block type="primary" native-type="submit" size="large" class="submit-btn">注册</van-button>
      <p class="login-link">已有账号？<span @click="goToLogin">去登录</span></p>
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
const confirmPassword = ref('');

const validatePassword = () => password.value === confirmPassword.value;

const onSubmit = async () => {
  showLoadingToast({ message: '注册中...', forbidClick: true, duration: 0 });
  try {
    const result = await userStore.register({ username: username.value, password: password.value });
    showToast(result.success ? { type: 'success', message: result.message } : { type: 'fail', message: result.message });
    if (result.success) router.push('/');
  } catch (error) {
    showToast({ type: 'fail', message: '注册失败，请稍后再试' });
  }
};

const goToLogin = () => router.push('/login');
</script>

<style scoped>
.register-page {
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

.login-link {
  padding-bottom: 6px;
  text-align: center;
  font-size: 13px;
  color: var(--text-color-light);
}

.login-link span {
  color: var(--pitch-700);
  font-weight: 650;
}
</style>
