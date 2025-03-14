import React from 'react';
import { Link } from 'react-router-dom';

const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="header-content">
        <h1>
          <Link to="/">Time Series Analyzer</Link>
        </h1>
        <nav>
          <ul>
            <li>
              <Link to="/">Upload</Link>
            </li>
            <li>
              <a href="https://github.com/fabioeloi/time-series-analyzer" target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
};

export default Header;