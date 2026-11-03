<template>
  <div
    class="shell"
    :class="{ 'is-collapsed': collapsed && !isMobile, 'is-mobile': isMobile, 'is-drawer-open': mobileOpen }"
  >
    <a href="#main-content" class="skip-link">{{ t('nav.skipToContent') }}</a>

    <AppSidebar
      ref="sidebar"
      class="shell__sidebar"
      :collapsed="collapsed && !isMobile"
      :is-mobile="isMobile"
      :inert="isMobile && !mobileOpen ? '' : undefined"
      @toggle-collapse="collapsed = !collapsed"
      @close="mobileOpen = false"
    />

    <div v-if="isMobile && mobileOpen" class="shell__backdrop" @click="mobileOpen = false" />

    <div class="shell__main">
      <AppTopbar
        ref="topbar"
        :title="pageTitle"
        :show-menu-button="isMobile"
        :menu-open="mobileOpen"
        @open-menu="mobileOpen = true"
      >
        <slot name="topbar" />
      </AppTopbar>

      <main id="main-content" class="shell__content" tabindex="-1">
        <slot name="toolbar" />
        <div class="shell__content-inner">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import { navigationItems } from '../config/navigation'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'

const STORAGE_KEY = 'sidebar-collapsed'
const FOCUSABLE = 'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'

const readCollapsed = () => {
  let saved = null
  try { saved = localStorage.getItem(STORAGE_KEY) } catch (e) { /* storage unavailable */ }
  if (saved !== null) return saved === '1'
  // No stored preference: tablets (768-1023px) start collapsed.
  return window.matchMedia('(max-width: 1023px)').matches
}

export default {
  name: 'AppShell',
  components: { AppSidebar, AppTopbar },
  setup() {
    const route = useRoute()
    const { t } = useI18n()

    const collapsed = ref(readCollapsed())
    const mobileOpen = ref(false)
    const mq = window.matchMedia('(max-width: 767px)')
    const isMobile = ref(mq.matches)
    const sidebar = ref(null)
    const topbar = ref(null)

    const pageTitle = computed(() => {
      const current = navigationItems.find(i => i.to === route.path)
      return current ? t(current.labelKey) : t('nav.companyName')
    })

    const onMq = () => {
      isMobile.value = mq.matches
      if (!mq.matches) mobileOpen.value = false
    }
    onMounted(() => mq.addEventListener('change', onMq))

    watch(collapsed, (v) => {
      try { localStorage.setItem(STORAGE_KEY, v ? '1' : '0') } catch (e) { /* ignore */ }
    })
    watch(() => route.fullPath, () => { mobileOpen.value = false })

    // Drawer: Esc closes, Tab is trapped inside, focus returns to the hamburger.
    const onKey = (e) => {
      if (e.key === 'Escape') { mobileOpen.value = false; return }
      if (e.key !== 'Tab') return
      const root = sidebar.value?.$el
      const els = root ? Array.from(root.querySelectorAll(FOCUSABLE)) : []
      if (!els.length) return
      const first = els[0]
      const last = els[els.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
      else if (!root.contains(document.activeElement)) { e.preventDefault(); first.focus() }
    }

    watch(mobileOpen, async (open) => {
      if (open) {
        document.addEventListener('keydown', onKey)
        await nextTick()
        sidebar.value?.$el?.querySelector(FOCUSABLE)?.focus()
      } else {
        document.removeEventListener('keydown', onKey)
        // Focus returns to the hamburger (the drawer is inert and hidden once closed).
        topbar.value?.focusMenuButton()
      }
    })

    onBeforeUnmount(() => {
      mq.removeEventListener('change', onMq)
      document.removeEventListener('keydown', onKey)
    })

    return { t, collapsed, mobileOpen, isMobile, pageTitle, sidebar, topbar }
  }
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--shell-sidebar-w) minmax(0, 1fr);
  height: 100%;
  overflow: hidden;
  transition: grid-template-columns var(--dur-base) var(--ease-out);
}
.shell.is-collapsed { grid-template-columns: var(--shell-sidebar-w-collapsed) minmax(0, 1fr); }
.shell.is-mobile { grid-template-columns: minmax(0, 1fr); }

.shell__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.shell__content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: var(--color-bg);
}
.shell__content:focus { outline: none; box-shadow: none; }
.shell__content-inner {
  max-width: var(--shell-content-max);
  margin: 0 auto;
  padding: var(--shell-content-pad);
}

/* Mobile drawer */
.shell.is-mobile .shell__sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  width: var(--shell-sidebar-w);
  max-width: 85vw;
  z-index: var(--z-drawer);
  transform: translateX(-100%);
  visibility: hidden;
  transition: transform var(--dur-base) var(--ease-out), visibility 0s linear var(--dur-base);
}
.shell.is-mobile.is-drawer-open .shell__sidebar {
  transform: translateX(0);
  visibility: visible;
  box-shadow: var(--shadow-lg);
  transition: transform var(--dur-base) var(--ease-out);
}
.shell__backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-backdrop);
  background: rgba(26, 26, 26, 0.32);
}

.skip-link {
  position: absolute;
  left: var(--space-2);
  top: -100px;
  z-index: 100;
  padding: var(--space-2) var(--space-4);
  background: var(--color-surface);
  color: var(--color-accent);
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}
.skip-link:focus { top: var(--space-2); }
</style>
