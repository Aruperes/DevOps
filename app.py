import os
from flask import (
    Flask, render_template, request, jsonify, 
    redirect, url_for, session, flash
)
import google.generativeai as genai
from pymongo import MongoClient
from bson import ObjectId
from flask_bcrypt import Bcrypt
from datetime import datetime

app = Flask(__name__)

# --- KUNCI RAHASIA ---
# WAJIB diisi untuk mengamankan session (login)
# Ganti dengan string acak yang panjang
app.config['SECRET_KEY'] = 'ganti-ini-dengan-string-rahasia-anda'

# --- KONEKSI DATABASE ---
# URI MongoDB Anda
mongo_uri = "mongodb+srv://lionking:lionking123@revando.zqfyyjo.mongodb.net/?retryWrites=true&w=majority&appName=Revando"
client = MongoClient(mongo_uri)
db = client['lionking']  # Database Anda
# Kita buat DUA collection: 'users' untuk akun, 'patients' untuk data pasien
users_collection = db['users']
patients_collection = db['patients']

# --- KONFIGURASI KEAMANAN ---
bcrypt = Bcrypt(app)

# --- KONFIGURASI GEMINI API ---
# Masukkan API Key Gemini Anda
API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"
try:
    if not API_KEY or API_KEY == "MASUKKAN_API_KEY_ANDA_DI_SINI":
        print("PERINGATAN: API_KEY Gemini belum diisi.")
    genai.configure(api_key=API_KEY)
    
    model_config = {"temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048}
    system_instruction = (
        "Anda adalah 'Sahabat Gizi', asisten AI yang ramah dan informatif. "
        "Tugas Anda adalah memberikan informasi akurat dan saran praktis "
        "mengenai pencegahan stunting, gizi anak, dan kesehatan ibu. "
        "Jawablah pertanyaan hanya dalam konteks kesehatan dan gizi. "
        "Jika pertanyaan di luar topik, tolak dengan sopan."
    )
    model = genai.GenerativeModel(
        model_name="gemini-1.0-pro",
        generation_config=model_config,
        system_instruction=system_instruction
    )
    chat_session = model.start_chat(history=[])
except Exception as e:
    print(f"Error konfigurasi Gemini: {e}")
    chat_session = None # Nonaktifkan chat jika error

# ==================================
# HALAMAN UTAMA & CHATBOT
# ==================================

@app.route('/')
def index():
    """Menampilkan halaman utama (info stunting & chatbot)."""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint API untuk chatbot Gemini."""
    if not chat_session:
        return jsonify({'error': 'Layanan chat tidak tersedia saat ini.'}), 500
    try:
        data = request.json
        user_message = data.get('message')
        if not user_message:
            return jsonify({'error': 'Pesan tidak boleh kosong'}), 400
        
        response = chat_session.send_message(user_message)
        return jsonify({'response': response.text})
    except Exception as e:
        print(f"Error saat memproses chat: {e}")
        return jsonify({'error': 'Terjadi kesalahan pada server'}), 500

# ==================================
# SISTEM AKUN PENGGUNA (BARU)
# ==================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Halaman registrasi akun baru."""
    if 'user_id' in session:
        return redirect(url_for('dashboard')) # Jika sudah login, lempar ke dashboard

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cek apakah username sudah ada
        existing_user = users_collection.find_one({'username': username})
        if existing_user:
            flash('Username sudah digunakan. Silakan pilih nama lain.', 'danger')
            return redirect(url_for('register'))

        # Hash password sebelum disimpan
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        # Simpan user baru
        users_collection.insert_one({
            'username': username,
            'password': hashed_password,
            'created_at': datetime.now()
        })
        
        flash('Registrasi berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman login."""
    if 'user_id' in session:
        return redirect(url_for('dashboard')) # Jika sudah login, lempar ke dashboard

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})
        
        # Cek user dan password
        if user and bcrypt.check_password_hash(user['password'], password):
            # Sukses login, simpan info user di session
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            flash('Login berhasil!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login gagal. Cek kembali username dan password Anda.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Keluar dari akun."""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Anda telah berhasil logout.', 'info')
    return redirect(url_for('index'))

# ==================================
# DASHBOARD & DATA PASIEN (BARU)
# ==================================

@app.route('/dashboard')
def dashboard():
    """Halaman pribadi pengguna untuk mengelola data pasien."""
    if 'user_id' not in session:
        flash('Anda harus login untuk mengakses halaman ini.', 'warning')
        return redirect(url_for('login'))

    # Ambil data pasien HANYA milik user yang login
    user_id = session['user_id']
    patient_list = list(patients_collection.find({
        'user_id': ObjectId(user_id)
    }).sort('created_at', -1))
    
    return render_template('dashboard.html', patients=patient_list)

@app.route('/add_patient', methods=['POST'])
def add_patient():
    """Proses penambahan data pasien."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user_id = ObjectId(session['user_id'])
        name = request.form['name']
        dob_str = request.form['dob'] # Tanggal Lahir (string)
        weight = float(request.form['weight']) # Berat (kg)
        height = float(request.form['height']) # Tinggi (cm)
        notes = request.form['notes']
        
        # Konversi string tanggal ke object datetime
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        
        patients_collection.insert_one({
            'user_id': user_id,
            'name': name,
            'dob': dob,
            'weight': weight,
            'height': height,
            'notes': notes,
            'created_at': datetime.now() # Tanggal data ini dimasukkan
        })
        
        flash('Data pasien berhasil ditambahkan.', 'success')
    except Exception as e:
        print(f"Error tambah pasien: {e}")
        flash('Gagal menambahkan data. Pastikan semua field terisi dengan benar.', 'danger')
        
    return redirect(url_for('dashboard'))

@app.route('/delete_patient/<id>')
def delete_patient(id):
    """Menghapus data pasien."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        patient_id = ObjectId(id)
        user_id = ObjectId(session['user_id'])
        
        # Hapus data HANYA jika ID pasien dan ID user cocok
        # Ini mencegah user menghapus data milik user lain
        result = patients_collection.delete_one({
            '_id': patient_id,
            'user_id': user_id 
        })
        
        if result.deleted_count == 1:
            flash('Data pasien berhasil dihapus.', 'success')
        else:
            flash('Data tidak ditemukan atau Anda tidak punya hak akses.', 'danger')
            
    except Exception as e:
        print(f"Error hapus pasien: {e}")
        flash('Gagal menghapus data.', 'danger')
        
    return redirect(url_for('dashboard'))

# ==================================
# RUN APLIKASI
# ==================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)