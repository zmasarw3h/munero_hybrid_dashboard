import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Munero AI Dashboard",
  description: "AI-powered analytics platform for business intelligence",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
