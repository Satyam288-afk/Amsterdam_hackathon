import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import { Toaster } from "react-hot-toast";

// Pages
import LandingPage from "./pages/LandingPage";
import LeadsPage from "./pages/LeadsPage";
import LeadDetailPage from "./pages/LeadDetailPage";
import RecoveryAnalyticsPage from "./pages/RecoveryAnalyticsPage";
import AppendixPage from "./pages/AppendixPage";
import RMPage from "./pages/RMPage";
import ProfileSettingsPage from "./pages/ProfileSettingsPage";
import QueueDashboard from "./pages/QueueDashboard";
import CallSummaries from "./pages/CallSummaries";
import RecoveryDashboardPage from "./pages/RecoveryDashboardPage";
import RecoveryCasePage from "./pages/RecoveryCasePage";
import BenchmarkPage from "./pages/BenchmarkPage";
import ScenarioLabPage from "./pages/ScenarioLabPage";

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-center" reverseOrder={false} />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard/*" element={<MainLayout>
              <Routes>
                <Route path="recovery" element={<RecoveryDashboardPage />} />
                <Route path="recovery/:id" element={<RecoveryCasePage />} />
                <Route path="leads" element={<LeadsPage />} />
                <Route path="leads/:id" element={<LeadDetailPage />} />
                <Route path="analytics" element={<RecoveryAnalyticsPage />} />
                <Route path="benchmark" element={<BenchmarkPage />} />
                <Route path="scenarios" element={<ScenarioLabPage />} />
                <Route path="appendix" element={<AppendixPage />} />
                <Route path="rm" element={<RMPage />} />
                <Route path="queue" element={<QueueDashboard />} />
                <Route path="summaries" element={<CallSummaries />} />
                <Route path="settings/profile" element={<ProfileSettingsPage />} />
                <Route path="*" element={<Navigate to="/dashboard/recovery" replace />} />
              </Routes>
            </MainLayout>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
