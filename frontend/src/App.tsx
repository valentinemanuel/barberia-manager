import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Login from './pages/Login'
import DashboardAdmin from './pages/DashboardAdmin'
import DashboardBarbero from './pages/DashboardBarbero'
import RegistroCortes from './pages/RegistroCortes'
import GestionUsuarios from './pages/GestionUsuarios'
import GestionServicios from './pages/GestionServicios'
import GestionProductos from './pages/GestionProductos'
import Reportes from './pages/Reportes'
import CierreCaja from './pages/CierreCaja'
import Layout from './components/Layout'

function App() {
  const { usuario, token } = useAuthStore()

  if (!token || !usuario) {
    return <Login />
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={
          usuario.rol === 'admin' ? <DashboardAdmin /> : <DashboardBarbero />
        } />
        <Route path="/cortes" element={<RegistroCortes />} />
        <Route path="/usuarios" element={
          usuario.rol === 'admin' ? <GestionUsuarios /> : <Navigate to="/" />
        } />
        <Route path="/servicios" element={
          usuario.rol === 'admin' ? <GestionServicios /> : <Navigate to="/" />
        } />
        <Route path="/productos" element={
          usuario.rol === 'admin' ? <GestionProductos /> : <Navigate to="/" />
        } />
        <Route path="/reportes" element={
          usuario.rol === 'admin' ? <Reportes /> : <Navigate to="/" />
        } />
        <Route path="/cierre-caja" element={
          usuario.rol === 'admin' ? <CierreCaja /> : <Navigate to="/" />
        } />
      </Routes>
    </Layout>
  )
}

export default App
