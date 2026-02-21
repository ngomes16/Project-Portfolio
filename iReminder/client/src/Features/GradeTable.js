import React from 'react';
import "./GradeTable.css";
const grades =[
    { name: "CS 222", grade: "100"},
    { name: "Class 2", grade: "100"},
    { name: "Class 3", grade: "100"},
    { name: "Class 4", grade: "100"}
]

const Table = () => {
    return(
        <div>
        <table>
            <tr>
                <th>Name:</th>
                <th>Grade: </th>
            </tr>
            {/* Referencing https://www.geeksforgeeks.org/how-to-create-a-table-in-reactjs/ */}
            {grades.map((val,key) => {
                   return (
                    <tr key={key}>
                        <td>{val.name}</td>
                        <td>{val.grade}</td>
                    </tr>
                )
            })}
        </table>
        </div>
    )

}

export default Table;