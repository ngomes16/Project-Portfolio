import React from 'react';
import { Navigate } from 'react-router-dom';

function ProtectedRoute({ children, isLoggedIn }) {
  if (!isLoggedIn) {
    return <Navigate to="/login" replace />; // Redirect to login if not logged in 
  }

  return children; 
}

export default ProtectedRoute;