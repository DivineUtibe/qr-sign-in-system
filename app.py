from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import qrcode
from datetime import datetime
import socket

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATABASE = 'database.db'
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    conn = get_db_connection()
    employees = conn.execute('SELECT * FROM employees').fetchall()
    conn.close()
    print(f"Fetched employees: {employees}")  # Debugging print statement
    return render_template('index.html', employees=employees)

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        try:
            name = request.form['name']
            print(f"POST request received with name: {name}")  # Debugging print statement
        except Exception as e:
            flash(f'Error occurred: {str(e)}', 'error')
            print(f"Error occurred during sign-in: {str(e)}")  # Debugging print statement
            return redirect(url_for('index'))

    elif request.method == 'GET':
        try:
            name = request.args.get('name')
            print(f"GET request received with name: {name}")  # Debugging print statement
        except Exception as e:
            flash(f'Error occurred: {str(e)}', 'error')
            print(f"Error occurred during sign-in: {str(e)}")  # Debugging print statement
            return redirect(url_for('index'))

    try:
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        conn = get_db_connection()

        # Insert sign-in record
        conn.execute('INSERT INTO sign_ins (name, date, time) VALUES (?, ?, ?)', (name, date, time))
        conn.commit()
        print(f"Sign-in record added for {name} at {date} {time}")  # Debugging print statement

        # Update time_logged for the employee
        conn.execute('UPDATE employees SET time_logged = ? WHERE name = ?', (f'{date} {time}', name))
        conn.commit()
        print(f"Time logged updated for {name} to {date} {time}")  # Debugging print statement

        conn.close()

        return render_template('sign_in_success.html')
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
        print(f"Error occurred during sign-in: {str(e)}")  # Debugging print statement
        return redirect(url_for('index'))

@app.route('/generate_qr', methods=['GET', 'POST'])
def generate_qr():
    try:
        # Construct URL for the common sign-in page
        sign_in_url = f"http://192.168.24.33:5000/sign_in_form"
        
        if request.method == 'POST':
            # Generate QR code when POST request is received
            img = qrcode.make(sign_in_url)
            img.save(f'static/common_sign_in.png')
            print(f"Common QR code saved in static/common_sign_in.png")  # Debugging print statement
            flash('Common QR code generated!')
        else:
            # Provide a simple response or message for GET requests
            print(f"GET request received. No QR code generated. URL: {sign_in_url}")  # Debugging print statement
            flash('Use POST to generate the QR code.')
        
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
        print(f"Error occurred during QR code generation: {str(e)}")  # Debugging print statement

    return redirect(url_for('index'))

@app.route('/sign_in_form')
def sign_in_form():
    print("Sign-in form route accessed")  # Debugging print statement
    conn = get_db_connection()
    employees = conn.execute('SELECT name FROM employees').fetchall()
    conn.close()
    return render_template('sign_in_form.html', employees=employees)

@app.route('/sign_in_data')
def sign_in_data():
    print("Sign-in data route accessed")  # Debugging print statement
    conn = get_db_connection()
    sign_ins = conn.execute('SELECT * FROM sign_ins').fetchall()
    conn.close()
    return render_template('sign_in_data.html', sign_ins=sign_ins)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
