import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from './contexts/ConfigContext';
import ChatInterface from './components/ChatInterface';
import './App.css';

function App() {
  return (
    <ConfigProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/" element={<ChatInterface />} />
          </Routes>
        </div>
      </Router>
    </ConfigProvider>
  );
}

export default App;
