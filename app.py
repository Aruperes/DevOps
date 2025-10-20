from flask import Flask, request, render_template, redirect
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load file .env
load_dotenv()

app = Flask(__name__)

# Ambil URL dari environment variable
mongo_uri = os.getenv("MONGO_URI")

# Koneksi ke MongoDB Atlas
client = MongoClient(mongo_uri)
db = client['lionking']
collection = db['lion']

@app.route('/')
def index():
    users = list(collection.find())
    return render_template('index.html', users=users)

@app.route('/add', methods=['POST'])
def add_user():
    name = request.form['name']
    collection.insert_one({'name': name})
    return redirect('/')

@app.route('/delete/<id>')
def delete_user(id):
    from bson import ObjectId
    collection.delete_one({'_id': ObjectId(id)})
    return redirect('/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
