import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function DeleteForm() {
  const [email, setEmail] = useState('');
  const [deleteMessage, setDeleteMessage] = useState('');

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const data = { email }; // Send the email

      const response = await axios.delete('http://127.0.0.1:5000/delete', {
        headers: {
          'Content-Type': 'application/json'
        },
        data: data  // Send the data in the body of the DELETE request
      });

      setDeleteMessage(response.data);
      if (response.status === 200) {
        // Handle successful deletion (e.g., redirect)
        console.log("User deleted, implement your logic here");
      } 
    } catch (error) {
      console.error('Deletion Error:', error);
      setDeleteMessage('Failed to delete user. Please try again.');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input 
        type="email" 
        placeholder="Email" 
        value={email} 
        onChange={(e) => setEmail(e.target.value)} 
        required 
        style={{ display: 'block', margin: '10px 0' }} 
      /> 
      <button type="submit">Delete User</button>
      {deleteMessage && <p>{deleteMessage}</p>}
    </form>
  );
}

export default DeleteForm;