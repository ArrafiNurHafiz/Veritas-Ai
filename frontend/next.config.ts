import type { NextConfig } from "next";

const HARNESS_URL =
  process.env.HARNESS_URL ||
  process.env.NEXT_PUBLIC_HARNESS_URL ||
  "http://127.0.0.1:8002";

const nextConfig: NextConfig = {
  output: 'standalone',
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${HARNESS_URL}/api/v1/:path*`,
      },
      {
        source: "/health/:path*",
        destination: `${HARNESS_URL}/health/:path*`,
      },
    ];
  },
};

export default nextConfig;
