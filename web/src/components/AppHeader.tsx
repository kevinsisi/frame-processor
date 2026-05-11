import { Link, NavLink } from "react-router-dom";

import { APP_VERSION } from "@/version";

import "./AppHeader.css";

export function AppHeader() {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <Link to="/" className="app-header__brand">
          <span className="brand-mark">F·P</span>
          <span className="brand-word">
            Frame <span className="em">·</span> Processor
          </span>
          <span
            className="app-header__version"
            title={`build version v${APP_VERSION}`}
          >
            v{APP_VERSION}
          </span>
        </Link>

        <nav className="app-header__nav">
          <NavLink to="/upload" className="nav-link">
            上傳
          </NavLink>
          <NavLink to="/preview" className="nav-link">
            預覽
          </NavLink>
          <NavLink to="/export" className="nav-link nav-link--quiet">
            匯出
          </NavLink>
          <NavLink to="/settings" className="nav-link nav-link--quiet">
            設定
          </NavLink>
        </nav>
      </div>
      <div className="app-header__rule" aria-hidden />
    </header>
  );
}
