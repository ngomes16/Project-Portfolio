import React from 'react';

import "./tab2.css";
import Table from "../Features/GradeTable";

import ChartComponent from '../Features/GradeChart';

import axios from 'axios';

const Tab2 = () => {

  const [noteData, setNoteData] = React.useState(null);
  React.useEffect(() => {
    const response = getNotes();
  }, []);

  const getNotes = async () => {
    try {
      const userLogin = localStorage.getItem('userLogin');
      const userLoginObj = JSON.parse(userLogin);
      const data = {email: userLoginObj.email};
      // console.log(data);

      const response = await axios.post('http://127.0.0.1:5000/get_notes', data, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if(response.status === 200){
        // console.log(response.data)
        setNoteData(response.data);
        
      }
      console.log(noteData);
    //  return [response.data];
  } catch (error) {
    console.error('Login Error:', error);
  }
};
  const handleSubmit = async (e) => {

    // e.preventDefault();

    try {
      // Format the data as JSON for the Python backend
      const userLogin = localStorage.getItem('userLogin');
      const data = {email: userLogin['email'], notes: e.target.elements.notes.value};

      const response = await axios.post('http://127.0.0.1:5000/post_notes', data, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.status === 200) {
        
        alert("Note saved successfully");
      }
    } catch (error) {
      console.error('Login Error:', error);
    }
  };
  return (
    <div>
    <div className='tab-content'>
      <h2>Notepad</h2>
      {/* <p>This is where we will display grades</p> */}
  
    </div>
    {noteData && noteData.map((item, idx) =>{
      const convertedString = item;
      return <div className="notecard" key={idx}>{convertedString}</div>
    })}
    <textarea name="notes" style={{minWidth: "200px", maxWidth: "800px", width: "100%", minHeight: "200px"}} form='note-form'></textarea>
    <form id="note-form" onSubmit={handleSubmit}>
      <input className="reg-log" type="submit" value="Save Note"/>
    </form>
    </div>
    
  );
};

export default Tab2;