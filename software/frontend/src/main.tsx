import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import { ResearchErrorBoundary } from './components/ResearchErrorBoundary';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ResearchErrorBoundary fallbackTitle="AuscultaForge Render Error">
      <App />
    </ResearchErrorBoundary>
  </StrictMode>,
);
