/** @type {import('next').NextConfig} */
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

const nextConfig = {
  async rewrites() {
    return [
      // Proxy all Flask API calls through Next.js (avoids browser CORS entirely)
      {
        source: "/api/samples/:path*",
        destination: `${API_BASE}/api/samples/:path*`,
      },
      {
        source: "/api/style-preview",
        destination: `${API_BASE}/api/style-preview`,
      },
      {
        source: "/api/onboarding/:path*",
        destination: `${API_BASE}/api/onboarding/:path*`,
      },
      {
        source: "/api/history/:path*",
        destination: `${API_BASE}/api/history/:path*`,
      },
      {
        source: "/api/pm/:path*",
        destination: `${API_BASE}/api/pm/:path*`,
      },
      {
        source: "/api/drafts/:path*",
        destination: `${API_BASE}/api/drafts/:path*`,
      },
      {
        source: "/api/tasks/:path*",
        destination: `${API_BASE}/api/tasks/:path*`,
      },
      {
        source: "/api/tasks",
        destination: `${API_BASE}/api/tasks`,
      },
      {
        source: "/api/escalation",
        destination: `${API_BASE}/api/escalation`,
      },
      {
        source: "/api/reports/:path*",
        destination: `${API_BASE}/api/reports/:path*`,
      },
    ];
  },
};

export default nextConfig;
