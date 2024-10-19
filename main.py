from flask import Flask, request, jsonify, render_template, redirect, url_for
from pymongo import MongoClient
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime
import threading
import time
import pyttsx3
import os

app = Flask(__name__)
CORS(app)

# MongoDB configuration
app.config["MONGO_URI"] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/reminders_db')  # Update with your MongoDB URI
mongo = PyMongo(app)
client = MongoClient(os.environ.get('MONGO_URI', 'mongodb://localhost:27017/'))
db = client['your_database_name']  # Replace with your actual database name

# Route to serve the main page
@app.route('/')
def doctor():
    return render_template('index.html')

# Route for login page
@app.route('/login')
def login():
    return render_template('login.html')

# Route for user registration
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    # Check if the user already exists
    existing_user = db.users.find_one({"username": username})
    if existing_user:
        return jsonify({'message': 'User already exists!'}), 400

    # Insert new user into MongoDB
    db.users.insert_one({"username": username, "password": password})
    return jsonify({'message': 'Registration successful!'})

# Route for user login
@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form.get('username')
    password = request.form.get('password')

    # Validate user credentials
    user = db.users.find_one({"username": username, "password": password})
    if user:
        return jsonify({'message': 'Login successful!'})
    else:
        return jsonify({'message': 'Invalid username or password!'}), 401

# Route to add a new reminder
@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid input"}), 400

        new_reminder = {
            "patient_id": data['patient_id'],
            "medicine": data['medicine'],
            "time": data['time'],
            "completed": False
        }
        mongo.db.reminders.insert_one(new_reminder)
        return jsonify({"message": "Reminder added successfully"}), 201
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# Route to get all unique patient IDs
@app.route('/get_patient_ids', methods=['GET'])
def get_patient_ids():
    try:
        # Retrieve unique patient IDs from reminders collection
        patient_ids = mongo.db.reminders.distinct("patient_id")
        return jsonify({"patient_ids": patient_ids})
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# Route to get all reminders for a specific patient
@app.route('/get_reminders/<patient_id>', methods=['GET'])
def get_patient_reminders(patient_id):
    try:
        reminders = mongo.db.reminders.find({"patient_id": patient_id})
        return jsonify([
            {"id": str(r['_id']), "medicine": r['medicine'], "time": r['time'], "completed": r['completed']}
            for r in reminders
        ])
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# Background process to check reminders and trigger notifications
def check_reminders():
    while True:
        current_time = datetime.now().strftime("%H:%M")
        print(f"Current time: {current_time}")  # Debugging line
        reminders = mongo.db.reminders.find({"time": current_time, "completed": False})
        print(f"Checking reminders...")  # Debugging line
        for reminder in reminders:
            print(f"Reminder found: {reminder['medicine']} at {reminder['time']}")  # Debugging line
            play_sound_reminder(reminder['medicine'])
            mongo.db.reminders.update_one({"_id": reminder['_id']}, {"$set": {"completed": True}})
        time.sleep(10)  # Check every 10 seconds

# Function to play sound and speak the reminder
def play_sound_reminder(medicine):
    try:
        print(f"Playing sound and speaking reminder for: {medicine}")
        
        # Text-to-speech for the medicine name
        engine = pyttsx3.init()
        engine.say(f"It's time to take your medicine: {medicine}")
        engine.runAndWait()
    except Exception as e:
        print(f"Error playing sound: {e}")

# 404 error handler
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Page not found'}), 404

# Start the Flask app and the reminder checking thread
if __name__ == '__main__':
    reminder_thread = threading.Thread(target=check_reminders, daemon=True)
    reminder_thread.start()
    app.run(debug=True)
