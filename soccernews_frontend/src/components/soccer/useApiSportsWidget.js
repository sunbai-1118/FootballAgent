import { onBeforeUnmount } from 'vue'

// 官方 Widget 使用方式：页面声明自定义标签（如 api-games），
// data-url-football 指向后端只读代理，data-key 留空由代理注入真实 Key。
let scriptPromise = null

function loadWidgetScript() {
  if (window.apiSportsWidgetReady) return window.apiSportsWidgetReady
  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/gh/api-football/api-football-docs@main/widgets/api-sports-widget.js'
    script.async = true
    script.onload = () => resolve(window.API_SPORTS)
    script.onerror = () => reject(new Error('Unable to load API-Sports widget'))
    document.head.appendChild(script)
  })
  window.apiSportsWidgetReady = scriptPromise
  return scriptPromise
}

export function useApiSportsWidget() {
  let cancelled = false

  async function mountWidget(widgets) {
    if (!widgets?.length) return
    const widgetList = Array.from(widgets || [])
    widgetList.forEach((widget) => {
      widget.dataset.key = ''
      widget.dataset.urlFootball = '/widget-api/football/'
    })
    await loadWidgetScript()
    const api = window.API_SPORTS
    if (!cancelled && api?.init) {
      api.init({ theme: 'dark', domain: 'api-football.com' })
      api.render()
    }
}

  onBeforeUnmount(() => {
    cancelled = true
  })

  return { mountWidget }
}
