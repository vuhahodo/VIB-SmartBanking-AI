import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { BrainCircuit, CreditCard, LayoutDashboard, LogOut, Menu, ReceiptText, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { api, isMock } from '../api/client'
import { useAsync } from '../utils/useAsync'
import Logo from './Logo'

const NAV = [
  { to: '/', label: 'Tổng quan', icon: LayoutDashboard, end: true },
  { to: '/products', label: 'Sản phẩm', icon: CreditCard },
  { to: '/transactions', label: 'Giao dịch', icon: ReceiptText },
  { to: '/ai-insights', label: 'AI Insights', icon: BrainCircuit },
]

export default function Layout() {
  const { customerId, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const { data } = useAsync(() => api.getCustomer(customerId), [customerId])
  const name = data?.profile.full_name ?? '...'
  const initials = name
    .split(' ')
    .slice(-2)
    .map((w) => w[0])
    .join('')

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-head">
          <Logo />
          <button className="icon-btn only-mobile" onClick={() => setOpen(false)} aria-label="Đóng menu">
            <X size={20} />
          </button>
        </div>
        <nav>
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="nav-link" onClick={() => setOpen(false)}>
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <button className="nav-link logout" onClick={logout}>
          <LogOut size={18} />
          Đăng xuất
        </button>
      </aside>
      {open && <div className="backdrop" onClick={() => setOpen(false)} />}

      <div className="main">
        <header className="topbar">
          <button className="icon-btn only-mobile" onClick={() => setOpen(true)} aria-label="Mở menu">
            <Menu size={20} />
          </button>
          {isMock && <span className="mock-pill">Dữ liệu demo</span>}
          <div className="user">
            <div className="user-text">
              <strong>{name}</strong>
              <span>Mã KH: {customerId}</span>
            </div>
            <div className="avatar">{initials}</div>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
