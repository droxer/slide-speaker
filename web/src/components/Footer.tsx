import React from 'react';
import { useI18n } from '@/i18n/hooks';

type FooterProps = {
  queueUnavailable: boolean;
  redisLatencyMs: number | null;
  uiTheme: "flat" | "classic" | "material";
  setUiTheme: (theme: "flat" | "classic" | "material") => void;
};

const Footer: React.FC<FooterProps> = ({ queueUnavailable, redisLatencyMs, uiTheme, setUiTheme }) => {
  const { t } = useI18n();
  const systemStatusLabel = queueUnavailable ? t('footer.queueUnavailable') : t('footer.queueOk');
  const systemStatusTitle = queueUnavailable
    ? t('footer.queueTooltipUnavailable')
    : redisLatencyMs != null
      ? t('footer.queueTooltipLatency', { latency: redisLatencyMs }, `System status OK • ${redisLatencyMs}ms`)
      : t('footer.queueTooltipOk');

  return (
    <footer className="app-footer" role="contentinfo">
      <div className="footer-content">
        <p className="footer-note">{t('footer.slogan')}</p>
        <div className="footer-right">
          <div
            className="health-indicator"
            role="status"
            aria-live="polite"
            title={systemStatusTitle}
          >
            <span className={`dot ${queueUnavailable ? 'down' : 'ok'}`} aria-hidden />
            <span className="label">{systemStatusLabel}</span>
          </div>
          <div
            className="view-toggle theme-toggle"
            role="tablist"
            aria-label="Theme Toggle"
          >
            <button
              onClick={() => setUiTheme("classic")}
              className={`toggle-btn ${uiTheme === "classic" ? "active" : ""}`}
              title={t('footer.theme.classic')}
              role="tab"
              aria-selected={uiTheme === "classic"}
              aria-controls="classic-theme-panel"
            >
              <span className="toggle-text">{t('footer.theme.classic')}</span>
            </button>
            <button
              onClick={() => setUiTheme("flat")}
              className={`toggle-btn ${uiTheme === "flat" ? "active" : ""}`}
              title={t('footer.theme.flat')}
              role="tab"
              aria-selected={uiTheme === "flat"}
              aria-controls="flat-theme-panel"
            >
              <span className="toggle-text">{t('footer.theme.flat')}</span>
            </button>
            <button
              onClick={() => setUiTheme("material")}
              className={`toggle-btn ${uiTheme === "material" ? "active" : ""}`}
              title={t('footer.theme.material')}
              role="tab"
              aria-selected={uiTheme === "material"}
              aria-controls="material-theme-panel"
            >
              <span className="toggle-text">{t('footer.theme.material')}</span>
            </button>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
