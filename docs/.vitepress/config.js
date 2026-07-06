import { defineConfig } from 'vitepress'

const enGuide = [
  { text: 'Overview', link: '/en/' },
  { text: 'Getting Started', link: '/en/guide/getting-started' },
  { text: 'Architecture', link: '/en/guide/architecture' },
  { text: 'Configuration', link: '/en/guide/configuration' },
  { text: 'Hardware', link: '/en/guide/hardware' },
  { text: 'Development', link: '/en/guide/development' },
  { text: 'Reference Index', link: '/en/reference/' }
]

const zhGuide = [
  { text: 'Overview', link: '/zh/' },
  { text: 'Getting Started', link: '/zh/guide/getting-started' },
  { text: 'Architecture', link: '/zh/guide/architecture' },
  { text: 'Configuration', link: '/zh/guide/configuration' },
  { text: 'Hardware', link: '/zh/guide/hardware' },
  { text: 'Development', link: '/zh/guide/development' },
  { text: 'Reference Index', link: '/zh/reference/' }
]

export default defineConfig({
  title: 'CH-RO Robot',
  description: 'Documentation for the Xiangqi robot system',
  cleanUrls: true,
  lastUpdated: true,
  locales: {
    root: {
      label: 'English',
      lang: 'en-US',
      themeConfig: {
        nav: [
          { text: 'Guide', link: '/en/guide/getting-started' },
          { text: 'Architecture', link: '/en/guide/architecture' },
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
          { text: 'Guide', link: '/zh/guide/getting-started' },
          { text: 'Architecture', link: '/zh/guide/architecture' },
          { text: 'English', link: '/en/' }
        ],
        sidebar: {
          '/zh/': [{ text: 'Guide', items: zhGuide }]
        }
      }
    }
  },
  themeConfig: {
    search: { provider: 'local' },
    socialLinks: []
  }
})
