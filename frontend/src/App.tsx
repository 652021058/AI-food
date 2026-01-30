import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import QCLive from "./pages/QCLive";
import QCHistory from "./pages/QCHistory";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <div className="app-container">
        {/* ================= HEADER ================= */}
        <header className="qc-header">
          <div className="qc-container">
            <div className="qc-header-content">
              <div className="qc-header-left">
                <div className="qc-logo">
                  <img
                    src="/src/image/images-removebg-preview.png"
                    alt="i-Tail Logo"
                    className="qc-header-logo"
                  />
                </div>

                <div>
                  <h1 className="qc-title">
                    Quality Control Management System
                  </h1>
                  <p className="qc-subtitle">
                    Food Weight Analysis and Inspection Module v2.1
                  </p>
                </div>
              </div>

              <div className="qc-header-right">
                <p className="qc-department">
                  Department of Quality Assurance
                </p>
                <p className="qc-session">
                  Session ID: QC-{new Date().getFullYear()}-
                  {String(new Date().getMonth() + 1).padStart(2, "0")}
                  {String(new Date().getDate()).padStart(2, "0")}-001
                </p>
              </div>
            </div>
          </div>
        </header>

        {/* ================= NAVBAR ================= */}
        <nav className="app-navbar">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              isActive ? "app-link app-link-active" : "app-link"
            }
          >
            QC Live
          </NavLink>

          <NavLink
            to="/history"
            className={({ isActive }) =>
              isActive ? "app-link app-link-active" : "app-link"
            }
          >
            History
          </NavLink>
        </nav>

        {/* ================= CONTENT ================= */}
        <main className="app-content">
          <Routes>
            {/* หน้าแรก */}
            <Route index element={<QCLive />} />

            {/* History */}
            <Route path="history" element={<QCHistory />} />

            {/* fallback กันจอดำ */}
            <Route path="*" element={<QCLive />} />
          </Routes>
        </main>
      </div>

      {/* ================= FOOTER ================= */}
      <footer className="qc-footer">
        <div className="qc-container">
          <div className="qc-footer-content">
            <p>
              © {new Date().getFullYear()} Quality Control Management System. All
              Rights Reserved.
            </p>
            <p className="qc-footer-version">
              <span>System Version 2.1.0</span>
              <span> • </span>
              <span>
                Build {new Date().getFullYear()}
                {String(new Date().getMonth() + 1).padStart(2, "0")}
                {String(new Date().getDate()).padStart(2, "0")}
              </span>
            </p>
          </div>
        </div>
      </footer>
    </BrowserRouter>
  );
}

export default App;
