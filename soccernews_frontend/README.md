# ⚽ 足球头条 (xwzx-news)

一款基于 **Vue 3 + Vite + Vant** 的移动端足球新闻资讯应用，支持新闻浏览、收藏、历史记录、AI 智能问答以及账号体系。

## ✨ 功能特性

- 📰 **新闻资讯**：首页 / 分类浏览体育新闻，支持下拉刷新与分页加载
- 📄 **新闻详情**：Markdown 内容渲染（`marked` + `DOMPurify` 净化），安全可靠
- ⭐ **收藏与历史**：本地记录 + 登录后与后端同步
- 🤖 **AI 智能对话**：基于账号体系的 AI 问答会话
- 👤 **用户系统**：注册、登录、个人资料、修改密码、设置
- 🌐 **多语言**：内置简体中文 / English（`vue-i18n`）
- 🎨 **个性化**：明暗主题切换，语言偏好持久化
- 📱 **移动端优先**：基于 Vant 4 组件库，适配移动端体验

## 🛠 技术栈

| 分类 | 技术 |
| --- | --- |
| 框架 | [Vue 3](https://vuejs.org/) |
| 构建工具 | [Vite](https://vitejs.dev/) |
| 路由 | [Vue Router 4](https://router.vuejs.org/) |
| 状态管理 | [Pinia](https://pinia.vuejs.org/)（持久化：`pinia-plugin-persistedstate`） |
| UI 组件 | [Vant 4](https://vant-ui.github.io/vant/) |
| 网络请求 | [Axios](https://axios-http.com/) |
| 国际化 | [vue-i18n](https://vue-i18n.intlify.dev/) |
| 富文本 | [marked](https://marked.js.org/) + [DOMPurify](https://github.com/cure53/DOMPurify) |

## 🚀 快速开始

### 环境要求

- Node.js ≥ 18
- npm / pnpm / yarn

### 安装依赖

```bash
npm install
```

### 启动开发服务

```bash
npm run dev
```

### 生产构建

```bash
npm run build
```

### 本地预览构建产物

```bash
npm run preview
```

## 📁 项目结构

```
├── src/
│   ├── assets/            # 静态资源
│   ├── components/        # 通用组件（TabBar、NewsItem 等）
│   ├── config/
│   │   └── api.js         # 后端 API 基础地址配置
│   ├── i18n/              # 国际化（zh-CN / en-US）
│   ├── router/            # 路由配置
│   ├── store/             # Pinia 状态管理（user、news、favorite、history、theme、language）
│   ├── views/             # 页面组件（Home、NewsDetail、AIChat、Login 等）
│   ├── App.vue
│   ├── main.js
│   └── style.css
├── public/                # 公共静态资源
├── index.html
├── vite.config.js
└── package.json
```

## ⚙️ 接口配置

后端 API 基础地址在 [`src/config/api.js`](src/config/api.js) 中配置，默认为本地开发地址：

```js
export const apiConfig = {
  baseURL: 'http://127.0.0.1:8000',
}
```

> 建议通过环境变量（`.env.local`）覆盖，避免将真实后端地址写入源码。

## 📄 License

暂无开源许可证（保留所有权利）。如需开源，请在仓库中补充相应的 LICENSE 文件。
