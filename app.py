from flask import Flask, request, render_template, redirect
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

mongo_uri = "mongodb+srv://lionking:lionking123@revando.zqfyyjo.mongodb.net/?retryWrites=true&w=majority&appName=Revando"

client = MongoClient(mongo_uri)
db = client['lionking']
collection = db['attendance']

@app.route('/')
def index():
    attendances = list(collection.find().sort('timestamp', -1))
    return render_template('index.html', attendances=attendances)

@app.route('/add', methods=['POST'])
def add_attendance():
    name = request.form['name']
    status = request.form['status']
    notes = request.form['notes']
    timestamp = datetime.now()
    
    collection.insert_one({
        'name': name,
        'status': status,
        'notes': notes,
        'timestamp': timestamp,
        'date': timestamp.strftime('%Y-%m-%d')
    })
    return redirect('/')

@app.route('/delete/<id>')
def delete_attendance(id):
    from bson import ObjectId
    collection.delete_one({'_id': ObjectId(id)})
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)