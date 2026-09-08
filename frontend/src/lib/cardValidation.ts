import type { CardBrand } from '../types'

const BRAND_RULES: { brand: CardBrand; prefixes: string[]; lengths: number[] }[] = [
  { brand: 'visa', prefixes: ['4'], lengths: [13, 16, 19] },
  {
    brand: 'mastercard',
    prefixes: [
      ...Array.from({ length: 5 }, (_, i) => String(51 + i)),
      ...Array.from({ length: 500 }, (_, i) => String(2221 + i)),
    ],
    lengths: [16],
  },
  {
    brand: 'discover',
    prefixes: ['6011', '65', ...Array.from({ length: 6 }, (_, i) => String(644 + i))],
    lengths: [16],
  },
  { brand: 'amex', prefixes: ['34', '37'], lengths: [15] },
]

function digitsOnly(value: string): string {
  return value.replace(/[^0-9]/g, '')
}

export function detectBrand(number: string): CardBrand | null {
  const digits = digitsOnly(number)
  for (const rule of BRAND_RULES) {
    if (!rule.lengths.includes(digits.length)) continue
    if (rule.prefixes.some((prefix) => digits.startsWith(prefix))) return rule.brand
  }
  return null
}

export function luhnIsValid(number: string): boolean {
  const digits = digitsOnly(number).split('').map(Number)
  if (digits.length === 0) return false
  let checksum = 0
  digits.reverse().forEach((digit, index) => {
    let value = digit
    if (index % 2 === 1) {
      value *= 2
      if (value > 9) value -= 9
    }
    checksum += value
  })
  return checksum % 10 === 0
}

export function cvvLengthFor(brand: CardBrand): number {
  return brand === 'amex' ? 4 : 3
}

interface CardInput {
  brand: CardBrand
  number: string
  expMonth: number
  expYear: number
  cvv: string
  postalCode: string
}

/** Field name -> error message. Empty object means the card looks valid. */
export function validateCard(input: CardInput): Record<string, string> {
  const errors: Record<string, string> = {}
  const digits = digitsOnly(input.number)

  if (digits.length < 12 || digits.length > 19) {
    errors.number = 'Card number length looks wrong.'
  } else if (!luhnIsValid(digits)) {
    errors.number = 'Card number failed the checksum check.'
  } else if (detectBrand(digits) !== input.brand) {
    errors.number = `That number doesn't look like a ${input.brand} card.`
  }

  if (input.expMonth < 1 || input.expMonth > 12) {
    errors.exp_month = 'Expiry month must be between 1 and 12.'
  } else {
    const now = new Date()
    const lastDayOfExpiryMonth = new Date(input.expYear, input.expMonth, 0)
    if (lastDayOfExpiryMonth < new Date(now.getFullYear(), now.getMonth(), now.getDate())) {
      errors.exp_year = 'This card has already expired.'
    }
  }

  const cvvDigits = digitsOnly(input.cvv)
  if (cvvDigits.length !== cvvLengthFor(input.brand)) {
    errors.cvv = `${input.brand} security codes are ${cvvLengthFor(input.brand)} digits.`
  }

  if (!/^\d{5}(-\d{4})?$/.test(input.postalCode)) {
    errors.postal_code = 'Zip code must be 5 digits (optionally +4).'
  }

  return errors
}
