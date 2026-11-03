<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div
          ref="dialogRef"
          class="modal-container"
          role="dialog"
          aria-modal="true"
          aria-labelledby="po-modal-title"
          @click.stop
        >
          <div class="modal-header">
            <h3 id="po-modal-title" class="modal-title">
              {{ isView ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button
              ref="closeBtnRef"
              class="close-button"
              type="button"
              :aria-label="t('purchaseOrder.close')"
              @click="close"
            >
              <X :size="20" />
            </button>
          </div>

          <div class="modal-body">
            <!-- Backlog item summary (both modes) -->
            <div class="item-summary">
              <div class="summary-icon"><PackageSearch :size="24" /></div>
              <div class="summary-main">
                <div class="item-name">{{ translateProductName(backlogItem.item_name) }}</div>
                <div class="item-meta">
                  <span>{{ t('purchaseOrder.order') }}: <span class="mono">{{ backlogItem.order_id }}</span></span>
                  <span>{{ t('purchaseOrder.sku') }}: <span class="mono">{{ backlogItem.item_sku }}</span></span>
                </div>
              </div>
              <div class="summary-shortage">
                <div class="info-label">{{ t('purchaseOrder.shortage') }}</div>
                <div class="shortage-value">{{ t('purchaseOrder.units', { count: shortage }) }}</div>
              </div>
            </div>

            <!-- View mode -->
            <template v-if="isView">
              <div v-if="loading" class="state-message" role="status">{{ t('purchaseOrder.loading') }}</div>
              <div v-else-if="loadError" class="form-error" role="alert">
                <AlertCircle :size="16" />
                <span>{{ loadError }}</span>
              </div>
              <div v-else-if="po" class="info-grid">
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.poNumber') }}</div>
                  <div class="info-value mono">{{ po.id }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                  <div class="info-value">
                    <span class="status-badge" :class="statusClass(po.status)">{{ statusLabel(po.status) }}</span>
                  </div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                  <div class="info-value">{{ po.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                  <div class="info-value">{{ t('purchaseOrder.units', { count: po.quantity }) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                  <div class="info-value">{{ formatMoney(po.unit_cost, 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.total') }}</div>
                  <div class="info-value strong">{{ formatMoney(po.quantity * po.unit_cost, 2) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                  <div class="info-value">{{ formatDate(po.created_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                  <div class="info-value">{{ formatDate(po.expected_delivery_date) }}</div>
                </div>
                <div class="info-item full">
                  <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                  <div class="info-value notes">{{ po.notes || '-' }}</div>
                </div>
              </div>
            </template>

            <!-- Create mode -->
            <form v-else id="po-form" class="po-form" novalidate @submit.prevent="submit">
              <div class="form-group full">
                <label for="po-supplier">{{ t('purchaseOrder.supplier') }} *</label>
                <input
                  id="po-supplier"
                  ref="firstFieldRef"
                  v-model="form.supplier_name"
                  type="text"
                  class="form-input"
                  maxlength="120"
                  :disabled="submitting"
                  :aria-invalid="touched.supplier_name && !!errors.supplier_name"
                  @blur="touched.supplier_name = true"
                />
                <span v-if="touched.supplier_name && errors.supplier_name" class="field-error">{{ errors.supplier_name }}</span>
              </div>

              <div class="form-group">
                <label for="po-quantity">{{ t('purchaseOrder.quantity') }} *</label>
                <input
                  id="po-quantity"
                  v-model="form.quantity"
                  type="number"
                  min="1"
                  step="1"
                  class="form-input"
                  :disabled="submitting"
                  :aria-invalid="touched.quantity && !!errors.quantity"
                  @blur="touched.quantity = true"
                />
                <span v-if="touched.quantity && errors.quantity" class="field-error">{{ errors.quantity }}</span>
              </div>

              <div class="form-group">
                <label for="po-unit-cost">{{ t('purchaseOrder.unitCostUsd') }} *</label>
                <input
                  id="po-unit-cost"
                  v-model="form.unit_cost"
                  type="number"
                  min="0"
                  step="0.01"
                  class="form-input"
                  :disabled="submitting"
                  :aria-invalid="touched.unit_cost && !!errors.unit_cost"
                  @blur="touched.unit_cost = true"
                />
                <span v-if="touched.unit_cost && errors.unit_cost" class="field-error">{{ errors.unit_cost }}</span>
              </div>

              <div class="form-group full">
                <label for="po-delivery">{{ t('purchaseOrder.expectedDelivery') }} *</label>
                <input
                  id="po-delivery"
                  v-model="form.expected_delivery_date"
                  type="date"
                  class="form-input"
                  :disabled="submitting"
                  :aria-invalid="touched.expected_delivery_date && !!errors.expected_delivery_date"
                  @blur="touched.expected_delivery_date = true"
                />
                <span v-if="touched.expected_delivery_date && errors.expected_delivery_date" class="field-error">{{ errors.expected_delivery_date }}</span>
              </div>

              <div class="form-group full">
                <label for="po-notes">{{ t('purchaseOrder.notes') }} ({{ t('purchaseOrder.optional') }})</label>
                <textarea
                  id="po-notes"
                  v-model="form.notes"
                  rows="3"
                  maxlength="500"
                  class="form-input"
                  :disabled="submitting"
                ></textarea>
              </div>

              <div class="total-row full">
                <span class="info-label">{{ t('purchaseOrder.total') }}</span>
                <span class="total-value">{{ totalDisplay }}</span>
              </div>

              <div v-if="submitError" class="form-error full" role="alert">
                <AlertCircle :size="16" />
                <span>{{ submitError }}</span>
              </div>
            </form>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" type="button" @click="close">{{ t('purchaseOrder.close') }}</button>
            <button
              v-if="!isView"
              class="btn-primary"
              type="submit"
              form="po-form"
              :disabled="!isValid || submitting"
            >
              {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { X, PackageSearch, AlertCircle } from 'lucide-vue-next'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  backlogItem: { type: Object, default: null },
  mode: { type: String, default: 'create', validator: (v) => ['create', 'view'].includes(v) }
})

const emit = defineEmits(['close', 'po-created'])

const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

const dialogRef = ref(null)
const closeBtnRef = ref(null)
const firstFieldRef = ref(null)
let previouslyFocused = null

const isView = computed(() => props.mode === 'view')

const shortage = computed(() => {
  if (!props.backlogItem) return 0
  return Math.max(0, props.backlogItem.quantity_needed - props.backlogItem.quantity_available)
})

// ---- Create mode ----------------------------------------------------------
const emptyForm = () => ({
  supplier_name: '',
  quantity: shortage.value || '',
  unit_cost: '',
  expected_delivery_date: '',
  notes: ''
})
const form = reactive(emptyForm())
const touched = reactive({ supplier_name: false, quantity: false, unit_cost: false, expected_delivery_date: false })
const submitting = ref(false)
const submitError = ref(null)

const quantityNum = computed(() => Number(form.quantity))
const unitCostNum = computed(() => Number(form.unit_cost))

const errors = computed(() => {
  const e = {}
  if (!form.supplier_name.trim()) e.supplier_name = t('purchaseOrder.errors.supplierRequired')
  // v-model on type=number yields '' when empty, a number otherwise
  if (form.quantity === '' || !Number.isInteger(quantityNum.value) || quantityNum.value <= 0) {
    e.quantity = t('purchaseOrder.errors.quantityPositive')
  }
  if (form.unit_cost === '' || !Number.isFinite(unitCostNum.value) || unitCostNum.value <= 0) {
    e.unit_cost = t('purchaseOrder.errors.unitCostPositive')
  }
  if (!form.expected_delivery_date || isNaN(new Date(form.expected_delivery_date).getTime())) {
    e.expected_delivery_date = t('purchaseOrder.errors.dateRequired')
  }
  return e
})

const isValid = computed(() => Object.keys(errors.value).length === 0)

const total = computed(() => {
  const q = quantityNum.value
  const c = unitCostNum.value
  return Number.isFinite(q) && Number.isFinite(c) && q > 0 && c > 0 ? q * c : 0
})
const totalDisplay = computed(() => formatMoney(total.value, 2))

const resetForm = () => {
  Object.assign(form, emptyForm())
  Object.keys(touched).forEach((k) => { touched[k] = false })
  submitError.value = null
  submitting.value = false
}

const submit = async () => {
  if (!isValid.value || submitting.value || !props.backlogItem) return
  submitting.value = true
  submitError.value = null
  try {
    const po = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.supplier_name.trim(),
      quantity: quantityNum.value,
      unit_cost: unitCostNum.value,
      expected_delivery_date: form.expected_delivery_date,
      notes: form.notes.trim() || null
    })
    emit('po-created', po)
  } catch (err) {
    // Backend sends a human-readable `detail` for 400/404/409. FastAPI's own
    // 422 validation errors send an array instead, so only trust strings.
    const detail = err?.response?.data?.detail
    submitError.value = typeof detail === 'string' ? detail : t('purchaseOrder.errors.generic')
    console.error('Failed to create purchase order:', err)
  } finally {
    submitting.value = false
  }
}

// ---- View mode ------------------------------------------------------------
const po = ref(null)
const loading = ref(false)
const loadError = ref(null)
let loadToken = 0

const loadPO = async () => {
  if (!props.backlogItem) return
  const token = ++loadToken
  loading.value = true
  loadError.value = null
  po.value = null
  try {
    const result = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
    if (token === loadToken) po.value = result
  } catch (err) {
    if (token !== loadToken) return
    const detail = err?.response?.data?.detail
    loadError.value = typeof detail === 'string' ? detail : t('purchaseOrder.errors.loadFailed')
    console.error('Failed to load purchase order:', err)
  } finally {
    if (token === loadToken) loading.value = false
  }
}

// ---- Formatting -----------------------------------------------------------
const formatMoney = (amount, decimals = 0) => {
  const n = Number(amount)
  if (!Number.isFinite(n)) return '-'
  return formatCurrencyWithDecimals(n, currentCurrency.value, decimals)
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const d = new Date(dateString)
  if (isNaN(d.getTime())) return '-'
  // Same output format as Orders.vue; UTC because the backend sends date-only
  // strings, which parse as UTC and would shift a day in western timezones.
  return d.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC'
  })
}

const statusClass = (status) => {
  const s = String(status || '').toLowerCase()
  if (s === 'delivered' || s === 'received') return 'success'
  if (s === 'cancelled') return 'danger'
  if (s === 'ordered' || s === 'shipped') return 'info'
  return 'warning'
}

const statusLabel = (status) => {
  const key = `purchaseOrder.statuses.${String(status || '').toLowerCase()}`
  const label = t(key)
  return label === key ? status : label
}

// ---- Dialog behavior ------------------------------------------------------
const close = () => emit('close')

const FOCUSABLE = 'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])'

// Listens on document, not the dialog: when the submit button is disabled
// mid-request, focus drops to <body> and a dialog-level handler would miss Esc.
const onKeydown = (e) => {
  if (e.key === 'Escape') {
    e.stopPropagation()
    close()
    return
  }
  if (e.key !== 'Tab' || !dialogRef.value) return
  const els = [...dialogRef.value.querySelectorAll(FOCUSABLE)]
  if (!els.length) return
  const first = els[0]
  const last = els[els.length - 1]
  // Focus falls back to <body> when the focused submit button gets disabled
  if (!dialogRef.value.contains(document.activeElement)) { e.preventDefault(); first.focus() }
  else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

watch(
  () => [props.isOpen, props.backlogItem?.id, props.mode],
  async ([open]) => {
    document.removeEventListener('keydown', onKeydown)
    if (open && props.backlogItem) document.addEventListener('keydown', onKeydown)
    if (!open || !props.backlogItem) {
      loadToken++ // drop any in-flight view request
      if (previouslyFocused && !open) {
        previouslyFocused.focus?.()
        previouslyFocused = null
      }
      return
    }
    if (!previouslyFocused) previouslyFocused = document.activeElement
    if (isView.value) loadPO()
    else resetForm()
    await nextTick()
    ;(isView.value ? closeBtnRef.value : firstFieldRef.value)?.focus()
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  loadToken++
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: var(--space-4);
}

.modal-container {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-6);
  border-bottom: 1px solid var(--color-border-2);
}

.modal-title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: var(--color-text-dim);
  cursor: pointer;
  padding: var(--space-2);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--dur-fast) var(--ease-out);
}

.close-button:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.item-summary {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-surface-3);
  border: 1px solid var(--color-border-2);
  border-radius: var(--radius-md);
}

.summary-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-danger-bg);
  color: var(--color-danger);
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.summary-main {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text);
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-dim);
  margin-top: var(--space-1);
}

.mono {
  font-family: var(--font-mono);
}

.summary-shortage {
  text-align: right;
  flex-shrink: 0;
}

.shortage-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-danger);
}

.info-label {
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-dim);
}

/* Form */
.po-form,
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4) var(--space-6);
}

