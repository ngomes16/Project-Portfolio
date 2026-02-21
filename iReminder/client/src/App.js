// App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import axios from 'axios';
import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import './App.css'; 
import Header from './Header';
import Tab1 from './Tabs/tab1';
import Tab2 from './Tabs/tab2';
import Tab3 from './Tabs/tab3';
import Tab4 from './Tabs/tab4';
import Tab5 from './Tabs/tab5';
import Tab6 from './Tabs/tab6';
import Footer from './Footer';
import LoginForm from './Features/LoginForm'; // Import LoginForm component
import RegisterForm from './Features/RegisterForm'; // Import RegisterForm component
// import DeleteForm from './Features/DeleteForm';

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  return (
    <Router>
      <div className="App">
        <Header />
        <Routes>
          <Route path="/" element={<HomePage />} /> {/* Set home page as the default route */}
          <Route path="/tab1" element={<Tab1 />} />
          {/* <Route path="/tab2" element={<Tab2 />} /> */}
          <Route path="/tab3" element={<Tab3 />} />
          <Route path="/tab4" element={<Tab4 />} />
          {/* <Route path="/tab5" element={<Tab5 />} /> */}
          <Route path="/tab6" element={<Tab6 />} />
          <Route path="/login" element={<LoginForm />} />
          <Route path="/register" element={<RegisterForm />} />
          {/* <Route path="/delete_user" element={<DeleteForm />} /> */}
          {/* Add more routes for additional tabs if needed */}
        </Routes>
        <Footer />
      </div>
    </Router>
  );
}



// Home page component
function HomePage() {
  const [token, setToken] = useState(''); // Add state for token
  const hasUserLogin = localStorage.getItem('userLogin');
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      
      const response = await axios.post(`http://127.0.0.1:5000/canvas/${token}`, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      if(response.status === 200){
        localStorage.setItem('userData', JSON.stringify(response.data));
        Navigate('/');
      }
    } catch (error) {
      console.error('Registration Error:', error);
    
    }
  };
  return (
    <div>
      <h1 className='welcome-legend'>Welcome to iReminder</h1>
      {!hasUserLogin ? <div>
        <Link to="/login">
          <button className='reg-log'>Login</button>
        </Link>
        <Link to="/register">
          <button className='reg-log'>Register</button>
        </Link>
      </div>: <><button className='reg-log' onClick={()=> {
        localStorage.removeItem('userLogin');
        window.location.reload();
      }}>Logout</button> 
      <form style={{ display: 'flex', justifyContent: 'center'}} onSubmit={handleSubmit}>
        <input type='text'
        placeholder="Put token here" 
        value={token} 
        onChange={(e) => setToken(e.target.value)}
        style={{ display: 'block', margin: '10px 0', width: '400px', lineHeight: '1.5rem', fontSize: '1.25 rem',}} />
        <button type='submit' className='reg-log'>Submit</button>
        
      </form>
      </>}
      {/* <Link to="/delete_user">
        <button>Delete</button>
      </Link> */}
    </div>
  );
}

export default App;

//<textarea placeholder="Enter your token here" value={token} onChange={(e) => setToken(e.target.value)}></textarea>
// function HomePage({ isLoggedIn }) {
//   return (
//     <div>
//       <h1>Welcome to Group 59's app</h1>
//       {isLoggedIn ? (
//         <div>
//           <h2>Hello, User!</h2>
//           {/* Add additional content or links for logged-in users here */}
//         </div>
//       ) : (
//         <div>
//           <Link to="/login">
//             <button>Login</button>
//           </Link>
//           <Link to="/register">
//             <button>Register</button>
//           </Link>
//           {/* <Link to="/delete_user">
//             <button>Delete</button>
//           </Link> */}
//         </div>
//       )}
//     </div>
//   );