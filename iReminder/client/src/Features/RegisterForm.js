// RegisterForm.js
import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function RegisterForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [registrationMessage, setRegistrationMessage] = useState('');

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      // Format the data as JSON for the Python backend
      const data = { email: email, password:password }; 

      const response = await axios.post('http://127.0.0.1:5000/register', data, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      setRegistrationMessage(response.data);
      if (response.status === 200) {
        
        navigate('/tab1'); 
        alert("Registration successful, go back to homepage to login")
      }
    } catch (error) {
      console.error('Registration Error:', error);
      setRegistrationMessage('Registration failed. Please try again.');
    }
  };

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <input 
        type="email" 
        placeholder="Email" 
        value={email} 
        onChange={(e) => setEmail(e.target.value)} 
        required 
        style={{ display: 'block', margin: '10px 0' }} 
      /> 
      <input 
        type="password" 
        placeholder="Password" 
        value={password} 
        onChange={(e) => setPassword(e.target.value)} 
        required 
        style={{ display: 'block', margin: '10px 0' }} 
      />
      <button type="submit">Register</button>
      {registrationMessage && <p>{registrationMessage}</p>}
    </form>
  );
}

export default RegisterForm;

// const res = await axios.post(`http://127.0.0.1:5000/login`,{
//                 email: loginInfo.account,
//                 password: loginInfo.password
//             })