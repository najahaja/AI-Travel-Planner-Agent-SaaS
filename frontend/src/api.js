import axios from 'axios';

const API = axios.create({ baseURL: '/api' });

// Attach JWT on every request
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
API.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post('/api/auth/refresh', { refresh_token: refresh });
          localStorage.setItem('access_token', data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return API(original);
        } catch {
          localStorage.clear();
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: (email, password) => API.post('/auth/login', { email, password }),
  me: () => API.get('/auth/me'),
};

export const agentApi = {
  chat: (message, session_id) => API.post('/agent/chat', { message, session_id }),
  getSessions: () => API.get('/agent/sessions'),
  getSession: (id) => API.get(`/agent/sessions/${id}`),
  deleteSession: (id) => API.delete(`/agent/sessions/${id}`),
  getTrips: () => API.get('/agent/trips'),
  getTrip: (id) => API.get(`/agent/trips/${id}`),
};

export const adminApi = {
  getUsers: () => API.get('/admin/users'),
  createUser: (data) => API.post('/admin/users', data),
  updateUser: (id, data) => API.put(`/admin/users/${id}`, data),
  deleteUser: (id, data) => API.delete(`/admin/users/${id}`, { data }),
};

export const exportApi = {
  getTripPdf: (trip_id) => API.get(`/export/trips/${trip_id}/pdf`, { responseType: 'blob' }),
};

export const reportsApi = {
  getAuditLogs: (params) => API.get('/reports/audit-logs', { params }),
  getUsageStats: (days) => API.get('/reports/usage-stats', { params: { days } }),
};

export default API;
