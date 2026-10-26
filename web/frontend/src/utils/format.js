const vnd = new Intl.NumberFormat('vi-VN')

export const formatVND = (n) => `${vnd.format(Math.round(n))} ₫`

export const formatSignedVND = (n) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${vnd.format(Math.abs(Math.round(n)))} ₫`

export const formatDate = (iso) =>
  new Date(iso).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })

export const formatDateTime = (iso) =>
  new Date(iso).toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

export const CATEGORY_LABEL = {
  Cards: 'Thẻ',
  Savings: 'Tiết kiệm',
  Lending: 'Vay',
}
