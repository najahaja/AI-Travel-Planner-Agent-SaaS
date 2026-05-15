import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../context/AuthContext';
import { agentApi, exportApi } from '../api';
import './Chat.css';

function Sidebar({ sessions, activeId, onSelect, onNew, onDelete, user, onLogout }) {
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation?')) return;
    setDeleting(id);
    try { await agentApi.deleteSession(id); onDelete(id); }
    finally { setDeleting(null); }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span>✈️</span>
          <span className="sidebar-logo-text">TravelMind AI</span>
        </div>
      </div>

      <button className="btn btn-primary new-chat-btn" onClick={onNew}>
        <span>+</span> New Chat
      </button>

      <div className="sidebar-section-label">Recent Conversations</div>
      <div className="sessions-list">
        {sessions.length === 0 && (
          <div className="sessions-empty">No conversations yet.<br />Start a new chat!</div>
        )}
        {sessions.map(s => (
          <div
            key={s.id}
            className={`session-item ${s.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(s.id)}
          >
            <div className="session-icon">💬</div>
            <div className="session-info">
              <div className="session-title">{s.title}</div>
              <div className="session-meta">
                {s.message_count} messages
                {s.travel_plan_id && <span className="sidebar-trip-badge">📄 Plan</span>}
              </div>
            </div>
            <button
              className="session-delete"
              onClick={e => handleDelete(e, s.id)}
              disabled={deleting === s.id}
              title="Delete"
            >
              {deleting === s.id ? '⟳' : '×'}
            </button>
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar">{user?.full_name?.[0]?.toUpperCase() || '?'}</div>
          <div className="user-details">
            <div className="user-name">{user?.full_name}</div>
            <div className="user-role badge badge-gold">{user?.role}</div>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onLogout}>Sign out</button>
      </div>
    </aside>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div className={`message-row ${isUser ? 'user-row' : 'ai-row'}`}>
      {!isUser && <div className="ai-avatar">🤖</div>}
      <div className={`message-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
        {isUser ? (
          <p>{msg.content}</p>
        ) : (
          <div className="markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>
        )}
      </div>
      {isUser && <div className="user-avatar-small" />}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="message-row ai-row">
      <div className="ai-avatar">🤖</div>
      <div className="message-bubble ai-bubble typing-bubble">
        <div className="typing-dots">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

export default function Chat() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [sessions, setSessions] = useState([]);
  const [messages, setMessages] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(sessionId ? parseInt(sessionId) : null);
  const [currentTripId, setCurrentTripId] = useState(null);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [loadingSession, setLoadingSession] = useState(false);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  // Load sessions list
  const loadSessions = useCallback(async () => {
    try {
      const { data } = await agentApi.getSessions();
      setSessions(data.sessions || []);
    } catch (err) { console.error('Failed to load sessions', err); }
  }, []);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // Load messages when session changes
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setCurrentTripId(null);
      return;
    }
    setLoadingSession(true);
    agentApi.getSession(activeSessionId)
      .then(({ data }) => {
        setMessages(data.messages || []);
        setCurrentTripId(data.travel_plan_id);
        navigate(`/chat/${activeSessionId}`, { replace: true });
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingSession(false));
  }, [activeSessionId, navigate]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleNew = () => {
    setActiveSessionId(null);
    setMessages([]);
    setCurrentTripId(null);
    navigate('/chat', { replace: true });
    textareaRef.current?.focus();
  };

  const handleSelectSession = (id) => {
    setActiveSessionId(id);
  };

  const handleDeleteSession = (id) => {
    setSessions(s => s.filter(x => x.id !== id));
    if (activeSessionId === id) handleNew();
  };

  const handleExportPdf = async () => {
    if (!currentTripId || exporting) return;
    setExporting(true);
    try {
      const response = await exportApi.getTripPdf(currentTripId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `itinerary_${currentTripId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export error:', err);
      let msg = 'Failed to export PDF.';
      if (err.response?.data instanceof Blob) {
        const text = await err.response.data.text();
        try {
          const json = JSON.parse(text);
          msg = json.detail || msg;
        } catch (e) { msg = text || msg; }
      } else {
        msg = err.response?.data?.detail || err.message;
      }
      alert(msg);
    } finally {
      setExporting(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput('');

    const userMsg = { role: 'user', content: text, id: Date.now() };
    setMessages(m => [...m, userMsg]);
    setSending(true);

    try {
      const { data } = await agentApi.chat(text, activeSessionId);
      const aiMsg = { role: 'assistant', content: data.response, id: Date.now() + 1 };
      setMessages(m => [...m, aiMsg]);
      
      if (data.travel_plan_id) {
        setCurrentTripId(data.travel_plan_id);
      }

      if (!activeSessionId) {
        setActiveSessionId(data.session_id);
        navigate(`/chat/${data.session_id}`, { replace: true });
      }
      loadSessions();
    } catch (err) {
      const errMsg = { role: 'assistant', content: '⚠️ ' + (err.response?.data?.detail || 'Something went wrong. Please try again.'), id: Date.now() + 1 };
      setMessages(m => [...m, errMsg]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    '🗺️ Plan a 7-day trip to Tokyo',
    '💰 What\'s the budget for Paris for 2 people?',
    '🌤️ Best time to visit Bali?',
    '🏖️ Top beaches in Thailand',
  ];

  return (
    <div className="chat-layout">
      <Sidebar
        sessions={sessions}
        activeId={activeSessionId}
        onSelect={handleSelectSession}
        onNew={handleNew}
        onDelete={handleDeleteSession}
        user={user}
        onLogout={logout}
      />

      <main className="chat-main">
        <header className="chat-header">
          <div className="chat-header-left">
            <h2>
              {activeSessionId
                ? sessions.find(s => s.id === activeSessionId)?.title || 'Conversation'
                : 'New Conversation'}
            </h2>
          </div>
          <div className="chat-header-right">
            {currentTripId && (
              <button 
                className="btn btn-ghost btn-sm export-btn" 
                onClick={handleExportPdf}
                disabled={exporting}
              >
                {exporting ? <span className="spinner" style={{ width: 14, height: 14 }} /> : '📄'} 
                {exporting ? 'Generating PDF...' : 'Download Itinerary (PDF)'}
              </button>
            )}
            <span className="badge badge-green">🟢 Online</span>
          </div>
        </header>

        <div className="messages-area">
          {!activeSessionId && messages.length === 0 && (
            <div className="welcome-screen">
              <div className="welcome-icon">🌍</div>
              <h1>Where do you want to go?</h1>
              <p>I can plan itineraries, estimate budgets, check weather, and find hidden gems for any destination in the world.</p>
              <div className="suggestions">
                {suggestions.map((s, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => setInput(s.replace(/^.{2}/, '').trim())}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {loadingSession ? (
            <div className="loading-session">
              <div className="spinner" style={{ width: 32, height: 32 }} />
              <p>Loading conversation...</p>
            </div>
          ) : (
            <>
              {messages.map((msg) => <Message key={msg.id || msg.timestamp} msg={msg} />)}
              {sending && <TypingIndicator />}
            </>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="input-area">
          <div className="input-box">
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder="Ask me about any destination, itinerary, budget, or travel tips..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={sending}
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!input.trim() || sending}
            >
              {sending ? <span className="spinner" style={{ width: 18, height: 18 }} /> : '➤'}
            </button>
          </div>
          <div className="input-hint">
            <span className="hint-key">Enter</span> to send · <span className="hint-key">Shift</span> + <span className="hint-key">Enter</span> for new line
          </div>
        </div>
      </main>
    </div>
  );
}
