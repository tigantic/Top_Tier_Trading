/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Allow images and API fetches from the worker service network address
  env: {
    METRICS_URL: process.env.METRICS_URL || 'http://workers:9108/metrics',
  },
};

module.exports = nextConfig;