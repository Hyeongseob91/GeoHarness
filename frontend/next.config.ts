import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";

const nextConfig: NextConfig = {
  ...(isProd && { output: "export" }), // 프로덕션만 정적 빌드
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // dev 모드에서 /api/v1/* → FastAPI 백엔드로 프록시
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
