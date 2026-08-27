<template>
  <div class="my-container page-shell">
    <van-nav-bar :title="$t('my.title')" />

    <section class="hero-band user-hero">
      <div class="user-card" @click="goToProfile" v-if="isLogin">
        <div class="avatar">
          <van-image round width="72" height="72" :src="userAvatar" />
        </div>
        <div class="info">
          <div class="username">{{ userInfo.username }}</div>
          <div class="desc">{{ userBio || $t('profile.bio') }}</div>
        </div>
        <van-icon name="arrow" class="arrow-icon" />
      </div>

      <div class="user-card guest-card" v-else>
        <div class="avatar guest-avatar">⚽</div>
        <div class="info">
          <div class="username">{{ $t('my.notLoggedIn') }}</div>
          <p class="guest-desc">登录后同步收藏、历史和 AI 会话</p>
          <div class="auth-actions">
            <van-button class="auth-button login-button" round size="small" @click.stop="goToLogin">去登录</van-button>
            <van-button class="auth-button register-button" round size="small" plain @click.stop="goToRegister">去注册</van-button>
          </div>
        </div>
      </div>
    </section>

    <div class="quick-grid section-card">
      <button class="quick-item" @click="goToFavorite">
        <span class="quick-icon"><van-icon name="star-o" /></span>收藏
      </button>
      <button class="quick-item" @click="goToHistory">
        <span class="quick-icon"><van-icon name="underway-o" /></span>历史
      </button>
      <button class="quick-item" @click="goToSettings">
        <span class="quick-icon"><van-icon name="setting-o" /></span>设置
      </button>
    </div>

    <div class="menu-list">
      <van-cell-group inset>
        <van-cell :title="$t('my.myFavorite')" is-link icon="star-o" @click="goToFavorite" />
      <van-cell :title="$t('my.browsingHistory')" is-link icon="clock-o" @click="goToHistory" />
      <van-cell
        v-if="isLogin"
        title="主队设置"
        :value="favoriteTeam || '未选择'"
        is-link
        icon="flag-o"
        @click="showTeamPopup = true"
      />
      <van-cell :title="$t('my.settings')" is-link icon="setting-o" @click="goToSettings" />
      </van-cell-group>
    </div>

    <van-popup v-model:show="showTeamPopup" position="bottom" round :style="{ height: '55%' }">
      <div class="popup-title">选择主队</div>
      <div class="team-list">
        <button
          v-for="team in teamOptions"
          :key="team"
          class="team-item"
          :class="{ active: favoriteTeam === team }"
          @click="saveFavoriteTeam(team)"
        >
          ⚽ {{ team }}
        </button>
      </div>
    </van-popup>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useUserStore } from '../store/user';
import { useRouter } from 'vue-router';
import { computed } from 'vue';
import { showToast, showLoadingToast, showSuccessToast, showFailToast } from 'vant';
import { useI18n } from 'vue-i18n';

const userStore = useUserStore();
const router = useRouter();
const { t } = useI18n();

const userInfo = computed(() => userStore.userInfo);
const isLogin = computed(() => userStore.getLoginStatus);
const userBio = computed(() => userStore.getUserBio || t('profile.bio'));
const userAvatar = computed(() => userStore.userInfo?.avatar || 'https://fastly.jsdelivr.net/npm/@vant/assets/cat.jpeg');
const favoriteTeam = computed(() => userStore.userInfo?.favoriteTeam || '');
const showTeamPopup = ref(false);
const savingFavoriteTeam = ref(false);
const teamOptions = ['曼城', '阿森纳', '利物浦', '皇家马德里', '巴塞罗那', '拜仁慕尼黑', '国际米兰', 'AC米兰', '巴黎圣日耳曼', '曼联', '切尔西', '其他球队'];

const goToLogin = () => router.push('/login');
const goToRegister = () => router.push('/register');
const goToProfile = () => isLogin.value && router.push('/profile');
const goToSettings = () => router.push('/settings');

const requireLogin = (target) => {
  if (!isLogin.value) {
    showToast('请先登录');
    router.push('/login');
    return;
  }
  router.push(target);
};

const goToHistory = () => requireLogin('/history');
const goToFavorite = () => requireLogin('/favorite');

const saveFavoriteTeam = async (team) => {
  if (savingFavoriteTeam.value) return;
  savingFavoriteTeam.value = true;
  const result = await userStore.updateUserProfile({ favoriteTeam: team });
  savingFavoriteTeam.value = false;

  if (result.success) {
    showTeamPopup.value = false;
    showSuccessToast('AI 已记住你的主队');
  } else {
    showFailToast(result.message || '保存失败');
  }
};

onMounted(async () => {
  try {
    await userStore.getUserInfoDetail();
  } catch (error) {
    console.error('获取用户信息失败:', error);
  }
});
</script>

<style scoped>
.my-container {
  background-color: var(--background-color);
}

.user-hero {
  min-height: 190px;
}

.user-card {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  padding-top: 0;
}

.avatar {
  margin-right: 16px;
  border: 2px solid rgba(255, 255, 255, .45);
}

.guest-avatar {
  display: grid;
  place-items: center;
  width: 58px;
  height: 58px;
  margin-right: 16px;
  font-size: 25px;
  border-radius: 50%;
  background: rgba(255, 255, 255, .14);
}

.info {
  flex: 1;
}

.username {
  font-size: var(--font-lg);
  font-weight: 750;
  margin-bottom: 4px;
}

.desc,
.guest-desc {
  max-width: 210px;
  font-size: var(--font-sm);
  color: rgba(255, 255, 255, .76);
}

.auth-actions {
  display: flex;
  gap: 8px;
  margin-top: 11px;
}

.auth-button {
  min-width: 72px;
  height: 30px;
  padding: 0 12px;
  font-size: var(--font-sm);
  border: 0;
}

.login-button {
  color: var(--pitch-800);
  background: #fff;
}

.register-button {
  height: 28px;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, .8);
  background: transparent;
}

.arrow-icon {
  color: rgba(255, 255, 255, .8);
}

.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  width: calc(100% - 32px);
  margin: -20px auto 0;
}

.quick-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 7px;
  padding: 15px 0 12px;
  border: 0;
  color: var(--text-color);
  background: transparent;
  font-size: 13px;
}

.quick-icon {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  color: var(--pitch-700);
  font-size: 16px;
  background: var(--secondary-color);
}

.menu-list {
  margin-top: 6px;
}

.popup-title {
  padding: 12px;
  text-align: center;
  font-weight: 700;
}

.team-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 0 12px 16px;
  overflow-y: auto;
}

.team-item {
  padding: 11px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  color: var(--text-color);
  background: var(--card-bg);
  font-size: var(--font-sm);
}

.team-item.active {
  border-color: var(--grass-500);
  color: var(--pitch-700);
  font-weight: 700;
  background: var(--secondary-color);
}
</style>
