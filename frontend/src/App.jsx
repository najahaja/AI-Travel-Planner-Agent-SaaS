import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Admin from './pages/Admin';

function PrivateRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  if (loading) return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span className="spinner" style={{ width: 40, height: 40 }} />
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/chat" replace />;
  return children;
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === 'user' ? '/chat' : '/admin'} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/chat" element={<PrivateRoute><Chat /></PrivateRoute>} />
          <Route path="/chat/:sessionId" element={<PrivateRoute><Chat /></PrivateRoute>} />
          <Route path="/admin" element={<PrivateRoute allowedRoles={['admin','super_admin']}><Admin /></PrivateRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
