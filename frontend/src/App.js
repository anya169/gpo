import logo from './logo.svg';
import './App.css';
import HelloPage from './pages/HelloPage';
import RegistrationPage from './pages/RegistrationPage';
import CodePage from './pages/CodePage';
import BreathingPracticePage from './pages/BreathingPracticePage';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';


function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HelloPage />} />
        <Route path="/registration" element={<RegistrationPage />} />
        <Route path="/check_code" element={<CodePage />} />
        <Route path="/breathe" element={<BreathingPracticePage />} />
      </Routes>
    </Router>
  );
}

export default App;
