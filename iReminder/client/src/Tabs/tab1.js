// tab1.js
import React from 'react';

import "./tab1.css";

const Tab1 = () => {
  return (
    <div>
    <div className = 'tab-content'>
      <h2>About Us </h2>
      <p>Your Learning, Streamlined.</p>

    </div>

    <div className='list-content'>
      <h2> What can we do?</h2>
      <li>Organize all your classes</li>
      <li>Track assignments</li>
      <li>Display all your deadlines</li>
      <li>Connect ALL your learning tools</li>
    </div>
    </div>
  );
};

export default Tab1;