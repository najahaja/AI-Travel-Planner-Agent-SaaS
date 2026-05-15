import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      navigate(user.role === 'user' ? '/chat' : '/admin');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Animated background orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      <div className="login-container page-enter">
        {/* Logo */}
        <div className="login-logo">
          <div className="logo-icon">✈️</div>
          <h1>TravelMind AI</h1>
          <p>Your intelligent travel planning companion</p>
        </div>

        <form className="login-form card" onSubmit={handleSubmit}>
          <h2>Welcome back</h2>
          <p className="login-subtitle">Sign in to plan your next adventure</p>

          {error && (
            <div className="error-banner">
              <span>⚠️</span> {error}
            </div>
          )}

          <div className="field">
            <label htmlFor="email">Email address</label>
            <input
              id="email"
              className="input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          <button className="btn btn-primary login-submit" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : '🚀'}
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="login-footer">
          AI-powered travel planning with RAG, real-time data &amp; smart itineraries.
        </p>
      </div>
    </div>
  );
}
