import { defineConfig } from 'vitepress'

const enGuide = [
  { text: 'Overview', link: '/en/' },
  { text: 'Getting Started', link: '/en/guide/getting-started' },
  { text: 'Architecture', link: '/en/guide/architecture' },
  { text: 'Configuration', link: '/en/guide/configuration' },
  { text: 'Hardware', link: '/en/guide/hardware' },
  { text: 'Development', link: '/en/guide/development' },
  { text: 'REST API', link: '/en/reference/api' },
  { text: 'Reference Index', link: '/en/reference/' },
  { text: 'Academic Paper', link: '/en/paper' }
]

const zhGuide = [
  { text: '总览', link: '/zh/' },
  { text: '快速开始', link: '/zh/guide/getting-started' },
  { text: '系统架构', link: '/zh/guide/architecture' },
  { text: '配置说明', link: '/zh/guide/configuration' },
  { text: '硬件与固件', link: '/zh/guide/hardware' },
  { text: '开发指南', link: '/zh/guide/development' },
  { text: 'REST API', link: '/zh/reference/api' },
  { text: '参考索引', link: '/zh/reference/' },
  { text: '学术论文', link: '/zh/paper' }
]

export default defineConfig({
  title: 'CH-RO Robot',
  description: 'Documentation for the Xiangqi robot system',
  base: '/chch-robot/',
  cleanUrls: true,
  lastUpdated: true,
  ignoreDeadLinks: true,
  locales: {
    root: {
      label: 'English',
      lang: 'en-US',
      themeConfig: {
        nav: [
          { text: 'Guide', link: '/en/guide/getting-started' },
          { text: 'Architecture', link: '/en/guide/architecture' },
          { text: 'API', link: '/en/reference/api' },
          { text: 'Paper', link: '/en/paper' },
          { text: 'Chinese', link: '/zh/' }
        ],
        sidebar: {
          '/en/': [{ text: 'Guide', items: enGuide }]
        }
      }
    },
    zh: {
      label: 'Chinese',
      lang: 'zh-CN',
      link: '/zh/',
      themeConfig: {
        nav: [
          { text: '指南', link: '/zh/guide/getting-started' },
          { text: '架构', link: '/zh/guide/architecture' },
          { text: 'API', link: '/zh/reference/api' },
          { text: '论文', link: '/zh/paper' },
          { text: 'English', link: '/en/' }
        ],
        sidebar: {
          '/zh/': [{ text: '指南', items: zhGuide }]
        }
      }
    }
  },
  themeConfig: {
    search: { provider: 'local' },
    socialLinks: []
  }
})
