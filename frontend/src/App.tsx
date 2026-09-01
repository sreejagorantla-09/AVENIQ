import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Playground from './pages/Playground';
import Passport from './pages/Passport';
import Products from './pages/Products';
import Policies from './pages/Policies';
import Agents from './pages/Agents';
import Negotiation from './pages/Negotiation';
import Transactions from './pages/Transactions';
import Audit from './pages/Audit';
import Integrations from './pages/Integrations';
import Settings from './pages/Settings';
import Approvals from './pages/Approvals';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="playground" element={<Playground />} />
          <Route path="passport" element={<Passport />} />
          <Route path="products" element={<Products />} />
          <Route path="policies" element={<Policies />} />
          <Route path="agents" element={<Agents />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="negotiation" element={<Negotiation />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="audit" element={<Audit />} />
          <Route path="integrations" element={<Integrations />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
