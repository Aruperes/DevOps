from flask import Flask, render_template, request, jsonify
import google.generativeai as genai

app = Flask(__name__)

# --- PENTING ---
# Masukkan API Key Gemini Anda langsung di sini
# Ganti "MASUKKAN_API_KEY_ANDA_DI_SINI" dengan API Key Anda
API_KEY = "MASUKKAN_API_KEY_ANDA_DI_SINI"
# ---------------

# Konfigurasi API Key Gemini
try:
    if not API_KEY or API_KEY == "MASUKKAN_API_KEY_ANDA_DI_SINI":
        print("*****************************************************************")
        print("PERINGATAN: API_KEY belum diisi di app.py.")
        print("Anda bisa mendapatkan API Key dari: https://aistudio.google.com/app/apikey")
        print("*****************************************************************")
    
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"Error konfigurasi Gemini: {e}")

# Inisialisasi model Gemini
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
)

model = genai.GenerativeModel(
    model_name="gemini-1.0-pro",
    generation_config=model_config,
    system_instruction=system_instruction
)

# Buat sesi chat (agar bisa mengingat konteks)
chat_session = model.start_chat(history=[])

@app.route('/')
def index():
    """Menampilkan halaman utama (index.html)."""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint API untuk menerima pesan dari user dan mengirim balasan dari Gemini."""
    try:
        data = request.json
        user_message = data.get('message')

        if not user_message:
            return jsonify({'error': 'Pesan tidak boleh kosong'}), 400

        # Kirim pesan ke Gemini melalui sesi chat
        response = chat_session.send_message(user_message)
        
        # Kembalikan respons dari Gemini sebagai JSON
        return jsonify({'response': response.text})

    except Exception as e:
        print(f"Error saat memproses chat: {e}")
        return jsonify({'error': 'Terjadi kesalahan pada server'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)