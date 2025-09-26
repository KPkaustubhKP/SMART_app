// React entry point (minimal setup for build compatibility)
import React from 'react';
import ReactDOM from 'react-dom/client';

const App = () => {
  return <div>Smart Agriculture Dashboard - Running on vanilla HTML/JS</div>;
};

// Only render if root element exists (for build compatibility)
const root = document.getElementById('root');
if (root) {
  ReactDOM.createRoot(root).render(<App />);
}
