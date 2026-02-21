import React from 'react';
import "./AssignmentTable.css";
import axios from 'axios';
import assignments from '../Tabs/assignments';



const Table = () => {
    const [homeworkData, setHomeworkData] = React.useState(()=>{
        let localData = localStorage.getItem('userData');
        if(!localData){
            return [];
        }
        localData = assignments.concat(JSON.parse(localData));
        return localData.length ? localData : [];
    });
    
   
        
    return(
        <div>
        {homeworkData.length ? <table>
            <tr>
                <th>Class:</th>
                <th>Assignment Name:</th>
                <th>Due Date:</th>
                <th>Due Time:</th>
            </tr>
            {/* Referencing https://www.geeksforgeeks.org/how-to-create-a-table-in-reactjs/ */}
            {homeworkData.map((val,key) => {
                   return (
                    <tr key={key}>
                        <td>{val.CourseName}</td>
                        <td>{val.AssignmentName}</td>
                        <td>{val.DueDate}</td>
                        <td>{val.DueTime}</td>
                    </tr>
                )
            })}
        </table> : <div> No Data </div>}
        </div>
    )

}

export default Table;