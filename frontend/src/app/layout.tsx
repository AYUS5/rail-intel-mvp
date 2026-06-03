import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Rail Intel MVP",
  description: "Railway route intelligence and hidden seat opportunity explorer.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

