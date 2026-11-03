<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="loadError" class="error">{{ loadError }}</div>
    <div v-else>
      <div class="card budget-card">
        <label class="budget-label" for="budget-slider">
          {{ t('restocking.budget') }}: <strong>{{ formatCurrency(budget) }}</strong>
        </label>
        <input
          id="budget-slider"
          class="budget-slider"
          type="range"
          min="0"
          :max="maxCost"
          :step="STEP"
          v-model.number="budget"
          @input="onBudgetInput"
        />
        <div class="budget-range">
          <span>{{ formatCurrency(0) }}</span>
          <span>{{ formatCurrency(maxCost) }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ formatCurrency(budget) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.allocated') }}</div>
          <div class="stat-value">{{ formatCurrency(result.total_cost) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ formatCurrency(result.remaining_budget) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.items') }}</div>
          <div class="stat-value">{{ result.items.length }}</div>
        </div>
      </div>

      <div v-if="orderSuccess" class="success-banner">
        <span>{{ t('restocking.success', { orderNumber: orderSuccess.order_number }) }}</span>
        <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
      </div>
      <div v-if="submitError" class="error">{{ submitError }}</div>
      <div v-if="fetchError" class="error">{{ fetchError }}</div>

      <div class="card">
        <div class="card-header restock-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ result.items.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="result.items.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>
        <div v-if="result.items.length === 0" class="empty-state">{{ t('restocking.empty') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.recommendedQty') }}</th>
                <th>{{ t('restocking.table.lineCost') }}</th>
                <th>{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in result.items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>
                  <span :class="['badge', item.trend]">
                    {{ t(`trends.${item.trend}`) }}
                  </span>
                </td>
                <td>{{ item.forecasted_demand.toLocaleString() }}</td>
                <td>{{ formatUnitCost(item.unit_cost) }}</td>
                <td>
                  {{ item.recommended_qty.toLocaleString() }}
                  <span v-if="item.partial" class="badge warning partial-badge">{{ t('restocking.partial') }}</span>
                </td>
                <td><strong>{{ formatCurrency(item.line_cost) }}</strong></td>
                <td>{{ t('restocking.days', { count: item.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency as formatCurrencyUtil, formatCurrencyWithDecimals } from '../utils/currency'

const STEP = 500
const DEBOUNCE_MS = 250

export default {
  name: 'Restocking',
  setup() {
    // Global filters intentionally ignored: forecast SKUs mostly don't exist in inventory, so warehouse/category can't be mapped.
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const loadError = ref(null)
    const fetchError = ref(null)
    const submitError = ref(null)
    const submitting = ref(false)
    const orderSuccess = ref(null)
    const budget = ref(0)
    const maxCost = ref(0)
    const result = ref({ budget: 0, total_cost: 0, remaining_budget: 0, max_cost: 0, items: [] })

    let timer = null
    let requestSeq = 0

    const formatCurrency = (value) => formatCurrencyUtil(value, currentCurrency.value)

    const formatUnitCost = (value) => formatCurrencyWithDecimals(value, currentCurrency.value, 2)

    const fetchRecommendations = async () => {
      const seq = ++requestSeq
      try {
        const data = await api.getRestockRecommendations(budget.value)
        if (seq !== requestSeq) return // stale response
        result.value = data
        fetchError.value = null
      } catch (err) {
        if (seq !== requestSeq) return
        fetchError.value = t('restocking.loadFailed') + ': ' + (err.response?.data?.detail || err.message)
      }
    }

    const onBudgetInput = () => {
      orderSuccess.value = null
      submitError.value = null
      clearTimeout(timer)
      timer = setTimeout(fetchRecommendations, DEBOUNCE_MS)
    }

    const init = async () => {
      try {
        const initial = await api.getRestockRecommendations(0)
        maxCost.value = Math.ceil(initial.max_cost / STEP) * STEP
        budget.value = Math.round(maxCost.value / 2 / STEP) * STEP
        await fetchRecommendations()
      } catch (err) {
        loadError.value = t('restocking.loadFailed') + ': ' + (err.response?.data?.detail || err.message)
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (submitting.value || result.value.items.length === 0) return
      clearTimeout(timer)
      submitting.value = true
      submitError.value = null
      orderSuccess.value = null
      try {
        // Make sure the order matches what the user sees at this budget
        await fetchRecommendations()
        const items = result.value.items
        orderSuccess.value = await api.createRestockOrder({
          items: items.map(i => ({ sku: i.sku, quantity: i.recommended_qty })),
          budget: budget.value
        })
      } catch (err) {
        submitError.value = err.response?.data?.detail || err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(init)
    onBeforeUnmount(() => clearTimeout(timer))

    return {
      t,
      STEP,
      loading,
      loadError,
      fetchError,
      submitError,
      submitting,
      orderSuccess,
      budget,
      maxCost,
      result,
      formatCurrency,
      formatUnitCost,
      translateProductName,
      onBudgetInput,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-label {
  display: block;
  margin-bottom: 0.75rem;
  color: var(--color-text);
  font-size: 0.938rem;
}

.budget-slider {
  width: 100%;
}

.budget-range {
  display: flex;
  justify-content: space-between;
  margin-top: 0.25rem;
  color: var(--color-text-dim);
  font-size: 0.813rem;
}

.restock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.place-order-btn {
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.place-order-btn:disabled {
  background: var(--color-border);
  cursor: not-allowed;
}

.partial-badge {
  margin-left: 0.5rem;
  font-size: 0.688rem;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-dim);
}

.success-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}

.success-banner a {
  color: #166534;
  font-weight: 600;
  text-decoration: underline;
}
</style>
