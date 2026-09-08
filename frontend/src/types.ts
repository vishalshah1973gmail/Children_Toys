export type UserRole = 'customer' | 'admin'

export interface User {
  id: number
  username: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface Category {
  id: number
  name: string
  slug: string
  description: string | null
  image_url: string | null
  product_count: number
}

export interface ProductImage {
  id: number
  url: string
  alt_text: string | null
  sort_order: number
  is_primary: boolean
}

export interface Product {
  id: number
  name: string
  slug: string
  description: string
  price_cents: number
  stock_quantity: number
  category_id: number
  category: { id: number; name: string; slug: string }
  min_age_months: number
  max_age_months: number
  brand: string
  safety_notes: string | null
  is_featured: boolean
  is_active: boolean
  images: ProductImage[]
  primary_image_url: string | null
  created_at: string
  updated_at: string
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface CartLine {
  id: number
  product_id: number
  name: string
  slug: string
  image_url: string | null
  unit_price_cents: number
  quantity: number
  line_total_cents: number
  stock_quantity: number
  in_stock: boolean
}

export interface Cart {
  items: CartLine[]
  subtotal_cents: number
  shipping_cents: number
  tax_cents: number
  total_cents: number
  item_count: number
  currency: string
}

export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled'

export interface OrderItem {
  id: number
  product_id: number
  product_name: string
  product_slug: string
  image_url: string | null
  unit_price_cents: number
  quantity: number
  line_total_cents: number
}

export interface Payment {
  id: number
  provider: string
  status: 'pending' | 'succeeded' | 'failed' | 'refunded'
  amount_cents: number
  currency: string
  stripe_payment_intent_id: string | null
  created_at: string
}

export interface Order {
  id: number
  order_number: string
  user_id: number | null
  status: OrderStatus
  subtotal_cents: number
  shipping_cents: number
  tax_cents: number
  total_cents: number
  currency: string
  contact_email: string
  shipping_name: string
  shipping_line1: string
  shipping_line2: string | null
  shipping_city: string
  shipping_state: string
  shipping_postal_code: string
  shipping_country: string
  billing_name: string | null
  billing_line1: string | null
  billing_line2: string | null
  billing_city: string | null
  billing_state: string | null
  billing_postal_code: string | null
  billing_country: string | null
  placed_at: string | null
  paid_at: string | null
  shipped_at: string | null
  delivered_at: string | null
  created_at: string
  items: OrderItem[]
  payments: Payment[]
}

export interface ShippingAddressInput {
  full_name: string
  line1: string
  line2?: string | null
  city: string
  state: string
  postal_code: string
  country: string
}

export interface CheckoutSession {
  order_number: string
  checkout_url: string
  session_id: string | null
  dev_mode: boolean
}

export interface AdminStats {
  products: number
  active_products: number
  low_stock: number
  categories: number
  customers: number
  orders: number
  pending_orders: number
  revenue_cents: number
}

export interface ApiError {
  code: string
  message: string
  field: string | null
}

export interface CatalogQuery {
  q?: string
  category?: string
  min_price_cents?: number
  max_price_cents?: number
  age_months?: number
  brand?: string
  in_stock?: boolean
  sort?: 'newest' | 'price_asc' | 'price_desc' | 'name_asc' | 'name_desc'
  page?: number
  page_size?: number
}

export type CardBrand = 'visa' | 'mastercard' | 'discover' | 'amex'

export interface GuestAddressInput {
  name: string
  line1: string
  line2?: string | null
  city: string
  state: string
  postal_code: string
  country: string
}

export interface CardDetailsInput {
  brand: CardBrand
  number: string
  name_on_card: string
  exp_month: number
  exp_year: number
  cvv: string
  postal_code: string
}

export interface GuestCheckoutRequestBody {
  contact_email: string
  billing_address: GuestAddressInput
  card: CardDetailsInput
  same_as_billing: boolean
  shipping_address?: GuestAddressInput | null
  items: { product_id: number; quantity: number }[]
}

export interface GuestCheckoutResponseBody {
  order: Order
  email_sent: boolean
}
