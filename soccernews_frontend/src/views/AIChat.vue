<template>
  <div class="ai-chat-container">
    <van-nav-bar>
      <template #left>
        <div class="nav-brand">
          <span class="brand-mark">🤖</span>
          <span class="brand-name">足球AI助手</span>
        </div>
      </template>
      <template #right>
        <van-icon name="replay" size="18" @click="startNewSession" />
      </template>
    </van-nav-bar>

    <div class="chat-content">
      <div class="messages-container" ref="messagesContainer">
        <div
          v-for="(message, index) in messages"
          :key="index"
          :class="['message', message.role === 'user' ? 'user-message' : 'ai-message']"
        >
          <div class="message-content">
            <!-- 工具调用过程卡片 -->
            <div v-if="message.role === 'assistant' && message.tools && message.tools.length" class="tool-steps">
              <div v-for="t in message.tools" :key="t.name" class="tool-step" :class="{ done: t.done }">
                <van-icon :name="t.done ? 'passed' : 'loading'" class="tool-icon" />
                <span>{{ t.label }}</span>
              </div>
            </div>
            <!-- 流式中:无文本显示打字动画,有文本显示原始文本 -->
            <div v-if="message.role === 'assistant' && message.streaming && !message.raw" class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div v-else-if="message.role === 'assistant' && message.streaming && message.raw" class="streaming-text">{{ message.raw }}</div>
            <div v-else v-html="formatMessage(message.content)"></div>
          </div>
          <!-- 反馈行:回答完成后显示 👍/👎 + Verifier 校验标记 -->
          <div v-if="message.role === 'assistant' && message.chatId && !message.streaming" class="feedback-row">
            <span
              v-if="message.verified"
              class="verified-tag"
              :class="{ warn: !message.verified.grounded }"
              :title="message.verified.note"
            >{{ message.verified.grounded ? '已校验' : '已修正' }}</span>
            <button class="fb-btn" :class="{ active: message.feedback === 'up' }" @click="sendFeedback(message, 'up')">👍</button>
            <button class="fb-btn" :class="{ active: message.feedback === 'down' }" @click="sendFeedback(message, 'down')">👎</button>
          </div>
        </div>
      </div>

      <div class="input-container">
        <van-field
          v-model="userInput"
          rows="1"
          autosize
          type="textarea"
          :placeholder="$t('aiChat.placeholder')"
          class="chat-input"
          @keypress.enter.prevent="sendMessage"
        />
        <van-button
          type="primary"
          class="send-button"
          :disabled="isLoading || !userInput.trim()"
          @click="sendMessage"
        >
          发送
        </van-button>
      </div>
    </div>

    <div class="login-hint" v-if="!userStore.getLoginStatus">
      <p>登录后可询问比赛、球员、战术与本站新闻</p>
      <van-button round type="primary" size="small" @click="router.push('/login')">去登录</van-button>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue';
import { showToast } from 'vant';
import { useRouter } from 'vue-router';
import * as marked from 'marked';
import DOMPurify from 'dompurify';
import { apiConfig } from '../config/api';
import { useUserStore } from '../store/user';

// 工具名 -> 友好中文标签
const TOOL_LABELS = {
  retrieve_news_tool: '检索本站新闻库',
  retrieve_images_tool: '检索新闻图片',
  search_news: '搜索新闻',
  get_news_detail: '读取新闻详情',
  get_hot_news: '拉取热门新闻',
  get_my_favorites: '读取我的收藏',
  get_my_history: '读取浏览历史',
  get_match_result: '查询实时比赛数据',
  get_match_pick: '获取球队/球员图片',
  web_search: '联网搜索',
  remember: '记住偏好',
};

// 聊天消息
const messages = ref([
  { role: 'assistant', content: '你好！我是⚽足球资讯助手，英超、西甲、欧冠、世界杯……你想聊哪场比赛或哪支球队？' }
]);
const userInput = ref('');
const messagesContainer = ref(null);
const isLoading = ref(false);

const userStore = useUserStore();
const router = useRouter();

// 会话ID:持久化到 localStorage(按用户隔离),刷新页面后恢复对话上下文
const sessionKey = () => `ai_chat_session_${userStore.userInfo?.id || 'anon'}`;
const chatSessionId = ref(localStorage.getItem(sessionKey()) || null);
const setSession = (sid) => {
  chatSessionId.value = sid;
  if (sid) localStorage.setItem(sessionKey(), sid);
};

// 格式化消息内容（支持Markdown）
const formatMessage = (content) => {
  if (!content) return '';
  return DOMPurify.sanitize(marked.parse(content));
};

