<template>
  <div class="reports">
    <div class="page-header">
      <h2>{{ t('reports.title') }}</h2>
      <p>{{ t('reports.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="isEmpty" class="card empty-state">
      <CodyMascot moment="shrug" :size="96" class="empty-cody" />
      {{ t('reports.empty') }}
    </div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.quarterly.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.quarterly.quarter') }}</th>
                <th>{{ t('reports.quarterly.totalOrders') }}</th>
                <th>{{ t('reports.quarterly.totalRevenue') }}</th>
                <th>{{ t('reports.quarterly.avgOrderValue') }}</th>
                <th>{{ t('reports.quarterly.fulfillmentRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in quarterlyData" :key="q.quarter">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>{{ formatCurrency(q.total_revenue) }}</td>
                <td>{{ formatCurrencyDecimals(q.avg_order_value) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.trend.title') }}</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="month in monthlyData" :key="month.month" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="formatCurrencyDecimals(month.revenue)"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('reports.mom.title') }}</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>{{ t('reports.mom.month') }}</th>
                <th>{{ t('reports.mom.orders') }}</th>
                <th>{{ t('reports.mom.revenue') }}</th>
                <th>{{ t('reports.mom.change') }}</th>
                <th>{{ t('reports.mom.growthRate') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(month, index) in monthlyData" :key="month.month">
                <td><strong>{{ formatMonth(month.month) }}</strong></td>
                <td>{{ month.order_count }}</td>
                <td>{{ formatCurrency(month.revenue) }}</td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getChangeValue(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getGrowthRate(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.avgMonthlyRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.totalOrders') }}</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('reports.stats.bestQuarter') }}</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch } from 'vue'
import CodyMascot from '../components/CodyMascot.vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency as formatCurrencyUtil, formatCurrencyWithDecimals } from '../utils/currency'

const MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
const MAX_BAR_HEIGHT = 200

export default {
  name: 'Reports',
  components: { CodyMascot },
  setup() {
    const { t, currentCurrency } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const quarterlyData = ref([])
    const monthlyData = ref([])

    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    // Guards against an older, slower response overwriting a newer one after rapid filter changes
    let requestId = 0

    const loadData = async () => {
      const currentRequest = ++requestId
      loading.value = true
      error.value = null
      try {
        const filters = getCurrentFilters()
        const [quarterly, monthly] = await Promise.all([
          api.getQuarterlyReports(filters),
          api.getMonthlyTrends(filters)
        ])
        if (currentRequest !== requestId) return
        quarterlyData.value = quarterly
        monthlyData.value = monthly
      } catch (err) {
        if (currentRequest !== requestId) return
        error.value = t('reports.loadFailed')
        console.error('Failed to load reports:', err)
      } finally {
        if (currentRequest === requestId) loading.value = false
      }
    }

    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadData()
    })

    onMounted(() => {
      loadData()
    })

    const isEmpty = computed(() => quarterlyData.value.length === 0 && monthlyData.value.length === 0)

    // Summary stats
    const totalRevenue = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + (Number(m.revenue) || 0), 0)
    )

    const avgMonthlyRevenue = computed(() =>
      monthlyData.value.length > 0 ? totalRevenue.value / monthlyData.value.length : 0
    )

    const totalOrders = computed(() =>
      monthlyData.value.reduce((sum, m) => sum + (Number(m.order_count) || 0), 0)
    )

    // '-' when there is no quarter with revenue, so the card never renders an empty or bogus value
    const bestQuarter = computed(() => {
      let best = null
      for (const q of quarterlyData.value) {
        if (q.total_revenue > 0 && (!best || q.total_revenue > best.total_revenue)) best = q
      }
      return best ? best.quarter : '-'
    })

    // Computed once per data change instead of once per bar
    const maxRevenue = computed(() =>
      monthlyData.value.reduce((max, m) => Math.max(max, Number(m.revenue) || 0), 0)
    )

    const getBarHeight = (revenue) => {
      if (maxRevenue.value <= 0) return 0
      return ((Number(revenue) || 0) / maxRevenue.value) * MAX_BAR_HEIGHT
    }

    const formatCurrency = (value) => formatCurrencyUtil(Number(value) || 0, currentCurrency.value)
    const formatCurrencyDecimals = (value) =>
      formatCurrencyWithDecimals(Number(value) || 0, currentCurrency.value, 2)

    // Accepts 'YYYY-MM'; falls back to '-' for anything else
    const formatMonth = (monthStr) => {
      if (typeof monthStr !== 'string') return '-'
      const match = /^(\d{4})-(\d{2})$/.exec(monthStr)
      if (!match) return '-'
      const monthIndex = parseInt(match[2], 10) - 1
      if (monthIndex < 0 || monthIndex > 11) return '-'
      return t('reports.monthFormat', {
        month: t(`months.${MONTH_KEYS[monthIndex]}`),
        year: match[1]
      })
    }

    const getFulfillmentClass = (rate) => {
      if (rate >= 90) return 'badge success'
      if (rate >= 75) return 'badge warning'
      return 'badge danger'
    }

    const getChangeValue = (current, previous) => {
      const change = current - previous
      if (change > 0) return '+' + formatCurrencyDecimals(change)
      if (change < 0) return '-' + formatCurrencyDecimals(Math.abs(change))
      return formatCurrencyDecimals(0)
    }

    const getChangeClass = (current, previous) => {
      const change = current - previous
      if (change > 0) return 'positive-change'
      if (change < 0) return 'negative-change'
      return ''
    }

    const getGrowthRate = (current, previous) => {
      if (!previous) return t('reports.mom.notAvailable')
      const rate = ((current - previous) / previous) * 100
      return (rate > 0 ? '+' : '') + rate.toFixed(1) + '%'
    }

    return {
      t,
      loading,
      error,
      quarterlyData,
      monthlyData,
      isEmpty,
      totalRevenue,
      avgMonthlyRevenue,
      totalOrders,
      bestQuarter,
      getBarHeight,
      formatCurrency,
      formatCurrencyDecimals,
      formatMonth,
      getFulfillmentClass,
      getChangeValue,
      getChangeClass,
      getGrowthRate
    }
  }
}
</script>

<style scoped>
/* .card, tables, .stat-card, .badge, .loading and .error come from App.vue; only
   Reports-specific pieces live here. */
.stats-grid {
  margin-top: var(--space-6);
}

.chart-container {
  padding: var(--space-8) var(--space-4);
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: var(--space-2);
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: var(--color-accent);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  transition: background-color var(--dur-base);
  cursor: pointer;
}

.bar:hover {
  background: var(--color-accent-hover);
}

.bar-label {
  font-size: var(--text-xs);
  color: var(--color-text-mid);
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: var(--space-6);
}

/* Accent marker so the summary cards keep the visual cue the old left border gave */
.stat-card {
  border-left: 4px solid var(--color-accent);
}

.positive-change {
  color: var(--color-success);
  font-weight: 600;
}

.negative-change {
  color: var(--color-danger);
  font-weight: 600;
}

.empty-state {
  text-align: center;
  color: var(--color-text-mid);
  padding: var(--space-12);
}

.empty-cody {
  margin: 0 auto var(--space-3);
}
</style>
