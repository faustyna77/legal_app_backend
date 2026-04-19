import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ROUTES } from './config'
import { SearchPage } from './pages/search/SearchPage'
import { JudgmentsPage } from './pages/judgments/JudgmentsPage'
import { JudgmentDetailPage } from './pages/judgments/DetailPage'
import { LoginPage } from './pages/auth/LoginPage'
import { RegisterPage } from './pages/auth/RegisterPage'
import { AdminPage } from './pages/admin/AdminPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path={ROUTES.HOME} element={<Navigate to={ROUTES.SEARCH} replace />} />
        <Route path={ROUTES.SEARCH} element={<SearchPage />} />
        <Route path={ROUTES.JUDGMENTS} element={<JudgmentsPage />} />
        <Route path={ROUTES.JUDGMENT_DETAIL} element={<JudgmentDetailPage />} />
        <Route path={ROUTES.LOGIN} element={<LoginPage />} />
        <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
        <Route path={ROUTES.ADMIN} element={<AdminPage />} />
      </Routes>
    </BrowserRouter>
  )
}
