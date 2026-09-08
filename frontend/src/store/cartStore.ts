import { create } from 'zustand'

import { cartApi } from '../api/cart'
import { toApiError } from '../api/client'
import type { Cart, CartLine, Product } from '../types'

/**
 * Signed-in shoppers get the real server cart, which is the only cart the
 * checkout ever prices. Guests get a local cart in localStorage purely so the
 * basket survives a page reload; its totals are a preview and are recomputed
 * server-side the moment the guest signs in and the carts merge.
 */
const GUEST_KEY = 'toybox.guest_cart'
const SHIPPING_FLAT_CENTS = 599
const FREE_SHIPPING_THRESHOLD_CENTS = 5000
const TAX_RATE_BPS = 663

const EMPTY_CART: Cart = {
  items: [],
  subtotal_cents: 0,
  shipping_cents: 0,
  tax_cents: 0,
  total_cents: 0,
  item_count: 0,
  currency: 'usd',
}

function readGuestLines(): CartLine[] {
  try {
    const raw = localStorage.getItem(GUEST_KEY)
    return raw ? (JSON.parse(raw) as CartLine[]) : []
  } catch {
    return []
  }
}

function writeGuestLines(lines: CartLine[]): void {
  try {
    localStorage.setItem(GUEST_KEY, JSON.stringify(lines))
  } catch {
    // Private browsing can refuse writes; the in-memory cart still works.
  }
}

function priceGuestCart(lines: CartLine[]): Cart {
  const priced = lines.map((line) => ({
    ...line,
    line_total_cents: line.unit_price_cents * line.quantity,
  }))
  const subtotal = priced.reduce((sum, line) => sum + line.line_total_cents, 0)
  const shipping =
    subtotal === 0 || subtotal >= FREE_SHIPPING_THRESHOLD_CENTS ? 0 : SHIPPING_FLAT_CENTS
  const tax = subtotal === 0 ? 0 : Math.floor((subtotal * TAX_RATE_BPS + 5000) / 10000)
  return {
    items: priced,
    subtotal_cents: subtotal,
    shipping_cents: shipping,
    tax_cents: tax,
    total_cents: subtotal + shipping + tax,
    item_count: priced.reduce((sum, line) => sum + line.quantity, 0),
    currency: 'usd',
  }
}

interface CartState {
  cart: Cart
  authenticated: boolean
  loading: boolean
  error: string | null
  setAuthenticated: (value: boolean) => void
  refresh: () => Promise<void>
  add: (product: Product, quantity?: number) => Promise<void>
  setQuantity: (line: CartLine, quantity: number) => Promise<void>
  remove: (line: CartLine) => Promise<void>
  clear: () => Promise<void>
  mergeGuestCart: () => Promise<void>
  loadGuestCart: () => void
}

export const useCartStore = create<CartState>((set, get) => ({
  cart: EMPTY_CART,
  authenticated: false,
  loading: false,
  error: null,

  setAuthenticated(value) {
    set({ authenticated: value })
  },

  loadGuestCart() {
    set({ cart: priceGuestCart(readGuestLines()) })
  },

  async refresh() {
    if (!get().authenticated) {
      get().loadGuestCart()
      return
    }
    set({ loading: true, error: null })
    try {
      set({ cart: await cartApi.get() })
    } catch (error) {
      set({ error: toApiError(error).message })
    } finally {
      set({ loading: false })
    }
  },

  async add(product, quantity = 1) {
    set({ error: null })
    if (!get().authenticated) {
      const lines = readGuestLines()
      const existing = lines.find((line) => line.product_id === product.id)
      const desired = (existing?.quantity ?? 0) + quantity
      if (desired > product.stock_quantity) {
        set({ error: `Only ${product.stock_quantity} left in stock.` })
        return
      }
      if (existing) {
        existing.quantity = desired
      } else {
        lines.push({
          id: product.id,
          product_id: product.id,
          name: product.name,
          slug: product.slug,
          image_url: product.primary_image_url,
          unit_price_cents: product.price_cents,
          quantity,
          line_total_cents: product.price_cents * quantity,
          stock_quantity: product.stock_quantity,
          in_stock: true,
        })
      }
      writeGuestLines(lines)
      set({ cart: priceGuestCart(lines) })
      return
    }

    set({ loading: true })
    try {
      set({ cart: await cartApi.add(product.id, quantity) })
    } catch (error) {
      set({ error: toApiError(error).message })
    } finally {
      set({ loading: false })
    }
  },

  async setQuantity(line, quantity) {
    set({ error: null })
    if (quantity < 1) {
      await get().remove(line)
      return
    }
    if (!get().authenticated) {
      const lines = readGuestLines().map((item) =>
        item.product_id === line.product_id
          ? { ...item, quantity: Math.min(quantity, item.stock_quantity) }
          : item,
      )
      writeGuestLines(lines)
      set({ cart: priceGuestCart(lines) })
      return
    }
    set({ loading: true })
    try {
      set({ cart: await cartApi.update(line.id, quantity) })
    } catch (error) {
      set({ error: toApiError(error).message })
    } finally {
      set({ loading: false })
    }
  },

  async remove(line) {
    set({ error: null })
    if (!get().authenticated) {
      const lines = readGuestLines().filter((item) => item.product_id !== line.product_id)
      writeGuestLines(lines)
      set({ cart: priceGuestCart(lines) })
      return
    }
    set({ loading: true })
    try {
      set({ cart: await cartApi.remove(line.id) })
    } catch (error) {
      set({ error: toApiError(error).message })
    } finally {
      set({ loading: false })
    }
  },

  async clear() {
    if (!get().authenticated) {
      writeGuestLines([])
      set({ cart: EMPTY_CART })
      return
    }
    set({ loading: true })
    try {
      set({ cart: await cartApi.clear() })
    } catch (error) {
      set({ error: toApiError(error).message })
    } finally {
      set({ loading: false })
    }
  },

  async mergeGuestCart() {
    const lines = readGuestLines()
    set({ authenticated: true })
    if (lines.length === 0) {
      await get().refresh()
      return
    }
    set({ loading: true })
    try {
      const merged = await cartApi.merge(
        lines.map((line) => ({ product_id: line.product_id, quantity: line.quantity })),
      )
      writeGuestLines([])
      set({ cart: merged })
    } catch (error) {
      set({ error: toApiError(error).message })
    } finally {
      set({ loading: false })
    }
  },
}))
