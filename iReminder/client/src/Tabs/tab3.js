// tab3.js
import React from 'react';

import "./tab3.css";
import Table from "../Features/AssignmentTable";
import ChartComponent from '../Features/GradeChart';

const Tab3 = () => {
  return (
    <div>
    <div className='tab-content'>
      <h2>Assignments</h2>
      <p>This is where we will display assignments</p>
      
    </div>
    <div className='table-style'>
    <Table>
e2
    </Table>

   <ChartComponent></ChartComponent>
    </div>
    </div>
    
  );
};

export default Tab3;