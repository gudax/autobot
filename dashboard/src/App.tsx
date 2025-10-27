import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout';
import {
  DashboardPage,
  UsersPage,
  TradingPage,
  TradesPage,
  PerformancePage,
} from './pages';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/trading" element={<TradingPage />} />
          <Route path="/positions" element={<TradingPage />} />
          <Route path="/trades" element={<TradesPage />} />
          <Route path="/performance" element={<PerformancePage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
