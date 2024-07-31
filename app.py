from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import qrcode
from datetime import datetime
import os
import pytz
from authlib.integrations.flask_client import OAuth
import logging
import traceback
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

DATABASE = 'database.db'
LAGOS_TIMEZONE = pytz.timezone('Africa/Lagos')

# OAuth Configuration
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_uri='https://qr-sign-in-system.onrender.com/oauth2callback',
    client_kwargs={
        'scope': 'openid profile email',
        'token_endpoint_auth_method': 'client_secret_basic'
    },
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
)

EXPECTED_ISSUER = 'https://accounts.google.com'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Ensure the email column is added to the sign_ins table
def add_email_column():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('ALTER TABLE sign_ins ADD COLUMN email TEXT')
    conn.commit()
    conn.close()

try:
    add_email_column()
except sqlite3.OperationalError:
    pass  # Ignore if the column already exists

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        employees = conn.execute('SELECT * FROM employees').fetchall()
        conn.close()
    except Exception as e:
        flash(f'Error occurred while fetching employees: {str(e)}', 'error')
        return redirect(url_for('index'))
    return render_template('index.html', employees=employees)

@app.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if 'user' not in session:
        flash('You must log in first.')
        return redirect(url_for('login'))

    user_email = session['user']
    
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
        now = datetime.now(LAGOS_TIMEZONE)
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M:%S")

        conn = get_db_connection()

        # Insert sign-in record with email
        conn.execute('INSERT INTO sign_ins (name, email, date, time) VALUES (?, ?, ?, ?)', (name, user_email, date, time))
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
        # Construct URL for the login page
        login_url = url_for('login', _external=True)

        if request.method == 'POST':
            # Generate QR code
            img = qrcode.make(login_url)
            qr_path = os.path.join('static', 'common_sign_in.png')
            img.save(qr_path)
            flash(f'Common QR code generated and saved to {qr_path}!')
        else:
            flash('Use POST to generate the QR code.')
        
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/sign_in_form')
def sign_in_form():
    if 'user' not in session:
        flash('You must log in first.')
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        employees = conn.execute('SELECT name FROM employees').fetchall()
        conn.close()
    except Exception as e:
        flash(f'Error occurred while fetching employees: {str(e)}', 'error')
        return redirect(url_for('index'))
    
    user_email = session['user']
    return render_template('sign_in_form.html', employees=employees, user_email=user_email)

@app.route('/sign_in_data')
def sign_in_data():
    try:
        conn = get_db_connection()
        sign_ins = conn.execute('SELECT * FROM sign_ins').fetchall()
        conn.close()
    except Exception as e:
        flash(f'Error occurred while fetching sign-in data: {str(e)}', 'error')
        return redirect(url_for('index'))
    return render_template('sign_in_data.html', sign_ins=sign_ins)

@app.route('/add_employee', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        try:
            name = request.form['name']
            # Add the new employee to the database
            conn = get_db_connection()
            conn.execute('INSERT INTO employees (name) VALUES (?)', (name,))
            conn.commit()
            conn.close()
            flash(f'Employee {name} added successfully!')
        except Exception as e:
            flash(f'Error occurred: {str(e)}', 'error')
        return redirect(url_for('index'))

    return render_template('add_employee.html')

@app.route('/delete_employee', methods=['POST'])
def delete_employee():
    try:
        name = request.form['name']
        conn = get_db_connection()
        conn.execute('DELETE FROM employees WHERE name = ?', (name,))
        conn.commit()
        conn.close()
        flash(f'Employee {name} deleted successfully!')
    except Exception as e:
        flash(f'Error occurred: {str(e)}', 'error')
    return redirect(url_for('index'))

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You were logged out')
    return redirect(url_for('index'))

@app.route('/oauth2callback')
def authorize(request):
    try:
        token = google.authorize_access_token(request)
        if not token:
            flash('Access denied')
            return redirect(url_for('index'))

        app.logger.info("Token received: %s", token)
        id_token = token.get('id_token')
        if id_token:
            decoded_token = jwt.decode(id_token, options={"verify_signature": False})
            app.logger.info("Decoded ID Token: %s", decoded_token)

            if decoded_token.get('iss') != EXPECTED_ISSUER:
                raise ValueError(f"Invalid issuer. Expected {EXPECTED_ISSUER}, but got {decoded_token.get('iss')}")

            state_data = google.get_state_data()
            userinfo = google.parse_id_token(
                token,
                nonce=state_data['nonce'],
                claims_options={'iss': {'values': [EXPECTED_ISSUER]}}
            )
            app.logger.info("User Info: %s", userinfo)

        resp = google.get('userinfo')
        user_info = resp.json()
        session['user'] = user_info['email']
        flash('You were successfully logged in as {}'.format(session['user']))
    except Exception as e:
        app.logger.error("Error during OAuth callback: %s", e)
        app.logger.error(traceback.format_exc())
        flash(f'An error occurred during the login process: {str(e)}')
        return redirect(url_for('index'))

    return redirect(url_for('sign_in_form'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
