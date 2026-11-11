import { NavLink, Route, Routes } from "react-router-dom";
import CaseBoard from "./pages/CaseBoard";
import Receipt from "./pages/Receipt";
import TrialRoom from "./pages/TrialRoom";

export default function App() {
  return (
    <>
      <a href="#main" className="skip">
        Skip to content
      </a>
      <header className="site-header">
        <NavLink to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            議
          </span>
          <span>Crypto Council</span>
        </NavLink>
        <nav aria-label="Primary">
          <NavLink to="/" end>
            Trial room
          </NavLink>
          <NavLink to="/board">Case board</NavLink>
        </nav>
      </header>
      <main id="main">
        <Routes>
          <Route path="/" element={<TrialRoom />} />
          <Route path="/case/:id" element={<TrialRoom />} />
          <Route path="/board" element={<CaseBoard />} />
          <Route path="/receipt/:id" element={<Receipt />} />
          <Route path="*" element={<div className="page empty">That page does not exist.</div>} />
        </Routes>
      </main>
    </>
  );
}
