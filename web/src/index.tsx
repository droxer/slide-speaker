import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import './styles/index.scss';
import App from './App';
import { queryClient } from './services/queryClient';
import { UIProvider } from './context/UIContext';

const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <UIProvider>
          <App />
        </UIProvider>
      </QueryClientProvider>
    </React.StrictMode>
  );
}
