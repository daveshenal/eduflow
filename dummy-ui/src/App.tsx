import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConfigProvider } from './contexts/ConfigContext';
import ChatInterface from './components/Sidebar';
import './App.css';

function App() {
  return (
    <ConfigProvider>
      <Router>
        <div className="App">
          <main>
            <Routes>
              <Route path="/" element={<ChatInterface />} />
            </Routes>
          </main>
        </div>
      </Router>
    </ConfigProvider>
  );
}

export default App;