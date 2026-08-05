import type { Metadata } from "next";
import "./globals.css";
import "./enterprise.css";

export const metadata: Metadata = {
  title: "ForgeOps — Mission Control",
  description: "Autonomous AI data and cloud engineer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="header">
          <div className="header-inner">
            <a href="/" className="logo">
              <span className="logo-forge">Forge</span>
              <span className="logo-ops">Ops</span>
            </a>
            <nav className="nav" aria-label="Primary navigation">
              <a href="/" className="nav-link">Missions</a>
              <a href="/approvals" className="nav-link">Approvals</a>
              <a href="/skills" className="nav-link">Skills</a>
              <a href="/memory" className="nav-link">Memory</a>
            </nav>
          </div>
        </header>
        <main className="main">{children}</main>
        <footer className="footer">
          <span>ForgeOps AI · Autonomous data and cloud engineer</span>
        </footer>
      </body>
    </html>
  );
}
