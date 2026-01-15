import os
import sys
import time
import json # <--- NEW: To parse the Quiz data
import warnings
from dotenv import load_dotenv

# --- 0. SUPPRESS WARNINGS ---
warnings.filterwarnings("ignore")
import logging
logging.getLogger("absl").setLevel(logging.ERROR)

# --- 1. SETUP & CREDENTIALS ---
print("⚙️ Loading configuration...")
load_dotenv()

# UI Tools
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt # <--- NEW: For nicer inputs
console = Console()

# AI Tools
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import SupabaseVectorStore
from supabase.client import Client, create_client
import google.generativeai as genai

# Fetch Keys
api_key = os.getenv("GOOGLE_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not api_key or not supabase_url or not supabase_key:
    sys.exit("❌ Error: Missing keys in .env file.")

# Configure Clients
try:
    genai.configure(api_key=api_key)
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    console.print(f"[bold red]❌ Connection Error: {e}[/bold red]")
    sys.exit(1)

print(f"✅ Connected to Supabase Project")

# --- 2. INITIALIZE AI MODELS ---
print("⚙️ Configuring AI Models...")
embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
# We use a slightly more creative temperature for quizzes so they aren't boring
chat_model = genai.GenerativeModel('gemini-flash-latest') 

# --- 3. CLOUD MEMORY SETUP ---
vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=embed_model,
    table_name="documents",
    query_name="match_documents"
)

# --- 4. UPLOAD LOGIC ---
print("\n" + "="*50)
choice = Prompt.ask("📂 Upload NEW Syllabus?", choices=["yes", "no"], default="no")

if choice == "yes":
    pdf_filename = input("   -> Drag & Drop PDF here: ").strip('"').strip("'").strip()
    
    if os.path.exists(pdf_filename):
        try:
            print("   📖 Reading PDF...")
            loader = PyMuPDFLoader(pdf_filename)
            pages = loader.load()
            
            print("   ✂️  Splitting text...")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
            chunks = text_splitter.split_documents(pages)
            
            print(f"   🚀 Found {len(chunks)} chunks. Starting Batch Upload...")
            
            batch_size = 50 
            total_batches = (len(chunks) + batch_size - 1) // batch_size
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                current_batch = (i // batch_size) + 1
                print(f"      📦 Uploading Batch {current_batch}/{total_batches}...")
                vector_store.add_documents(batch)
                time.sleep(2) 
            
            console.print("[bold green]✅ Upload Complete![/bold green]")
        except Exception as e:
            console.print(f"[bold red]❌ Error: {e}[/bold red]")
    else:
        console.print("[bold red]❌ File not found.[/bold red]")
else:
    console.print("[bold yellow]⚡ Skipping upload. Using existing memory from Cloud.[/bold yellow]")

# --- 5. SEARCH FUNCTION (Passive Mode) ---
def ask_tutor(question):
    console.print(f"\n[bold cyan]❓ Searching Syllabus for:[/bold cyan] {question}")
    
    try:
        query_vector = embed_model.embed_query(question)
        response = supabase.rpc("match_documents", {"query_embedding": query_vector, "match_threshold": 0.5, "match_count": 4}).execute()
        
        matches = response.data
        context = "\n\n".join([match['content'] for match in matches]) if matches else "No relevant info found."

        prompt = f"""
        You are a strict Digital Dean.
        Context: {context}
        Question: {question}
        Answer based on context. If missing, use general knowledge but warn the student.
        """
        ai_response = chat_model.generate_content(prompt)
        console.print(Panel(Markdown(ai_response.text), title="🤖 Digital Dean", border_style="blue"))
        
    except Exception as e:
         console.print(f"[bold red]Error: {e}[/bold red]")
    print("-" * 50)

# --- 6. QUIZ FUNCTION (Active Mode - ROBUST FIX) ---
def start_quiz(topic):
    console.print(f"\n[bold red]🚨 SURPRISE QUIZ DETECTED: {topic.upper()} 🚨[/bold red]")
    console.print("Generative AI is building your exam... please wait...")

    try:
        # 1. Get Context
        query_vector = embed_model.embed_query(topic)
        response = supabase.rpc("match_documents", {"query_embedding": query_vector, "match_threshold": 0.4, "match_count": 5}).execute()
        context = "\n\n".join([m['content'] for m in response.data])

        # 2. Strict JSON Prompt
        json_prompt = f"""
        You are a ruthless exam setter.
        Based on this context: {context}
        
        Create 5 HARD multiple-choice questions about '{topic}'.
        
        CRITICAL: Output ONLY valid JSON array. No text before or after.
        Format:
        [
            {{
                "question": "The actual question?",
                "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                "answer": "A"
            }}
        ]
        """
        
        # 3. Generate
        ai_response = chat_model.generate_content(json_prompt)
        raw_text = ai_response.text

        # --- FIX: ROBUST JSON EXTRACTOR ---
        try:
            # Find the first '[' and the last ']'
            start_index = raw_text.find('[')
            end_index = raw_text.rfind(']') + 1
            
            if start_index == -1 or end_index == 0:
                raise ValueError("No JSON brackets found in response.")
                
            clean_json = raw_text[start_index:end_index]
            quiz_data = json.loads(clean_json)
            
        except json.JSONDecodeError:
            # Fallback: Sometimes the AI adds markdown code blocks
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
            quiz_data = json.loads(clean_json)
        # ----------------------------------

        # 4. The Exam Loop
        score = 0
        for i, q in enumerate(quiz_data):
            console.print(f"\n[bold white]Q{i+1}: {q['question']}[/bold white]")
            for opt in q['options']:
                print(opt)
            
            user_ans = Prompt.ask("Your Answer", choices=["A", "B", "C", "D"], default="A").upper()
            
            # Extract just the letter from the correct answer
            correct_letter = q['answer'].split(")")[0].strip().upper()
            
            if user_ans == correct_letter:
                console.print("[bold green]✅ CORRECT[/bold green]")
                score += 1
            else:
                console.print(f"[bold red]❌ WRONG! Correct was {q['answer']}[/bold red]")
                
        # 5. Final Grade
        percentage = (score / 5) * 100
        console.print(Panel(f"Final Score: {score}/5 ({percentage}%)", title="🎓 Report Card", border_style="red" if percentage < 60 else "green"))

    except Exception as e:
        console.print(f"[bold red]Quiz Generation Failed: {e}[/bold red]")
        console.print("[yellow]Tip: Try a broader topic name.[/yellow]")

# --- 7. MAIN INTERACTIVE LOOP ---
print("\n💬 DIGITAL DEAN ONLINE.")
print("👉 Type a question to ask.")
print("👉 Type 'quiz [topic]' to take a test (e.g., 'quiz pointers').")
print("👉 Type 'exit' to quit.")
print("-" * 50)

while True:
    try:
        user_input = console.input("[bold yellow]Student > [/bold yellow]").strip()
    except KeyboardInterrupt:
        break
    
    if user_input.lower() in ["exit", "quit"]:
        print("👋 Dismissed.")
        break
        
    # ROUTING LOGIC (The Brain)
    if user_input.lower().startswith("quiz "):
        # User wants to fight
        topic = user_input[5:].strip() # Extract topic after "quiz "
        start_quiz(topic)
    elif user_input:
        # User wants to learn
        ask_tutor(user_input)