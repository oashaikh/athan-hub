import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './pages/Dashboard.vue'
import Settings from './pages/Settings.vue'
import QuranPractice from './pages/QuranPractice.vue'
import AdminLayout from './pages/AdminLayout.vue'
import AdminHome from './pages/AdminHome.vue'
import AdminProfiles from './pages/AdminProfiles.vue'
import AdminQuranCache from './pages/AdminQuranCache.vue'
import AdminQuranSources from './pages/AdminQuranSources.vue'
import '@fontsource/inter/latin-400.css'
import '@fontsource/inter/latin-500.css'
import '@fontsource/inter/latin-600.css'
import '@fontsource/inter/latin-700.css'
import '@fontsource/manrope/latin-500.css'
import '@fontsource/manrope/latin-600.css'
import '@fontsource/manrope/latin-700.css'
import '@fontsource/manrope/latin-800.css'
import '@fontsource/material-icons'
import '@fontsource/noto-naskh-arabic/arabic-400.css'
import '@fontsource/noto-naskh-arabic/arabic-600.css'
import './styles/bulma.scss'
import './styles/themes.scss'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'dashboard', component: Dashboard },
    { path: '/quran', name: 'quran', component: QuranPractice },
    { path: '/settings', redirect: '/admin/timetable' },
    { path: '/admin', component: AdminLayout, meta: { admin: true }, children: [
      { path: '', name: 'admin', component: AdminHome },
      { path: 'profiles', name: 'admin-profiles', component: AdminProfiles },
      { path: 'system', redirect: '/admin/general' },
      { path: 'timetable', name: 'admin-timetable', component: Settings, props: { forcedTab: 'timetable' } },
      { path: 'bluetooth', name: 'admin-bluetooth', component: Settings, props: { forcedTab: 'bluetooth' } },
      { path: 'activity', name: 'admin-activity', component: Settings, props: { forcedTab: 'activity' } },
      { path: 'exclusions', name: 'admin-exclusions', component: Settings, props: { forcedTab: 'exclusions' } },
      { path: 'audio', name: 'admin-audio', component: Settings, props: { forcedTab: 'audio' } },
      { path: 'general', name: 'admin-general', component: Settings, props: { forcedTab: 'general' } },
      { path: 'quran-cache', name: 'admin-quran', component: AdminQuranCache },
      { path: 'quran-sources', name: 'admin-quran-sources', component: AdminQuranSources }
    ] }
  ]
})

createApp(App).use(router).mount('#app')
