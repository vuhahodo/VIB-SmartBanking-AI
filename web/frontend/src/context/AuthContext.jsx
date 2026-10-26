import { createContext, useContext, useState } from 'react'
import { api } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [customerId, setCustomerId] = useState(() => localStorage.getItem('vib_customer'))

  async function login(id, password) {
    const { access_token, customer_number } = await api.login(id, password)
    localStorage.setItem('vib_token', access_token)
    localStorage.setItem('vib_customer', customer_number)
    setCustomerId(customer_number)
  }

  function logout() {
    localStorage.removeItem('vib_token')
    localStorage.removeItem('vib_customer')
    setCustomerId(null)
  }

  return <AuthContext.Provider value={{ customerId, login, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
