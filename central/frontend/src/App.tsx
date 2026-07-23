import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { CamerasPage } from './pages/CameraPage';
import { SettingsPage } from './pages/SettingsPage';
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <Router>
      <AppLayout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/cameras" element={<CamerasPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
          <Toaster/>
      </AppLayout>
    </Router>
  );
}

export default App;