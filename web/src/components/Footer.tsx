import React from 'react';
import { useI18n } from '@/i18n/hooks';
import ThemeToggle from '@/components/ThemeToggle';

type FooterProps = {
  queueUnavailable: boolean;
  redisLatencyMs: number | null;
};

const Footer: React.FC<FooterProps> = ({ queueUnavailable, redisLatencyMs }) => {
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
          <ThemeToggle ariaLabel={t('footer.theme.toggleLabel', undefined, 'Theme toggle')} />
        </div>
      </div>
    </footer>
  );
};

export default Footer;
