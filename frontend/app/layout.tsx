import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GeoHarness — 이 가게, 아직 있을까?",
  description:
    "구글 지도의 장소를 네이버와 교차검증하여 폐업·이전 위험을 알려드립니다.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="antialiased">{children}</body>
    </html>
  );
}
