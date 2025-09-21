import React from 'react';

type FooterProps = {
  queueUnavailable: boolean;
  redisLatencyMs: number | null;
  uiTheme: "flat" | "classic" | "material";
  setUiTheme: (theme: "flat" | "classic" | "material") => void;
};

const Footer: React.FC<FooterProps> = ({ queueUnavailable, redisLatencyMs, uiTheme, setUiTheme }) => {
  return (
    <footer className="app-footer" role="contentinfo">
      <div className="footer-content">
        <p className="footer-note">
          Powered by SlideSpeaker AI • Where presentations become your
          masterpiece
        </p>
        <div className="footer-right">
          <div
            className="health-indicator"
            role="status"
            aria-live="polite"
            title={queueUnavailable ? 'Queue unavailable' : (redisLatencyMs != null ? `Queue OK • ${redisLatencyMs}ms` : 'Queue OK')}
          >
            <span className={`dot ${queueUnavailable ? 'down' : 'ok'}`} aria-hidden />
            <span className="label">{queueUnavailable ? 'Queue: Unavailable' : 'Queue: OK'}</span>
          </div>
          <div
            className="view-toggle theme-toggle"
            role="tablist"
            aria-label="Theme Toggle"
          >
            <button
              onClick={() => setUiTheme("classic")}
              className={`toggle-btn ${uiTheme === "classic" ? "active" : ""}`}
              title="Classic Theme"
              role="tab"
              aria-selected={uiTheme === "classic"}
              aria-controls="classic-theme-panel"
            >
              <span className="toggle-text">Classic</span>
            </button>
            <button
              onClick={() => setUiTheme("flat")}
              className={`toggle-btn ${uiTheme === "flat" ? "active" : ""}`}
              title="Flat Theme"
              role="tab"
              aria-selected={uiTheme === "flat"}
              aria-controls="flat-theme-panel"
            >
              <span className="toggle-text">Flat</span>
            </button>
            <button
              onClick={() => setUiTheme("material")}
              className={`toggle-btn ${uiTheme === "material" ? "active" : ""}`}
              title="Material Theme"
              role="tab"
              aria-selected={uiTheme === "material"}
              aria-controls="material-theme-panel"
            >
              <span className="toggle-text">Material</span>
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;