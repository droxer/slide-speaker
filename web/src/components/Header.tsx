import React, { useState, useEffect } from 'react';
import GoogleLoginButton from './GoogleLoginButton';
import { initiateGoogleLogin, getCurrentUser, logout } from '../services/auth';

type HeaderProps = {
  showTaskMonitor: boolean;
  setShowTaskMonitor: (show: boolean) => void;
};

const Header: React.FC<HeaderProps> = ({ showTaskMonitor, setShowTaskMonitor }) => {
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
            className="view-toggle"
            role="tablist"
            aria-label="View Toggle"
          >
            <button
              onClick={() => setShowTaskMonitor(false)}
              className={`toggle-btn ${!showTaskMonitor ? "active" : ""}`}
              title="Studio"
              role="tab"
              aria-selected={!showTaskMonitor}
              aria-controls="studio-panel"
              id="studio-tab"
            >
              <span className="toggle-icon" aria-hidden="true">
                ▶
              </span>
              <span className="toggle-text">Studio</span>
            </button>
            <button
              onClick={() => setShowTaskMonitor(true)}
              className={`toggle-btn ${showTaskMonitor ? "active" : ""}`}
              title="Task Monitor"
              role="tab"
              aria-selected={showTaskMonitor}
              aria-controls="monitor-panel"
              id="monitor-tab"
            >
              <span className="toggle-icon" aria-hidden="true">
                📊
              </span>
              <span className="toggle-text">Monitor</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;