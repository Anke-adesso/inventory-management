import { markRaw } from 'vue'
import {
  LayoutDashboard,
  Package,
  ShoppingCart,
  Wallet,
  TrendingUp,
  PackagePlus,
  FileChartColumn
} from 'lucide-vue-next'

// Icons are markRaw so Vue never makes the components reactive.
const item = (key, to, icon) => ({ key, to, labelKey: `nav.${key}`, icon: markRaw(icon) })

export const navigationGroups = [
  {
    key: 'operations',
    labelKey: 'nav.groupOperations',
    items: [
      item('overview', '/', LayoutDashboard),
      item('inventory', '/inventory', Package),
      item('orders', '/orders', ShoppingCart),
      item('restocking', '/restocking', PackagePlus),
      item('demandForecast', '/demand', TrendingUp)
    ]
  },
  {
    key: 'finance',
    labelKey: 'nav.groupFinance',
    items: [
      item('finance', '/spending', Wallet),
      item('reports', '/reports', FileChartColumn)
    ]
  }
]

export const navigationItems = navigationGroups.flatMap(g => g.items)
