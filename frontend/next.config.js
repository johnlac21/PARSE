/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy /api to backend so the browser uses same-origin requests (avoids CORS and "Failed to fetch").
    const backend = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    return [{ source: '/api/:path*', destination: `${backend}/api/:path*` }];
  },
};

module.exports = nextConfig;
