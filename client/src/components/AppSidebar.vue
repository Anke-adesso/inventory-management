<template>
  <aside class="sidebar" :class="{ 'is-collapsed': collapsed }">
    <div class="sidebar__brand">
      <span class="sidebar__mark" aria-hidden="true" @click="onMarkClick">{{ markLetter }}</span>
      <div v-if="!collapsed" class="sidebar__brand-text">
        <span class="sidebar__name">{{ t('nav.companyName') }}</span>
        <span class="sidebar__subtitle">{{ t('nav.subtitle') }}</span>
      </div>
      <button
        v-if="isMobile"
        type="button"
        class="sidebar__close"
        :aria-label="t('nav.closeNavigation')"
        @click="$emit('close')"
      >
        <X :size="18" aria-hidden="true" />
      </button>
    </div>

    <nav class="sidebar__nav" :aria-label="t('nav.mainNavigation')">
      <section v-for="(group, gi) in groups" :key="group.key" class="sidebar__group">
        <h2 v-if="!collapsed" class="sidebar__group-label">{{ t(group.labelKey) }}</h2>
        <hr v-else-if="gi > 0" class="sidebar__divider" />
        <ul class="sidebar__list">
          <li v-for="item in group.items" :key="item.key">
            <SidebarNavItem :item="item" :label="t(item.labelKey)" :collapsed="collapsed" />
          </li>
        </ul>
      </section>
    </nav>

    <div v-if="!isMobile" class="sidebar__footer">
      <button
        type="button"
        class="sidebar__toggle"
        :aria-expanded="String(!collapsed)"
        :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :title="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        @click="$emit('toggle-collapse')"
      >
        <PanelLeftOpen v-if="collapsed" :size="18" aria-hidden="true" />
        <PanelLeftClose v-else :size="18" aria-hidden="true" />
        <span v-if="!collapsed">{{ t('nav.collapse') }}</span>
      </button>
    </div>

    <!-- Teleported: the sidebar clips overflow and the mobile drawer may be transformed. -->
    <Teleport to="body">
      <Transition name="egg-fade">
        <div v-if="eggOpen" class="egg__backdrop" @click="closeEgg">
          <div class="egg__panel" role="dialog" aria-modal="true" :aria-label="t('nav.easterEggAlt')">
            <button
              ref="eggCloseBtn"
              type="button"
              class="egg__close"
              :aria-label="t('nav.easterEggClose')"
              @click="closeEgg"
            >
              <X :size="18" aria-hidden="true" />
            </button>
            <img class="egg__img" :src="EGG_SRC" :alt="t('nav.easterEggAlt')" />
          </div>
        </div>
      </Transition>
    </Teleport>
  </aside>
</template>

