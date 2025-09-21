import React from 'react';

type HeaderProps = {
  showTaskMonitor: boolean;
  setShowTaskMonitor: (show: boolean) => void;
};

const Header: React.FC<HeaderProps> = ({ showTaskMonitor, setShowTaskMonitor }) => {
  return (
    <header className="app-header">
      <div className="header-content">
        <div className="header-left">
          {/* Spacer to balance the layout */}
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