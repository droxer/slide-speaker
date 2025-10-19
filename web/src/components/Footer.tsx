import React from 'react';
import { useI18n } from '@/i18n/hooks';

type FooterProps = {
  queueUnavailable: boolean;
  redisLatencyMs: number | null;
};

const Footer = ({ queueUnavailable, redisLatencyMs }: FooterProps) => {
  const { t } = useI18n();
  const systemStatusLabel = queueUnavailable ? t('footer.queueUnavailable') : t('footer.queueOk');

  // For hydration compatibility, we need to ensure the same initial title is rendered
  // on both server and client - we'll use a stable value initially and update after mount
  const [title, setTitle] = React.useState(() =>
    queueUnavailable
      ? t('footer.queueTooltipUnavailable')
      : t('footer.queueTooltipOk')
  );

  // Update the title after the component mounts to reflect the actual latency
  React.useEffect(() => {
    const newTitle = queueUnavailable
      ? t('footer.queueTooltipUnavailable')
      : redisLatencyMs != null
        ? t('footer.queueTooltipLatency', { latency: redisLatencyMs }, `System status OK • ${redisLatencyMs}ms`)
        : t('footer.queueTooltipOk');

    setTitle(newTitle);
  }, [queueUnavailable, redisLatencyMs, t]);

  return (
    <footer className="app-footer" role="contentinfo">
      <div className="footer-content">
        <p className="footer-note">{t('footer.slogan')}</p>
        <div className="footer-right">
          <div
            className="health-indicator"
            role="status"
            aria-live="polite"
            title={title}
          >
            <span className={`dot ${queueUnavailable ? 'down' : 'ok'}`} aria-hidden="true" />
            <span className="label">{systemStatusLabel}</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
