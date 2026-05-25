import React, { createContext, useEffect, useState } from 'react'
import { Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { api } from './api'

import Rubrics from './pages/Rubrics.jsx'
import Grading from './pages/Grading.jsx'
import Review from './pages/Review.jsx'
import Audit from './pages/Audit.jsx'

export const RoleContext = createContext({ role: 'instructor', user: null, users: [] })

const NAV = [
  { to: '/rubrics', label: 'Rubrics' },
  { to: '/grading', label: 'Grading' },
  { to: '/review',  label: 'Review'  },
  { to: '/audit',   label: 'Audit'   },
]

export default function App() {
  const [users, setUsers] = useState([])
  const [user, setUser] = useState(null)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    api.users().then(us => { setUsers(us); setUser(us[0] || null) }).catch(() => {})
    api.health().then(setHealth).catch(() => setHealth({ status: 'error' }))
  }, [])

  return (
    <RoleContext.Provider value={{ role: user?.role || 'instructor', user, users }}>
      <div className="min-h-full flex flex-col bg-background">
        <Header user={user} users={users} setUser={setUser} health={health} />

        <main className="flex-1 max-w-[1400px] w-full mx-auto px-8 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/rubrics" replace />} />
            <Route path="/rubrics" element={<Rubrics />} />
            <Route path="/grading" element={<Grading />} />
            <Route path="/review" element={<Review />} />
            <Route path="/audit" element={<Audit />} />
          </Routes>
        </main>

        <footer className="border-t border-border bg-surface">
          <div className="max-w-[1400px] mx-auto px-8 py-3 flex justify-between text-label-sm text-ink-subtle">
            <span>GradeOps</span>
            <span>v0.1.0</span>
          </div>
        </footer>
      </div>
    </RoleContext.Provider>
  )
}

function Header({ user, users, setUser, health }) {
  return (
    <header className="bg-surface border-b border-border sticky top-0 z-30">
      <div className="max-w-[1400px] mx-auto px-8 h-14 flex items-center justify-between gap-6">
        <div className="flex items-center gap-8">
          <Wordmark />
          <nav className="flex items-center gap-1">
            {NAV.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `relative h-9 px-3 inline-flex items-center text-label-md rounded transition-colors ${
                    isActive
                      ? 'text-brand bg-brand-subtle'
                      : 'text-ink-muted hover:text-ink hover:bg-surface-muted'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-4">
         {health && (
  <div className="hidden md:flex items-center gap-1.5 text-label-sm text-ink-subtle">
    <span className={`h-1.5 w-1.5 rounded-full ${health.status === 'ok' ? 'bg-success' : 'bg-danger'}`} />
    <span>{health.status === 'ok' ? 'Connected' : 'Disconnected'}</span>
  </div>
)}
          {users.length > 0 && (
            <select
              value={user?.id || ''}
              onChange={(e) => setUser(users.find(u => String(u.id) === e.target.value))}
              className="h-8 px-2.5 pr-7 text-label-md text-ink bg-surface border border-border rounded
                         focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand"
            >
              {users.map(u => (
                <option key={u.id} value={u.id}>
                  {u.role === 'instructor' ? 'Instructor' : 'TA'} · {u.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
    </header>
  )
}

function Wordmark() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-7 w-7 rounded bg-brand flex items-center justify-center">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M3 7L6 10L11 4" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <span className="text-headline-sm tracking-tight text-ink">GradeOps</span>
    </div>
  )
}
