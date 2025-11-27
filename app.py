import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import pymongo
from datetime import datetime
from bson.objectid import ObjectId
from dotenv import load_dotenv  

load_dotenv()

app = Flask(__name__)

API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

try:
    genai.configure(api_key=API_KEY)
    system_instruction = (
        "Anda adalah 'Sahabat Gizi'. Tugas: Analisis data stunting. "
        "Gunakan format Markdown (**Tebal**, - List, Tabel) agar rapi."
    )
    model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
    chat_session = model.start_chat(history=[])
except Exception as e:
    print(f"Error AI: {e}")

# Config DB
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client.sahabat_gizi_db 
    history_collection = db.checkup_history 
except Exception as e:
    print(f"Error Mongo: {e}")
    history_collection = None

def get_who_standards(age_month, gender):
    if gender == 'Laki-laki':
        std_weight = 3.3 + (age_month * 0.8) - (0.01 * age_month**2) 
        std_height = 50 + (age_month * 2.5) - (0.08 * age_month**2)
    else: 
        std_weight = 3.2 + (age_month * 0.75) - (0.01 * age_month**2)
        std_height = 49 + (age_month * 2.4) - (0.08 * age_month**2)
    
    if age_month > 12:
        years = age_month / 12.0
        if gender == 'Laki-laki':
            std_weight = 9.6 + (2 * (years - 1)) 
            std_height = 75 + (11 * (years - 1)) 
        else:
            std_weight = 8.9 + (2 * (years - 1))
            std_height = 74 + (11 * (years - 1))

    return std_weight, std_height

def calculate_nutritional_status(age, gender, weight, height):
    """
    Menentukan status gizi berdasarkan BB/U dan TB/U.
    """
    std_weight, std_height = get_who_standards(age, gender)
    
    status_list = []
    color = "success"
    main_status = "Gizi Baik & Normal"

    # 1. Cek STUNTING (Tinggi Badan menurut Umur)
    height_ratio = height / std_height
    if height_ratio < 0.85:
        status_list.append("Sangat Pendek (Severely Stunted)")
        color = "danger"
    elif height_ratio < 0.92:
        status_list.append("Pendek (Stunted)")
        color = "warning"
    
    # 2. Cek BERAT BADAN (Berat Badan menurut Umur)
    weight_ratio = weight / std_weight
    if weight_ratio < 0.7:
        status_list.append("Gizi Buruk (Severely Wasted)")
        color = "danger"
    elif weight_ratio < 0.85:
        status_list.append("Gizi Kurang (Wasted)")
        if color != "danger": color = "warning" 
    elif weight_ratio > 1.2:
        status_list.append("Risiko Obesitas")
        if color == "success": color = "warning"

    # Gabungkan status
    if not status_list:
        main_status = "Tumbuh Kembang Normal"
    else:
        main_status = " + ".join(status_list)

    return {"status": main_status, "color": color, "std_weight": round(std_weight,1), "std_height": round(std_height,1)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze_growth', methods=['POST'])
def analyze_growth():
    try:
        data = request.json
        child = data.get('child_data', {})
        if not child: return jsonify({'error': 'No data'}), 400

        # Ambil data aman
        nama = child.get('nama', 'Anak')
        usia = child.get('usia_bulan', 0)
        gender = child.get('gender', 'Laki-laki')
        berat = child.get('berat_kg', 0)
        panjang = child.get('panjang_cm', 0)

        # 1. Hitung Status (Logic Baru)
        analysis = calculate_nutritional_status(usia, gender, berat, panjang)
        
        # 2. AI Advice
        ai_text = "AI tidak merespon."
        try:
            prompt = (
                f"Anak: {nama}, {usia} bln, {gender}. BB: {berat}kg (Ideal: {analysis['std_weight']}kg), "
                f"TB: {panjang}cm (Ideal: {analysis['std_height']}cm). "
                f"Status Sistem: {analysis['status']}. "
                f"Berikan penjelasan medis kenapa statusnya demikian dan saran nutrisi spesifik."
            )
            ai_response = model.generate_content(prompt)
            ai_text = ai_response.text
        except Exception as e:
            print(f"AI Error: {e}")

        result = {
            "calculation": analysis,
            "ai_advice": ai_text,
            "child_data": child
        }

        # 3. Simpan DB
        if history_collection is not None:
            history_collection.insert_one({
                "nama_anak": nama,
                "usia_bulan": usia,
                "berat_kg": berat,
                "panjang_cm": panjang,
                "gender": gender,
                "status_result": analysis['status'],
                "ai_advice": ai_text,
                "created_at": datetime.utcnow()
            })

        return jsonify(result)
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    if history_collection is None: return jsonify([])
    cursor = history_collection.find().sort('created_at', -1).limit(50)
    results = []
    for doc in cursor:
        doc['_id'] = str(doc['_id'])
        results.append(doc)
    return jsonify(results)

@app.route('/api/history/<id>', methods=['DELETE'])
def delete_history(id):
    history_collection.delete_one({'_id': ObjectId(id)})
    return jsonify({'msg': 'deleted'})

@app.route('/api/history/update_name', methods=['PUT'])
def update_name():
    data = request.json
    history_collection.update_one(
        {'_id': ObjectId(data['id'])},
        {'$set': {'nama_anak': data['new_name']}}
    )
    return jsonify({'msg': 'updated'})

@app.route('/api/generate_meal_plan', methods=['POST'])
def generate_meal_plan():
    try:
        data = request.json
        child = data.get('child_data')
        prompt = f"Buatkan menu makan 1 hari untuk anak {child['usia_bulan']} bulan, berat {child['berat_kg']}kg."
        resp = model.generate_content(prompt)
        return jsonify({'response': resp.text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    resp = chat_session.send_message(data.get('message'))
    return jsonify({'response': resp.text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)