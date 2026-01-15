import os
import json
import time
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# AI & DB Tools
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client
import google.generativeai as genai
import PIL.Image

# --- 1. SETUP & CONFIGURATION ---
load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Fetch Keys
api_key = os.getenv("GOOGLE_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Initialize Clients
genai.configure(api_key=api_key)
supabase: Client = create_client(supabase_url, supabase_key)

# Models (Using stable versions)
embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
chat_model = genai.GenerativeModel('gemini-flash-latest')
vision_model = genai.GenerativeModel('gemini-flash-latest')

# Initialize Vector Store for Uploads
vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=embed_model,
    table_name="documents",
    query_name="match_documents"
)

print("✅ Digital Dean API is Online & Connected to Supabase")

# --- 2. HELPER FUNCTION ---
def get_syllabus_context(query, threshold=0.5, count=4):
    try:
        query_vector = embed_model.embed_query(query)
        response = supabase.rpc(
            "match_documents", 
            {
                "query_embedding": query_vector, 
                "match_threshold": threshold, 
                "match_count": count
            }
        ).execute()
        
        matches = response.data
        if not matches:
            return None
        return "\n\n".join([m['content'] for m in matches])
    except Exception as e:
        print(f"Error searching Supabase: {e}")
        return None

# --- 3. API ENDPOINTS ---

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "message": "Digital Dean is watching you."})

# === NEW: UPLOAD SYLLABUS ===
@app.route('/upload', methods=['POST'])
def upload_syllabus():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # 1. Read PDF
            loader = PyMuPDFLoader(filepath)
            pages = loader.load()

            # 2. Split Text
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = text_splitter.split_documents(pages)

            # 3. Upload to Supabase (Batching to be safe)
            # Simple batching implementation
            batch_size = 50
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                vector_store.add_documents(batch)
                time.sleep(1) # Gentle pause for API limits

            # Cleanup
            os.remove(filepath)
            return jsonify({"message": f"Successfully memorized {len(chunks)} knowledge chunks."})

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# === MODULE 1: THE TUTOR (Chat) ===
@app.route('/chat', methods=['POST'])
def chat_tutor():
    data = request.json
    user_question = data.get('question')
    if not user_question: return jsonify({"error": "No question"}), 400

    context = get_syllabus_context(user_question)
    
    prompt = f"""
    You are a strict Digital Dean.
    Context from Syllabus:
    {context if context else "No specific context found in syllabus."}
    
    Student Question: {user_question}
    
    Instructions:
    - Answer based on the syllabus context first.
    - If context is missing, use general knowledge but warn the student.
    - Keep it concise and academic.
    """
    
    response = chat_model.generate_content(prompt)
    return jsonify({"reply": response.text})

# === MODULE 2: THE EXAMINER (Quiz) ===
@app.route('/quiz', methods=['POST'])
def generate_quiz():
    data = request.json
    topic = data.get('topic')
    if not topic: return jsonify({"error": "No topic"}), 400

    context = get_syllabus_context(topic, threshold=0.4, count=5)
    if not context: return jsonify({"error": "Topic not found in syllabus."}), 404

    json_prompt = f"""
    Based on this context: {context}
    Create 5 HARD multiple-choice questions about '{topic}'.
    CRITICAL: Output ONLY valid JSON array.
    Format: [{{ "question": "...", "options": ["A)...", "B)..."], "answer": "A" }}]
    """
    
    try:
        response = chat_model.generate_content(json_prompt)
        raw_text = response.text
        start_index = raw_text.find('[')
        end_index = raw_text.rfind(']') + 1
        clean_json = raw_text[start_index:end_index] if start_index != -1 else raw_text
        return jsonify({"quiz": json.loads(clean_json)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === MODULE 3: THE GRADER (Vision) ===
@app.route('/grade', methods=['POST'])
def grade_image():
    # 1. Validation
    if 'image' not in request.files or 'topic' not in request.form:
        return jsonify({"error": "Missing image or topic"}), 400
        
    file = request.files['image']
    topic = request.form['topic']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # 2. Save Image Temporarily
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # 3. Retrieve Syllabus Context
        syllabus_context = get_syllabus_context(topic)
        if not syllabus_context:
            # Clean up even if we fail here
            if os.path.exists(filepath): 
                os.remove(filepath)
            return jsonify({"error": "Topic not found in syllabus. Cannot grade."}), 404

        # 4. Analyze with Gemini Vision
        img = PIL.Image.open(filepath)
        
        prompt = f"""
        You are a strict Professor. Grade this answer about '{topic}'.
        Syllabus Context: {syllabus_context}
        Compare handwriting strictly to syllabus.
        Output Format (JSON ONLY): {{ "score": "X/10", "feedback": "Critique..." }}
        """
        
        response = vision_model.generate_content([prompt, img])
        
        # --- CRITICAL FIX: CLOSE THE FILE ---
        img.close() 
        # ------------------------------------
        
        # 5. Parse Response
        raw_text = response.text
        start_index = raw_text.find('{')
        end_index = raw_text.rfind('}') + 1
        
        if start_index != -1 and end_index != 0:
            clean_json = raw_text[start_index:end_index]
        else:
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        
        # 6. Delete File (Now safe because img is closed)
        if os.path.exists(filepath): 
            os.remove(filepath)
            
        return jsonify(json.loads(clean_json))

    except Exception as e:
        # Emergency Cleanup
        if os.path.exists(filepath):
            try:
                img.close()
            except: 
                pass
            os.remove(filepath)
        print(f"GRADING ERROR: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)