<script>
import { computed, ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { PanelLeftClose, PanelLeftOpen, X } from 'lucide-vue-next'
import { useI18n } from '../composables/useI18n'
import { navigationGroups } from '../config/navigation'
import SidebarNavItem from './SidebarNavItem.vue'

export default {
  name: 'AppSidebar',
  components: { SidebarNavItem, PanelLeftClose, PanelLeftOpen, X },
  props: {
    collapsed: { type: Boolean, default: false },
    isMobile: { type: Boolean, default: false }
  },
  emits: ['toggle-collapse', 'close'],
  setup() {
    const { t } = useI18n()
    const groups = navigationGroups
    const markLetter = computed(() => t('nav.companyName').charAt(0))

    // Easter egg: 5 clicks on the brand mark within 2s. The gif is gitignored (third-party
    // artwork), so it may not exist on a fresh clone: preload it and open only on success,
    // otherwise stay silent (no broken image, no empty overlay).
    const EGG_SRC = '/Clawd-Breaking.gif'
    const EGG_CLICKS = 5
    const EGG_WINDOW_MS = 2000
    const eggOpen = ref(false)
    const eggCloseBtn = ref(null)
    let clicks = 0
    let resetTimer = null
    let loading = false

    const resetClicks = () => {
      clicks = 0
      clearTimeout(resetTimer)
      resetTimer = null
    }

    const closeEgg = () => { eggOpen.value = false }

    const onKeydown = (e) => { if (e.key === 'Escape') closeEgg() }

    const triggerEgg = () => {
      if (loading || eggOpen.value) return
      loading = true
      const img = new Image()
      img.onload = () => {
        loading = false
        eggOpen.value = true
        nextTick(() => eggCloseBtn.value && eggCloseBtn.value.focus())
      }
      img.onerror = () => { loading = false }
      img.src = EGG_SRC
    }

    const onMarkClick = () => {
      // Window starts at the first click; later clicks don't extend it.
      if (clicks === 0) resetTimer = setTimeout(resetClicks, EGG_WINDOW_MS)
      clicks += 1
      if (clicks >= EGG_CLICKS) {
        resetClicks()
        triggerEgg()
      }
    }

    // Listener only lives while the overlay is open.
    watch(eggOpen, (open) => {
      if (open) document.addEventListener('keydown', onKeydown)
      else document.removeEventListener('keydown', onKeydown)
    })

    onBeforeUnmount(() => {
      clearTimeout(resetTimer)
      document.removeEventListener('keydown', onKeydown)
    })

    return { t, groups, markLetter, EGG_SRC, eggOpen, eggCloseBtn, onMarkClick, closeEgg }
  }
}
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--color-nav-bg);
  border-right: 1px solid var(--color-border-2);
  overflow: hidden;
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  height: var(--shell-topbar-h);
  padding: 0 var(--space-3);
  border-bottom: 1px solid var(--color-border-2);
  flex-shrink: 0;
}
.is-collapsed .sidebar__brand { justify-content: center; padding: 0; }
.sidebar__mark {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-on-accent);
  font-weight: 600;
  font-size: var(--text-sm);
  flex-shrink: 0;
}
.sidebar__brand-text { display: flex; flex-direction: column; min-width: 0; }
.sidebar__name {
  font-size: var(--text-lg);
  line-height: 20px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sidebar__subtitle {
  font-size: var(--text-xs);
  line-height: 16px;
  color: var(--color-text-mid);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sidebar__close {
  display: grid;
  place-items: center;
  margin-left: auto;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-mid);
  cursor: pointer;
}
.sidebar__close:hover { background: var(--color-surface-2); color: var(--color-text); }

.sidebar__nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) var(--space-2);
}
.sidebar__group + .sidebar__group { margin-top: var(--space-6); }
.sidebar__group-label {
  margin: 0 0 var(--space-2);
  padding: 0 var(--space-3);
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-text-dim);
}
.sidebar__divider {
  margin: 0 var(--space-3) var(--space-4);
  border: 0;
  border-top: 1px solid var(--color-border-2);
}
.sidebar__list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar__footer {
  padding: var(--space-2);
  border-top: 1px solid var(--color-border-2);
  flex-shrink: 0;
}
.sidebar__toggle {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  height: 36px;
  padding: 0 var(--space-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-mid);
  font: inherit;
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: background var(--dur-fast);
}
.is-collapsed .sidebar__toggle { justify-content: center; padding: 0; }
.sidebar__toggle:hover { background: var(--color-surface-2); color: var(--color-text); }

/* Easter egg overlay (teleported, so scoped styles still apply via data attribute) */
.egg__backdrop {
  position: fixed;
  inset: 0;
  z-index: 2100; /* above modals (1000-2000) */
  display: grid;
  place-items: center;
  padding: var(--space-4);
  /* No scrim: the gif has a transparent background and floats over the app.
     The layer still covers the page so any click dismisses it. */
  background: transparent;
}
.egg__panel {
  position: relative;
  width: min(420px, 100%);
}
.egg__img {
  display: block;
  width: 100%;
  height: auto;
}
/* Visually hidden but still focusable for screen readers: without a panel a
   visible X floats detached from the gif. Esc or any click closes as well. */
.egg__close {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}
.egg-fade-enter-active,
.egg-fade-leave-active { transition: opacity var(--dur-base) var(--ease-out); }
.egg-fade-enter-from,
.egg-fade-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .egg-fade-enter-active,
  .egg-fade-leave-active { transition: none; }
}
</style>
