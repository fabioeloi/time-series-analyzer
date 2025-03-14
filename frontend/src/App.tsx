import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import FileUpload from './components/FileUpload';
import TimeSeriesViewer from './components/TimeSeriesViewer';
import Header from './components/Header';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Header />
        <main className="App-main">
          <Routes>
            <Route path="/" element={<FileUpload />} />
            <Route path="/view/:analysisId" element={<TimeSeriesViewer />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;