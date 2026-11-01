import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow client scripts and HMR when accessing chobitmac over LAN or Tailscale.
  allowedDevOrigins: [
    "192.168.*.*",
    "100.*.*.*",
    "chobitmac",
    "chobitmac.local",
  ],
  turbopack: {
    rules: {
      "*.css": { loaders: ["@tailwindcss/turbopack"], as: "*.css" },
    },
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_URL ?? "http://127.0.0.1:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
