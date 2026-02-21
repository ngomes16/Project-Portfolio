import React, { useState } from 'react';
import axios from 'axios';
import "./tab6.css"; // Ensure this CSS file exists and is properly linked

const Tab6 = () => {
  const [note, setNote] = useState("");
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
        setNote(response.data);
        
      }
      
    //  return [response.data];
  } catch (error) {
    console.error('Login Error:', error);
  }
};

  const handleNoteChange = (event) => {
    setNote(event.target.value); // Update note state with input value
  };



  const handleNoteSubmit = () => {
    const userLogin = localStorage.getItem('userLogin');
    const userLoginObj = JSON.parse(userLogin);
    const data = {email: userLoginObj.email, note: note};
    
    axios.post("http://127.0.0.1:5000/update_notes", data)
      .then(function(response) {
        console.log(response.data);
        alert('Note saved successfully!');
      })
      .catch(function(error) {
        console.error('Error saving note:', error);
        alert('Failed to save note.');
      });
  };

  return (
    
    <div className='tab-content'>
      <h2> Notepad</h2>
      <textarea
        value={note}
        onChange={handleNoteChange}
        placeholder="Enter your notes here..."
        style={{ width: '100%', height: '150px', marginTop: '10px' }}
      />
      <button className='reg-log' onClick={handleNoteSubmit}>Save Note</button>
    </div>
  );
};

export default Tab6;
