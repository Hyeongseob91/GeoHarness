import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GeoHarness — 실제 위치 찾기",
  description:
    "한국 규제로 업데이트되지 못한 구글 지도 좌표를 ML로 보정하여 실제 위치를 안내합니다.",
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
