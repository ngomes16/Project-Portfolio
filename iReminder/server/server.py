import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import random
import os
from dotenv import load_dotenv
from canvas import get_assignments

# once we got the DB setup, we 
mydb = mysql.connector.connect(
   host='34.70.157.253',
   port="3306",
   user="group59proj",
   password='aV7cj"O-KkYCcmu1',
   database="test2"
)
global global_notes
global_notes = ""
app = Flask(__name__)

CORS(app)

def data_parser(byte_string):
    # byte_string = b'email=blah&password=12345'
    regular_string = byte_string.decode('utf-8')

    # Step 2: Split string into key-value pairs
    pairs = regular_string.split('&')

    # Step 3: Split each pair into key and value
    parsed_data = {}
    for pair in pairs:
        key, value = pair.split('=')
        parsed_data[key] = value
    return parsed_data

#testing API
@app.route('/prof')
def my_profile():
    return {"name": "Nagato"}

@app.route('/schedule')
def schedule():
    return {"Monday": "9AM - 5PM", "Tuesday": "9AM - 5PM", "Wednesday": "9AM - 5PM", "Thursday": "9AM - 5PM", "Friday": "9AM - 5PM"}


# 0. Login
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    mycursor = mydb.cursor()
    check = """Select * FROM test2.users WHERE email = %s"""
    # print(request.get)
    mycursor.execute(check, (data['email'],))
    checkres = mycursor.fetchall()
    if (len(checkres) == 0):
        return "User Not Exists", 200

    check = """Select email,password FROM test2.users WHERE email = %s""" 
    mycursor.execute(check, (data['email'],))
    checkres = mycursor.fetchall()
    print(checkres)
    if (str(checkres[0][1]) != str(data['password'])):
        print(checkres[0][1], str(data['password']))
        return "Wrong Password", 200
    mydb.commit()
    mycursor.close()
    return "Success", 200


#1. Register new user: Insert new user into database
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    #print(data)
   # data = data_parser(data)
    # print(data['email'])
    # print(data['password'])
    mycursor = mydb.cursor()
    check = """Select email FROM test2.users WHERE email = %s"""
    mycursor.execute(check, (data['email'],))
    checkres = mycursor.fetchall()
    if (len(checkres) >= 1):
        return "User Exists", 200

    query1 = """
            INSERT INTO test2.users(email, password) VALUES (%s, %s)
            """

    mycursor.execute(query1, (data['email'], data['password']))
    mydb.commit()
    mycursor.close()
    return "Success", 200


#2. delete user
@app.route('/delete_user', methods=['POST'])
def delete_user():
    data = request.get_json()
    #print(data['email'])
    mycursor = mydb.cursor()
    query = """DELETE FROM test2.users WHERE email = %s"""
    mycursor.execute(query, (data['email'],))
    mydb.commit()
    mycursor.close()
    return "Success", 200

@app.route('/update_notes', methods=['POST'])
def update_notes():
    global global_notes
    data = request.get_json()
    print(data)
    email = data.get('email')
    notes = data.get('note')
    global_notes = notes
    
    if not email or not notes:
        return jsonify({'error': 'Missing email or note'}), 400
    
    mycursor = mydb.cursor()
    query = """UPDATE test2.users SET user_notes = %s WHERE email = %s"""
    
    try:
        mycursor.execute(query, (notes, email))
        mydb.commit()
        global_notes = notes
        return jsonify({'success': 'Notes updated successfully'}), 200
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return jsonify({'error': 'Failed to update notes'}), 500
    finally:
        mycursor.close()

#3. given token, get a assignment dict, each element represents a assignment 
@app.route('/canvas/<token>', methods=['POST'])
def get_assignment_from_token(token = None):
   if (token == None):
      return 'Unauthorized - No token provided', 401
   return get_assignments(str(token)), 200

# #4. notes
# @app.route('/post_notes', methods=['POST'])
# def put_notes():
#     data = request.get_json()
#     #print(data)
#     mycursor = mydb.cursor()
#     query = """UPDATE test2.users
#             SET user_notes = CONCAT(note, %s)
#             WHERE email = %s"""
#     mycursor.execute(query, (data['notes'],data['email'],))
#     mydb.commit()
#     mycursor.close()
#     return "Success", 200

@app.route('/get_notes', methods=['POST'])
def get_notes():
    global global_notes
    return [global_notes], 200
    data = request.get_json()
    email = data.get('email')
    print(email)
    mycursor = mydb.cursor()
    query = """SELECT user_notes FROM test2.users WHERE email = %s"""
    mycursor.execute(query, (email,))
    res = mycursor.fetchall()
    print(res)
    mydb.commit()
    mycursor.close()
    return res, 200


if __name__ == "__main__":
    # call_sp()
    app.run(host="127.0.0.1", port="5000", debug=False)
