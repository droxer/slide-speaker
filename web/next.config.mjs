import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const nextConfig = {
  reactStrictMode: true,
  // Inline critical CSS
  experimental: {
    optimizeCss: true,
  },
};

export default withNextIntl(nextConfig);
