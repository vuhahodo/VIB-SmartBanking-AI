import { CreditCard, HandCoins, PiggyBank } from 'lucide-react'

const ICONS = { Cards: CreditCard, Savings: PiggyBank, Lending: HandCoins }

export default function ProductIcon({ category, size = 22 }) {
  const Icon = ICONS[category] ?? CreditCard
  return (
    <div className={`product-icon cat-${category}`}>
      <Icon size={size} />
    </div>
  )
}
