<template>
  <AppShell>
    <template #topbar>
      <LanguageSwitcher />
      <ProfileMenu
        @show-profile-details="showProfileDetails = true"
        @show-tasks="showTasks = true"
      />
    </template>

    <template #toolbar>
      <FilterBar />
    </template>

    <router-view />
  </AppShell>

  <ProfileDetailsModal
    :is-open="showProfileDetails"
    @close="showProfileDetails = false"
  />

  <TasksModal
    :is-open="showTasks"
    :tasks="tasks"
    @close="showTasks = false"
    @add-task="addTask"
    @delete-task="deleteTask"
    @toggle-task="toggleTask"
  />
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import AppShell from './components/AppShell.vue'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    AppShell,
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* Global base (box-sizing, body, height chain, focus ring) lives in styles/theme.css. */
* {
  margin: 0;
  padding: 0;
}

/* ---- Page header (shared by every routed view) ------------------------- */
.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2) var(--space-4);
  margin-bottom: var(--space-6);
}

/* Accent rule marks the page title; the one place the accent is decorative */
.page-header h2 {
  flex: 1 1 auto;
  padding-left: var(--space-3);
  border-left: 3px solid var(--color-accent);
  min-width: 0;
  font-size: var(--text-xl);
  line-height: 28px;
  font-weight: 600;
  color: var(--color-text);
}

.page-header p {
  flex-basis: 100%;
  order: 3;
  color: var(--color-text-mid);
  font-size: var(--text-sm);
  line-height: 20px;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-left: auto;
}

/* ---- Stats ------------------------------------------------------------- */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.stat-card {
  background: var(--color-surface);
  padding: var(--space-4) var(--space-6);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-2);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--dur-fast), box-shadow var(--dur-fast);
}

.stat-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-md);
}

.stat-label {
  color: var(--color-text-mid);
  font-size: var(--text-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: var(--text-2xl);
  line-height: 32px;
  font-weight: 600;
  color: var(--color-text);
  font-variant-numeric: tabular-nums;
}

.stat-card.warning .stat-value { color: var(--color-warning); }
.stat-card.success .stat-value { color: var(--color-success); }
.stat-card.danger .stat-value { color: var(--color-danger); }
.stat-card.info .stat-value { color: var(--color-info); }

/* ---- Cards ------------------------------------------------------------- */
.card {
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-6);
  border: 1px solid var(--color-border-2);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-2);
}

.card-title {
  font-size: var(--text-lg);
  line-height: 24px;
  font-weight: 600;
  color: var(--color-text);
}

@media (max-width: 767px) {
  .card { padding: var(--space-4); }
}

/* ---- Tables ------------------------------------------------------------ */
.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}

thead {
  background: var(--color-surface-3);
  border-top: 1px solid var(--color-border-2);
  border-bottom: 1px solid var(--color-border-2);
}

th {
  text-align: left;
  padding: var(--space-3);
  font-weight: 600;
  color: var(--color-text-mid);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

td {
  height: 44px;
  padding: var(--space-3);
  border-top: 1px solid var(--color-surface-2);
  color: var(--color-text);
  font-size: var(--text-sm);
}

td strong {
  white-space: nowrap;
}

tbody tr {
  transition: background-color var(--dur-fast);
}

tbody tr:hover {
  background: var(--color-surface-2);
}

/* ---- Badges ------------------------------------------------------------ */
.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  white-space: nowrap;
}

.badge.success,
.badge.increasing {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.badge.warning,
.badge.medium {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}

.badge.danger,
.badge.decreasing,
.badge.high {
  background: var(--color-danger-bg);
  color: var(--color-danger);
}

.badge.info,
.badge.low {
  background: var(--color-info-bg);
  color: var(--color-info);
}

.badge.stable {
  background: var(--color-surface-2);
  color: var(--color-text-mid);
}

/* ---- States ------------------------------------------------------------ */
.loading {
  text-align: center;
  padding: var(--space-12);
  color: var(--color-text-mid);
  font-size: var(--text-base);
}

.error {
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  color: var(--color-danger);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  margin: var(--space-4) 0;
  font-size: var(--text-base);
}
</style>
