<template>
  <aside class="sidebar" :class="{ 'is-collapsed': collapsed }">
    <div class="sidebar__brand">
      <span class="sidebar__mark" aria-hidden="true">{{ markLetter }}</span>
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
  </aside>
</template>

<script>
import { computed } from 'vue'
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
    return { t, groups, markLetter }
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
</style>
