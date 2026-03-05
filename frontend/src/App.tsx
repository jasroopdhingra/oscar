import { BrowserRouter, Routes, Route } from "react-router-dom";
import PoliciesPage from "./pages/PoliciesPage";
import PolicyDetailPage from "./pages/PolicyDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="max-w-6xl mx-auto flex items-center gap-3">
            <div className="w-8 h-8 bg-gray-900 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              O
            </div>
            <h1 className="text-lg font-semibold text-gray-900">
              Guidelines Explorer
            </h1>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-6 py-8">
          <Routes>
            <Route path="/" element={<PoliciesPage />} />
            <Route path="/policies/:id" element={<PolicyDetailPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
