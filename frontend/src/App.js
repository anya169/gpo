import logo from './logo.svg';
import './App.css';
import HelloPage from './pages/HelloPage';
import RegistrationPage from './pages/RegistrationPage';
import CodePage from './pages/CodePage';
import BreathingPracticePage from './pages/BreathingPracticePage';
import PhysicalActivityPage from './pages/PhysicalActivityPage';
import CalibrationPage from './pages/CalibrationPage';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import SessionPage from './pages/SessionPage'


function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HelloPage />} />
        <Route path="/registration" element={<RegistrationPage />} />
        <Route path="/check_code" element={<CodePage />} />
        <Route path="/breathing-exercise" element={<BreathingPracticePage />} />
        <Route path="/calibrate" element={<CalibrationPage />} />
        <Route path="/movement-exercise" element={<PhysicalActivityPage />} />
        <Route path="/session" element={<SessionPage />} />
      </Routes>
    </Router>
  );
}

export default App;
