// tabs.js
import React from 'react';
import { Link } from 'react-router-dom';

const Tabs = () => {
  return (
    <nav>
      <ul>
        <li><Link to="/tab1">Tab 1</Link></li>
        <li><Link to="/tab2">Tab 2</Link></li>
        <li><Link to="/tab3">Tab 3</Link></li>
        <li><Link to="/tab4">Tab 4</Link></li>
        <li><Link to="/tab5">Tab 5</Link></li>
        <li><Link to="/tab6">Tab 6</Link></li>
      </ul>
    </nav>
  );
};

export default Tabs;