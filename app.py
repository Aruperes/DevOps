import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import pymongo
from datetime import datetime

app = Flask(__name__)

API_KEY = "AIzaSyAKoUgLWfPM_8nYEtpM5RDtzo7DSRzhhg8" 
# ---------------
MONGO_URI = "mongodb+srv://lionking:lionking123@revando.zqfyyjo.mongodb.net/?retryWrites=true&w=majority&appName=Revando"
# --- Konfigurasi Gemini ---
try:
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"Error konfigurasi Gemini: {e}")

model_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

system_instruction = (
    "Anda adalah 'Sahabat Gizi', asisten AI yang ramah dan informatif. "
    "Tugas Anda adalah memberikan informasi akurat dan saran praktis "
    "mengenai pencegahan stunting, gizi anak, dan kesehatan ibu. "
    "Jawablah pertanyaan hanya dalam konteks kesehatan dan gizi. "
    "Jika pertanyaan di luar topik (misal: politik, olahraga, hiburan), "
    "tolak dengan sopan dan kembalikan fokus ke topik stunting atau kesehatan."
    "Selalu pertimbangkan Data Pasien yang diberikan saat merumuskan jawaban."
)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash", # Diubah ke model yang valid
    generation_config=model_config,
    system_instruction=system_instruction
)

# Buat sesi chat (agar bisa mengingat konteks)
chat_session = model.start_chat(history=[])

# --- Konfigurasi MongoDB ---
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.sahabat_gizi_db 
    patients_collection = db.patients 
    # Uji koneksi
    client.server_info() 
    print("Koneksi MongoDB berhasil.")
except Exception as e:
    print(f"Error koneksi MongoDB: {e}")
    patients_collection = None

# --- Routes ---
@app.route('/')
def index():
    """Menampilkan halaman utama (index.html)."""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint API untuk menerima pesan DAN KONTEKS dari user."""
    try:
        data = request.json
        user_message = data.get('message')
        user_context = data.get('context', '') # Ambil data konteks

        if not user_message:
            return jsonify({'error': 'Pesan tidak boleh kosong'}), 400

        if user_context and user_context.strip():
            prompt = f"Berdasarkan Data Pasien berikut:\n{user_context}\n\nJawab pertanyaan ini: {user_message}"
        else:
            prompt = user_message
            
        response = chat_session.send_message(prompt)
        
        return jsonify({'response': response.text})

    except Exception as e:
        print(f"Error saat memproses chat: {e}")
        return jsonify({'error': 'Terjadi kesalahan pada server'}), 500

@app.route('/api/save_data', methods=['POST'])
def save_data():
    """Endpoint API untuk menyimpan data pasien ke MongoDB."""
    
    # --- 2. INI ADALAH PERBAIKANNYA ---
    if patients_collection is None:
    # ------------------------------------
        return jsonify({'error': 'Koneksi database gagal'}), 500
        
    try:
        data = request.json
        
        mother_data = data.get('mother_data')
        child_data = data.get('child_data')
        
        patient_record = {
            "mother_data": mother_data,
            "child_data": child_data,
            # --- 3. PERBAIKAN PADA TIMESTAMP ---
            "timestamp": datetime.utcnow() 
            # ------------------------------------
        }
        
        result = patients_collection.insert_one(patient_record)
        
        print(f"Data tersimpan dengan ID: {result.inserted_id}")
        
        return jsonify({'success': True, 'saved_id': str(result.inserted_id)}), 201

    except Exception as e:
        print(f"Error saat menyimpan data: {e}")
        return jsonify({'error': 'Gagal menyimpan data ke server'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)