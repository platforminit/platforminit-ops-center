import { Routes, Route, Navigate } from "react-router-dom";
import ProblemsPage from "./ProblemsPage";
import "./App.css";

function App() {
  return (
    <Routes>
      <Route path="/problems" element={<ProblemsPage />} />
      <Route path="*" element={<Navigate to="/problems" replace />} />
    </Routes>
  );
}

export default App;
