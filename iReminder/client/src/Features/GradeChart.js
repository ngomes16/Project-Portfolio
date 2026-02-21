// import React from 'react';
// import { Line } from 'react-chartjs-2';

// import { Chart as ChartJS, Legend, registerables } from 'chart.js';
// import { Chart } from 'react-chartjs-2';
import "./GradeChart.css";

import React, { useState, useEffect } from 'react';
import Chart from 'chart.js/auto';
import assignments from '../Tabs/assignments';


// ChartJS.register(...registerables);


const ChartComponent = () => {
  const [homeworkData, setHomeworkData] = React.useState(()=>{
      let localData = localStorage.getItem('userData');
      if(!localData){
          return [];
      }
      localData = assignments.concat(JSON.parse(localData));
      return localData.length ? localData : [];
  });

  useEffect(() => { 
    const assignmentCounts = {};
    homeworkData.forEach(item => {
      (assignmentCounts[item.CourseName]) ? assignmentCounts[item.CourseName]++ : assignmentCounts[item.CourseName] = 1;
    });

    const labels = Object.keys(assignmentCounts);
    const data = Object.values(assignmentCounts);

    //AI suggestion
    const existingChart = Chart.getChart('barChart');
    if (existingChart) {
      existingChart.destroy();
    }

    //Reference to AI
    const ctx = document.getElementById('barChart').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Number of Assignments',
          data: data,
          backgroundColor: 'rgb(173, 173, 232, 0.8)',
          borderColor: 'rgb(136, 136, 186)',
          borderWidth: 3
        }]
      },
      options: {
        animation:{
          easing: 'easeInExpo',
          animateScale: true
        },
        layout:{
          padding: {
            top: 100, 
            right: 100, 
            bottom: 100, // Adjust this value to add more padding towards the bottom
            left: 100
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            title: {
              fontSize: 26,
              display: true,
              text: 'Number of Assignments'
            }
          },
          x: {
            title: {
              
              display: true,
              text: 'Course Name',
              fontSize: 26
            }
          }
        }
      }
    });
  }, [homeworkData]);

  return (
    <div>
      <canvas id="barChart" width="400" height="200"></canvas>
    </div>
  );
}

// const ChartComponent = () => {
//   // Sample data (replace with your own data)
//   const labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May'];
//   const dataset = {
//     label: 'Grade Data',
//     data: [73, 79, 80, 93, 87, 85, 88],
//     borderColor: 'rgb(66, 66, 139)',
//   };

//   // Create a data object
//   const data = {
//     labels: labels,
//     datasets: [dataset],
//   };

//   const options = {
//     responsive: true,
//     layout: {
//       padding: {
//         top: 100, 
//         right: 100, 
//         bottom: 100,
//         left: 100
//       }
//     },
//     plugins: {
//       title: {
//         display: true,
//         text: 'Grade Tracking',
//         font: {
//           size: 20, 
//           weight: 'bold' // Font weight of the title
//         },
//         color: 'rgb(66, 66, 139)'
//       },
//       legend: {
//         display: false,
//       }
//     },

//   }
//   return (
//     <div>
//       <h2></h2>
//       <Line data={data} options = {options} className="chart"/>
//     </div>
//   );
// };

// export default ChartComponent;
  


export default ChartComponent;