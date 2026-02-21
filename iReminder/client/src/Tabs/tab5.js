// tab4.js
import React from 'react';
import axios from 'axios';
import "./tab5.css";
import { useState } from 'react';

const Tab5 = () => {
  // const name="r";
  const [content, setContent] = useState(""); // Define content state
    const handle = () => {
      axios.get("http://127.0.0.1:5000/prof")
      .then(function(response) {
        console.log(response);
        setContent(response.data.name);      })
      .catch(function(error) {
        console.error(error);
      });
    }
   
    return (
        <div>
          <p>Working on API req stuff</p>
        <button onClick={handle}></button>
        <p>{content}</p>
        </div>
      );
    };
export default Tab5; 