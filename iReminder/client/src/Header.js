// Header.js
import React from "react";
import "./Header.css";
import { Link } from 'react-router-dom';

const Header = () => {
  return (
    <header>
      <nav className="header-nav">
        <Link to="/" className="header-link">
          <h1>iReminder</h1>
        </Link>
        <div className="header-tabs">
          <Link to="/tab1" className="header-tab">About us</Link>
          {/* <Link to="/tab2" className="header-tab">Notepad</Link> */}
          <Link to="/tab3" className="header-tab">Assignments</Link>
          <Link to="/tab4" className="header-tab">Calendar</Link>
          {/* <Link to="/tab5" className="header-tab">Testing Stuff</Link> */}
          <Link to="/tab6" className="header-tab">Notepad</Link>
        </div>
      </nav>

    </header>
  );
};

export default Header;