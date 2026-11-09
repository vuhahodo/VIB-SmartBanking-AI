import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import ProductDetail from './pages/ProductDetail'
import Transactions from './pages/Transactions'
import AIInsights from './pages/AIInsights'
import Infrastructure from './pages/Infrastructure'

function RequireAuth({ children }) {
  const { customerId } = useAuth()
  return customerId ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="products/:code" element={<ProductDetail />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="ai-insights" element={<AIInsights />} />
        <Route path="infrastructure" element={<Infrastructure />} />
        <Route path="admin/infrastructure" element={<Infrastructure />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
