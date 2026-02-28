import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export", // 정적 빌드 → FastAPI에서 서빙
  trailingSlash: true,
  images: {
    unoptimized: true, // static export에서는 Image Optimization 비활성화
  },
};

export default nextConfig;