.full {
  grid-column: 1 / -1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-group label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-mid);
}

.form-input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-input-bg);
  color: var(--color-text);
  font-size: var(--text-base);
  font-family: inherit;
  transition: border-color var(--dur-fast) var(--ease-out);
}

.form-input:hover:not(:disabled) {
  border-color: var(--color-border-3);
}

.form-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.form-input[aria-invalid="true"] {
  border-color: var(--color-danger);
}

.form-input:disabled {
  background: var(--color-surface-2);
  color: var(--color-text-dim);
  cursor: not-allowed;
}

textarea.form-input {
  resize: vertical;
}

.field-error {
  font-size: var(--text-xs);
  color: var(--color-danger);
}

.total-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-2);
}

.total-value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text);
}

.form-error {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-sm);
  color: var(--color-danger);
  font-size: var(--text-sm);
}

.form-error svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.state-message {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-dim);
}

/* View */
.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.info-value {
  font-size: var(--text-base);
  color: var(--color-text);
  font-weight: 500;
}

.info-value.strong {
  font-weight: 700;
}

.info-value.notes {
  white-space: pre-wrap;
  font-weight: 400;
}

.status-badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
}

.status-badge.success { background: var(--color-success-bg); color: var(--color-success); }
.status-badge.info { background: var(--color-info-bg); color: var(--color-info); }
.status-badge.warning { background: var(--color-warning-bg); color: var(--color-warning); }
.status-badge.danger { background: var(--color-danger-bg); color: var(--color-danger); }

.modal-footer {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border-2);
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn-secondary,
.btn-primary {
  padding: var(--space-2) var(--space-5);
  border-radius: var(--radius-md);
  font-weight: 500;
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-out);
  font-family: inherit;
}

.btn-secondary {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border-2);
  color: var(--color-text-mid);
}

.btn-secondary:hover {
  background: var(--color-border);
}

.btn-primary {
  background: var(--color-accent);
  border: 1px solid var(--color-accent);
  color: var(--color-on-accent);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 560px) {
  .po-form,
  .info-grid {
    grid-template-columns: 1fr;
  }
  .item-summary {
    flex-wrap: wrap;
  }
  .summary-shortage {
    text-align: left;
  }
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--dur-base) ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform var(--dur-base) ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
