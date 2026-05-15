import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { adminApi, agentApi, reportsApi, exportApi } from '../api';
import './Admin.css';

function StatCard({ icon, label, value, color }) {
  return (
    <div className="stat-card card">
      <div className="stat-icon" style={{ color }}>{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function UserModal({ user, onClose, onSave }) {
  const { user: currentUser } = useAuth();
  const [form, setForm] = useState(user || { email: '', full_name: '', password: '', role: 'user' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const userRole = currentUser?.role;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await onSave(form);
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save user.');
    } finally { setLoading(false); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{user ? 'Edit User' : 'Create User'}</h3>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>×</button>
        </div>
        {error && <div className="error-banner"><span>⚠️</span> {error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Full Name</label>
            <input className="input" value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} required />
          </div>
          <div className="field">
            <label>Email</label>
            <input className="input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
          </div>
          {!user && (
            <div className="field">
              <label>Password</label>
              <input className="input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
            </div>
          )}
          {/* Only Super Admin can choose roles. Regular Admins only create 'user' role. */}
          {userRole === 'super_admin' ? (
            <div className="field">
              <label>Role</label>
              <select 
                className="input" 
                value={form.role} 
                onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
              >
                <option value="user">End User</option>
                <option value="admin">System Admin</option>
              </select>
            </div>
          ) : (
            // Hidden input to ensure role is 'user' for regular admins
            <input type="hidden" value="user" />
          )}
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {user ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function Admin() {
  const { user, logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [trips, setTrips] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [usageStats, setUsageStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [activeTab, setActiveTab] = useState('users');

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [uRes, tRes, lRes, sRes] = await Promise.all([
        adminApi.getUsers(),
        agentApi.getTrips(),
        reportsApi.getAuditLogs({ limit: 100 }),
        reportsApi.getUsageStats(30),
      ]);
      setUsers(uRes.data.users || uRes.data);
      setTrips(tRes.data.plans || []);
      setAuditLogs(lRes.data.logs || []);
      setUsageStats(sRes.data);
    } catch (err) {
      console.error('Failed to fetch admin data', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSaveUser = async (form) => {
    if (modal === 'create') {
      const { data } = await adminApi.createUser(form);
      setUsers(u => [...u, data]);
    } else {
      const { data } = await adminApi.updateUser(modal.id, form);
      setUsers(u => u.map(x => x.id === modal.id ? data : x));
    }
  };

  const handleDeleteUser = async (id) => {
    if (!window.confirm('Delete this user? This cannot be undone.')) return;
    await adminApi.deleteUser(id);
    setUsers(u => u.filter(x => x.id !== id));
  };

  const handleToggleActive = async (u) => {
    const { data } = await adminApi.updateUser(u.id, { ...u, is_active: !u.is_active });
    setUsers(us => us.map(x => x.id === u.id ? data : x));
  };

  if (loading && !users.length) return (
    <div className="admin-loading">
      <div className="spinner" style={{ width: 40, height: 40 }} />
      <p>Loading dashboard...</p>
    </div>
  );

  const activeUsers = users.filter(u => u.is_active).length;

  return (
    <div className="admin-page page-enter">
      <header className="admin-header">
        <div className="admin-header-left">
          <span className="admin-logo">✈️ TravelMind AI</span>
          <span className="badge badge-gold">{user?.role}</span>
        </div>
        <div className="admin-header-right">
          <span className="admin-greeting">Hello, {user?.full_name?.split(' ')[0]} 👋</span>
          <button className="btn btn-ghost btn-sm" onClick={logout}>Sign out</button>
        </div>
      </header>

      <div className="admin-content">
        <div className="stats-grid">
          <StatCard icon="👥" label="Total Users" value={users.length} color="#3b82f6" />
          <StatCard icon="✅" label="Active Users" value={activeUsers} color="#10b981" />
          <StatCard icon="🗺️" label="Travel Plans" value={usageStats?.total_trips_created || trips.length} color="#f59e0b" />
          <StatCard icon="📄" label="PDF Exports" value={usageStats?.total_pdf_exports || 0} color="#ef4444" />
        </div>

        <div className="admin-tabs">
          <button className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`} onClick={() => setActiveTab('users')}>👥 Users</button>
          <button className={`tab-btn ${activeTab === 'trips' ? 'active' : ''}`} onClick={() => setActiveTab('trips')}>🗺️ Travel Plans</button>
          <button className={`tab-btn ${activeTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveTab('logs')}>📋 Audit Logs</button>
        </div>

        {activeTab === 'users' && (
          <div className="tab-panel card">
            <div className="table-header">
              <h3>{user?.role === 'super_admin' ? 'User & Admin Management' : 'User Management'}</h3>
              <button className="btn btn-primary btn-sm" onClick={() => setModal('create')}>
                {user?.role === 'super_admin' ? '+ Add User/Admin' : '+ Add User'}
              </button>
            </div>
            
            <div className="table-wrapper">
              {/* Admins Section (Only for Super Admin) */}
              {user?.role === 'super_admin' && (
                <>
                  <h4 className="section-title">🛡️ System Administrators</h4>
                  <table className="data-table mb-8">
                    <thead>
                      <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
                    </thead>
                    <tbody>
                      {users.filter(u => u.role === 'admin' || u.role === 'super_admin').map(u => (
                        <tr key={u.id}>
                          <td><div className="user-cell"><div className="user-avatar-sm" style={{background: 'var(--info)'}}>{u.full_name?.[0]?.toUpperCase()}</div>{u.full_name}</div></td>
                          <td className="muted">{u.email}</td>
                          <td><span className={`badge ${u.role === 'super_admin' ? 'badge-gold' : 'badge-blue'}`}>{u.role}</span></td>
                          <td><button className={`status-toggle ${u.is_active ? 'active' : 'inactive'}`} onClick={() => handleToggleActive(u)}>{u.is_active ? '● Active' : '○ Inactive'}</button></td>
                          <td>
                            <div className="action-btns">
                              <button className="btn btn-ghost btn-sm" onClick={() => setModal(u)}>Edit</button>
                              {u.role !== 'super_admin' && <button className="btn btn-danger btn-sm" onClick={() => handleDeleteUser(u.id)}>Delete</button>}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <hr className="section-divider" />
                </>
              )}

              {/* Regular Users Section */}
              <h4 className="section-title">👤 End Users</h4>
              <table className="data-table">
                <thead>
                  <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Actions</th></tr>
                </thead>
                <tbody>
                  {users.filter(u => u.role === 'user').map(u => (
                    <tr key={u.id}>
                      <td><div className="user-cell"><div className="user-avatar-sm">{u.full_name?.[0]?.toUpperCase()}</div>{u.full_name}</div></td>
                      <td className="muted">{u.email}</td>
                      <td><span className="badge badge-green">{u.role}</span></td>
                      <td><button className={`status-toggle ${u.is_active ? 'active' : 'inactive'}`} onClick={() => handleToggleActive(u)}>{u.is_active ? '● Active' : '○ Inactive'}</button></td>
                      <td>
                        <div className="action-btns">
                          <button className="btn btn-ghost btn-sm" onClick={() => setModal(u)}>Edit</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDeleteUser(u.id)}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {users.filter(u => u.role === 'user').length === 0 && (
                    <tr><td colSpan="5" className="empty-row">No regular users found.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'trips' && (
          <div className="tab-panel card">
            <div className="table-header"><h3>Travel Plans</h3></div>
            <div className="table-wrapper">
              {!trips.length ? <div className="empty-state">No travel plans generated yet.</div> : (
                <table className="data-table">
                  <thead><tr><th>User</th><th>Destination</th><th>Dates</th><th>Cost</th><th>Created</th><th>Actions</th></tr></thead>
                  <tbody>
                    {trips.map(t => (
                      <tr key={t.id}>
                        <td className="muted">{t.user_email || 'Owner'}</td>
                        <td>🌍 {t.destination}</td>
                        <td className="muted">{t.start_date || '—'} → {t.end_date || '—'}</td>
                        <td>{t.estimated_cost_usd ? `$${t.estimated_cost_usd.toLocaleString()}` : '—'}</td>
                        <td className="muted">{new Date(t.created_at).toLocaleDateString()}</td>
                        <td>
                          <button className="btn btn-ghost btn-sm" onClick={async () => {
                            try {
                              const res = await exportApi.getTripPdf(t.id);
                              const url = window.URL.createObjectURL(new Blob([res.data]));
                              const link = document.createElement('a');
                              link.href = url;
                              link.setAttribute('download', `trip_${t.id}.pdf`);
                              document.body.appendChild(link);
                              link.click();
                              link.remove();
                              window.URL.revokeObjectURL(url);
                            } catch (err) { 
                              console.error('Download error:', err);
                              let msg = 'Failed to download PDF.';
                              if (err.response?.data instanceof Blob) {
                                // Try to parse error message from blob
                                const text = await err.response.data.text();
                                try {
                                  const json = JSON.parse(text);
                                  msg = json.detail || msg;
                                } catch (e) { msg = text || msg; }
                              } else {
                                msg = err.response?.data?.detail || err.message;
                              }
                              alert(msg);
                            }
                          }}>📄 PDF</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="tab-panel card">
            <div className="table-header"><h3>System Audit Logs</h3></div>
            <div className="table-wrapper">
              <table className="data-table">
                <thead><tr><th>Action</th><th>User</th><th>Details</th><th>Time</th></tr></thead>
                <tbody>
                  {auditLogs.map(l => (
                    <tr key={l.id}>
                      <td><span className={`badge ${l.status === 'success' ? 'badge-green' : 'badge-danger'}`}>{l.action}</span></td>
                      <td className="muted">{users.find(u => u.id === l.user_id)?.full_name || 'System'}</td>
                      <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{l.detail}</td>
                      <td className="muted">{new Date(l.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {modal && <UserModal user={modal === 'create' ? null : modal} onClose={() => setModal(null)} onSave={handleSaveUser} />}
    </div>
  );
}