// 处理一条 SSE 事件
const handleEvent = (data, aiIndex) => {
  const msg = messages.value[aiIndex];
  switch (data.type) {
    case 'session':
      setSession(data.sessionId);
      break;
    case 'tool_call':
      console.log('[agent] 调用工具:', data.tool);
      msg.tools = (data.tool || []).map(name => ({
        name,
        label: TOOL_LABELS[name] || name,
        done: false,
      }));
      break;
    case 'tool_done':
      if (msg.tools) {
        const t = msg.tools.find(x => x.name === data.tool);
        if (t) t.done = true;
      }
      break;
    case 'token':
      msg.raw = (msg.raw || '') + data.content;
      break;
    case 'done':
      msg.raw = data.reply || msg.raw;
      msg.content = data.reply || msg.raw; // 触发最终 Markdown 渲染(含图片)
      msg.streaming = false;
      msg.chatId = data.chatId;      // 关联反馈
      msg.verified = data.verified || null; // Verifier 校验信息 {grounded, note}
      setSession(data.sessionId);
      console.log('[agent] 完成 reply_len=', msg.content?.length, 'verified=', data.verified);
      break;
    case 'error':
      msg.content = `发生错误: ${data.message}`;
      msg.streaming = false;
      break;
  }
  nextTick(scrollToBottom);
};

// 发送消息(SSE 流式)
const sendMessage = async () => {
  if (!userInput.value.trim() || isLoading.value) return;

  // 检查登录状态（AI接口需要登录）
  if (!userStore.getLoginStatus || !userStore.token) {
    showToast('请先登录后再使用AI问答');
    return;
  }

  const userMessage = userInput.value.trim();
  messages.value.push({ role: 'user', content: userMessage });
  userInput.value = '';

  // AI 消息占位（流式）
  const aiIndex = messages.value.length;
  messages.value.push({ role: 'assistant', content: '', raw: '', streaming: true, tools: [] });
  isLoading.value = true;
  console.log('[agent] 流式对话开始, sessionId=', chatSessionId.value);
  await nextTick();
  scrollToBottom();

  try {
    const resp = await fetch(`${apiConfig.baseURL}/api/ai/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': userStore.token,
      },
      body: JSON.stringify({
        message: userMessage,
        sessionId: chatSessionId.value,
      }),
    });
    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}：${resp.statusText}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buf = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      // SSE 帧以空行分隔
      const frames = buf.split('\n\n');
      buf = frames.pop();
      for (const frame of frames) {
        for (const line of frame.split('\n')) {
          if (line.startsWith('data:')) {
            handleEvent(JSON.parse(line.slice(5).trim()), aiIndex);
          }
        }
      }
    }
    // 处理末尾残留帧
    if (buf.includes('data:')) {
      for (const line of buf.split('\n')) {
        if (line.startsWith('data:')) {
          handleEvent(JSON.parse(line.slice(5).trim()), aiIndex);
        }
      }
    }
  } catch (error) {
    console.error('AI 流式请求失败:', error);
    const msg = error.response?.data?.message || error.message || 'AI服务暂时不可用，请稍后再试';
    messages.value[aiIndex].content = `发生错误: ${msg}`;
    messages.value[aiIndex].streaming = false;
  } finally {
    isLoading.value = false;
    await nextTick();
    scrollToBottom();
  }
};

// 提交回答反馈(👍/👎)，用于优化 Prompt/RAG/Tool
const sendFeedback = async (msg, score) => {
  if (!msg.chatId) {
    showToast('该回答无法关联反馈');
    return;
  }
  if (!userStore.getLoginStatus || !userStore.token) {
    showToast('请先登录');
    return;
  }
  msg.feedback = score;
  try {
    const resp = await fetch(`${apiConfig.baseURL}/api/ai/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': userStore.token },
      body: JSON.stringify({ chatId: msg.chatId, score }),
    });
    const json = await resp.json();
    showToast(json.message || (score === 'up' ? '已点赞 👍' : '已点踩 👎'));
  } catch (error) {
    console.error('提交反馈失败:', error);
    showToast('反馈提交失败');
    msg.feedback = null;
  }
};

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

// 监听消息变化，自动滚动
watch(messages, () => {
  nextTick(scrollToBottom);
}, { deep: true });

const startNewSession = () => {
  messages.value = [
    { role: 'assistant', content: '你好！我是⚽足球资讯助手，英超、西甲、欧冠、世界杯……你想聊哪场比赛或哪支球队？' }
  ];
  chatSessionId.value = null;
  localStorage.removeItem(sessionKey());
};

