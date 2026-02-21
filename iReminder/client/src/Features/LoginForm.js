// LoginForm.js
import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginMessage, setLoginMessage] = useState(()=> {
    const userLogin = localStorage.getItem('userLogin');
    return userLogin ? "Already Login" : '';
  }); 

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    if (loginMessage) {
      return;
    }
    e.preventDefault();

    try {
      // Format the data as JSON for the Python backend
      const data = { email, password }; 

      const response = await axios.post('http://127.0.0.1:5000/login', data, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      setLoginMessage(response.data);
      if (response.status === 200) {
        // Handle successful login (e.g., store token in localStorage, redirect)
        localStorage.setItem('userLogin', JSON.stringify({email:email, password:password}));
        navigate('/tab1');
        
      } 
    } catch (error) {
      console.error('Login Error:', error);
      setLoginMessage('Login failed. Please check your credentials.');
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
      <button type="submit">Login</button>
      {loginMessage && <p>{loginMessage}</p>}
    </form>
  );
}

export default LoginForm;
