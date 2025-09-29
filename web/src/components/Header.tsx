import React, { useState, useEffect } from 'react';
import GoogleLoginButton from './GoogleLoginButton';
import { initiateGoogleLogin, getCurrentUser, logout } from '../services/auth';

export type AppView = 'studio' | 'creations';

type HeaderProps = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
};

const Header: React.FC<HeaderProps> = ({ activeView, onNavigate }) => {
  const [user, setUser] = useState<any>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);

  // Check for existing session on component mount
  useEffect(() => {
    const token = localStorage.getItem('slidespeaker_session_token');
    if (token) {
      setSessionToken(token);
      // Fetch user data
      getCurrentUser(token).then(setUser).catch(console.error);
    }
  }, []);

  const handleLogin = () => {
    initiateGoogleLogin();
  };

  const handleLogout = async () => {
    if (sessionToken) {
      await logout(sessionToken);
      localStorage.removeItem('slidespeaker_session_token');
      setSessionToken(null);
      setUser(null);
      // Reload the page to show the logged out view
      window.location.reload();
    }
  };

  return (
    <header className="app-header">
      <div className="header-content">
        <div className="header-left">
          {user ? (
            <div className="user-info">
              <span>Welcome, {user.name}</span>
              <button onClick={handleLogout} className="logout-btn">
                Logout
              </button>
            </div>
          ) : (
            <GoogleLoginButton onClick={handleLogin} />
          )}
        </div>
        <div className="header-center">
          <h1>SlideSpeaker AI</h1>
          <p>Transform slides into AI-powered videos</p>
        </div>
        <div className="header-right">
          <div
            className="view-toggle ai-toggle"
            role="tablist"
            aria-label="View Toggle"
          >
            <button
              onClick={() => onNavigate('studio')}
              className={`toggle-btn ${activeView === 'studio' ? "active" : ""}`}
              title="Studio"
              role="tab"
              aria-selected={activeView === 'studio'}
              aria-controls="studio-panel"
              id="studio-tab"
            >
              <span className="toggle-icon" aria-hidden="true">
                ▶
              </span>
              <span className="toggle-text">Studio</span>
            </button>
            <button
              onClick={() => onNavigate('creations')}
              className={`toggle-btn ${activeView === 'creations' ? "active" : ""}`}
              title="Creations"
              role="tab"
              aria-selected={activeView === 'creations'}
              aria-controls="monitor-panel"
              id="monitor-tab"
            >
              <span className="toggle-icon" aria-hidden="true">
                🎬
              </span>
              <span className="toggle-text">Creations</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