// 刷新页面后恢复对话历史
const restoreHistory = async () => {
  const sid = chatSessionId.value;
  if (!sid || !userStore.getLoginStatus || !userStore.token) return;
  try {
    const resp = await fetch(
      `${apiConfig.baseURL}/api/ai/history?sessionId=${encodeURIComponent(sid)}`,
      { headers: { Authorization: userStore.token } }
    );
    const json = await resp.json();
    if (json.code === 200 && json.data?.messages?.length) {
      messages.value = json.data.messages.map(m => ({ role: m.role, content: m.content }));
      if (messages.value.length >= 2) {
        const latest = messages.value[messages.value.length - 1];
        latest.chatId = `history-${Date.now()}`;
        latest.feedback = null;
      }
    } else {
      // 会话已失效:清除本地 sessionId,回到欢迎语
      chatSessionId.value = null;
      localStorage.removeItem(sessionKey());
    }
  } catch (error) {
    console.error('恢复对话历史失败:', error);
  }
  await nextTick();
  scrollToBottom();
};

// 组件挂载时滚动到底部,并尝试恢复对话
onMounted(async () => {
  scrollToBottom();
  await restoreHistory();
});
</script>

<style scoped>
.ai-chat-container {
  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100dvh - 56px - var(--safe-area-inset-bottom));
  min-height: 0;
  overflow: hidden;
  box-sizing: border-box;
}

.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 8px 10px;
}

.message {
  margin-bottom: 7px;
  max-width: 88%;
}

.user-message {
  margin-left: auto;
}

.ai-message {
  margin-right: auto;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-name {
  color: var(--white);
  font-size: var(--font-md);
  font-weight: 750;
}

.brand-mark {
  width: 28px;
  height: 28px;
  font-size: 16px;
}

.login-hint {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: min(76vw, 270px);
  padding: 18px 15px 16px;
  text-align: center;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, .95);
  color: var(--text-color-light);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(12px);
}

.login-hint p {
  margin-bottom: 11px;
  font-size: var(--font-sm);
  line-height: 1.5;
}

.message-content {
  padding: 8px 10px;
  border-radius: var(--radius);
  font-size: var(--font-sm);
  line-height: 1.6;
  word-break: break-word;
  box-shadow: var(--shadow-sm);
}

.user-message .message-content {
  border-bottom-right-radius: 6px;
  background: linear-gradient(120deg, var(--pitch-800), var(--grass-500));
  color: white;
}

.ai-message .message-content {
  border-bottom-left-radius: 6px;
  background-color: var(--card-bg);
  color: var(--text-color);
}

.input-container {
  display: flex;
  gap: 7px;
  align-items: flex-end;
  padding: 7px 8px;
  border-top: 1px solid rgba(219, 231, 224, .7);
  background: rgba(255, 255, 255, .96);
  backdrop-filter: blur(16px);
}

.chat-input {
  flex: 1;
  margin-right: 7px;
  --van-field-background: #fff;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  overflow: hidden;
}

.send-button {
  align-self: flex-end;
  --van-button-small-height: 30px;
  --van-button-normal-height: 30px;
  padding: 0 12px;
  font-size: var(--font-sm);
}

/* 工具调用过程卡片 */
.tool-steps {
  margin-bottom: 5px;
}

.tool-step {
  display: flex;
  align-items: center;
  font-size: var(--font-xs);
  color: var(--text-color-light);
  padding: 3px 0;
}

.tool-step.done {
  color: var(--grass-500);
}

.tool-icon {
  margin-right: 5px;
  font-size: 13px;
}

/* 流式文本(渲染为纯文本,结束后切换为 Markdown) */
.streaming-text {
  white-space: pre-wrap;
}

/* 反馈行(👍/👎 + Verifier 校验标记) */
.feedback-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  padding: 0 4px;
}

.fb-btn {
  border: none;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  opacity: 0.6;
}

.fb-btn.active {
  opacity: 1;
  background: rgba(0, 184, 108, .12);
}

.verified-tag {
  font-size: 11px;
  color: var(--pitch-700);
  background: rgba(0, 184, 108, .12);
  padding: 1px 6px;
  border-radius: 999px;
  margin-right: 4px;
}

.verified-tag.warn {
  color: #d64b2c;
  background: rgba(238, 10, 36, .08);
}

/* Markdown 样式 */
.message-content pre {
  background-color: #f8f8f8;
  padding: 10px;
  border-radius: 5px;
  overflow-x: auto;
}

.message-content code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}

.message-content img {
  max-width: 100%;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  padding: 5px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  background-color: #999;
  border-radius: 50%;
  margin: 0 2px;
  display: inline-block;
  animation: bounce 1.5s infinite ease-in-out;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-5px);
  }
}

/* Markdown样式 */
:deep(pre) {
  background-color: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

:deep(code) {
  font-family: monospace;
  background-color: #f0f0f0;
  padding: 2px 4px;
  border-radius: 4px;
}

:deep(p) {
  margin: 8px 0;
}

:deep(ul), :deep(ol) {
  padding-left: 20px;
}

:deep(a) {
  color: var(--pitch-700);
  text-decoration: none;
}
</style>
