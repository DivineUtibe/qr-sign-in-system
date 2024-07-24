from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import qrcode
from datetime import datetime
import socket
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

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
    return render_template('index.html', employees=employees)

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if request.method == 'POST':
        try:
            name = request.form['name']
        except Exception as e:
            flash(f'Error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))

    elif request.method == 'GET':
        try:
            name = request.args.get('name')
        except Exception as e:
            flash(f'Error occurred: {str(e)}', 'error')
            return redirect(url_for('index'))

    try:
        now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        conn = get_db_connection()

        # Insert sign-in record
        conn.execute('INSERT INTO sign_ins (name, date, time) VALUES (?, ?, ?)', (name, date, time))
        conn.commit()

        # Update time_logged for the employee
        conn.execute('UPDATE employees SET time_logged = ? WHERE name = ?', (f'{date} {time}', name))
        conn.commit()

        conn.close()

        return render_template('sign_in_success.html')
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    try:
        # Construct URL for the common sign-in page
        sign_in_url = "https://qr-sign-in-system.onrender.com/sign_in_form"  # Updated for Render

        if request.method == 'POST':
            # Generate QR code
            img = qrcode.make(sign_in_url)
            img.save(f'static/common_sign_in.png')
            flash('Common QR code generated!')
        else:
            flash('Use POST to generate the QR code.')
        
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/sign_in_form')
def sign_in_form():
    conn = get_db_connection()
    employees = conn.execute('SELECT name FROM employees').fetchall()
    conn.close()
    return render_template('sign_in_form.html', employees=employees)

@app.route('/sign_in_data')
def sign_in_data():
    conn = get_db_connection()
    sign_ins = conn.execute('SELECT * FROM sign_ins').fetchall()
    conn.close()
    return render_template('sign_in_data.html', sign_ins=sign_ins)

if __name__ == '__main__':
    # Remove 'port=5000' if deploying on Render; Render assigns a dynamic port
    app.run(debug=True, host='0.0.0.0')
