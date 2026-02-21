// tab4.js
import React from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import "./tab4.css";
import assignments from './assignments';

function MyCalendar() {
  
  const [homeworkData, setHomeworkData] = React.useState(()=>{
    let localData = localStorage.getItem('userData');
    if(!localData) return [];
    localData = assignments.concat(JSON.parse(localData));
    return localData.length ? localData : [];
});
  return (
    <FullCalendar
      plugins={[ dayGridPlugin ]}
      initialView="dayGridMonth"

      events={
        homeworkData.map((val) => {
          let temp = val.DueDate.split("/");
          return (
            { title: val.AssignmentName, date: `${temp[2]}-${temp[0]}-${temp[1]}` }
          )
        })  
        // { title: '', date: '2024-03-26' },
        // { title: 'Event 2', date: '2024-03-30' }
        // Add more events as needed
      }
    />
  );
}

export { MyCalendar }; 

const Tab4 = () => {
  return (
    <div className='tab-content'>
      <h2>Calendar</h2>
      <p>Keep track of assignments</p>
      <MyCalendar />
    </div>
  );
};

export default Tab4; 