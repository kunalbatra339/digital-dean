# 🎓 Digital Dean: AI-Powered Study Assistant
Digital Dean is a full-stack, AI-driven educational platform that transforms the way students interact with their course materials. Utilizing **Retrieval-Augmented Generation (RAG)** and **Vision AI**, it acts as a strict, highly knowledgeable professor that tests, tutors, and grades students based strictly on their uploaded syllabus.

---

## ✨ Key Features

### 📖 1. The Tutor (RAG Chatbot)
* **Dynamic Knowledge Ingestion:** Upload any syllabus or textbook chapter as a PDF. The backend chunks, embeds, and stores the knowledge in a vector database.
* **Context-Aware Responses:** Ask questions, and the AI will scan the uploaded documents to provide answers derived *only* from the official syllabus.

### 🧠 2. The Examiner (Automated Quizzes)
* **Dynamic Generation:** Enter a topic, and the AI generates 5 high-difficulty Multiple Choice Questions (MCQs) based on the ingested syllabus context.
* **Real-time Evaluation:** Interactive UI that grades your exam instantly and determines if you pass the protocol.

### 📸 3. The Grader (Vision AI)
* **Handwriting Analysis:** Snap a photo of your handwritten homework and upload it.
* **Strict Evaluation:** The Vision AI reads your handwriting, compares the logic and keywords against the official syllabus, and assigns a strict score (X/10) along with detailed critique and feedback.

### 🌙 4. UI/UX: Nocturnal Focus Mode
* A premium, distraction-free dark mode UI designed to reduce eye strain during late-night study sessions.
* "Holy Grail" Flexbox layout ensuring seamless scrolling and persistent state management (chat history is saved even when switching between tabs).

---

## 🛠️ Tech Stack

**Frontend (Client)**
* **React.js** (via Vite)
* **Axios** (API communication)
* **Lucide-React** (Icons)
* Custom CSS (Responsive, Mobile-First)
* *Deployed on **Vercel***

**Backend (Server)**
* **Python & Flask** (REST API)
* **LangChain & PyMuPDF** (Document parsing and chunking)
* **Pillow** (Image processing)
* **Gunicorn** (Production WSGI server)
* *Deployed on **Render***

**AI & Database**
* **Google Gemini 1.5 Flash & Vision Pro** (LLM & Image processing)
* **Google Generative AI Embeddings** (`text-embedding-004`)
* **Supabase** (PostgreSQL Vector Database for semantic search)

---

## 🚀 How to Run Locally

If you want to clone this project and run it on your own machine, follow these steps:

### Prerequisites
* Node.js & npm installed
* Python 3.10+ installed
* A Google Gemini API Key
* A Supabase Project (with a `documents` table configured for pgvector)

### 1. Backend Setup
Navigate to the backend directory (or root if combined):

```bash
# Create a virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate
# Activate it (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

```

Create a `.env` file in the same directory and add your keys:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

```

Run the server:

```bash
python app.py

```

*The API will start at `http://127.0.0.1:5000*`

### 2. Frontend Setup

Open a new terminal and navigate to the frontend directory:

```bash
# Install Node dependencies
npm install

# Start the Vite development server
npm run dev

```

*The app will start at `http://localhost:5173*`

---

## 🔒 Environment Variables

To deploy this project yourself, you must configure the following environment variables on your hosting provider (e.g., Render):

* `GOOGLE_API_KEY`
* `SUPABASE_URL`
* `SUPABASE_KEY`

---

## 👨‍💻 Author

Built by **Kunal Batra**. If you found this project helpful or interesting, feel free to drop a ⭐ on the repository!

```

```
