import os
import sys
import time
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

# DEBUG: Check for common copy-paste errors
if supabase_key and " " in supabase_key:
    console.print("[bold red]❌ Error: Your SUPABASE_KEY in .env has spaces! Please remove them.[/bold red]")
    sys.exit(1)

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
chat_model = genai.GenerativeModel('gemini-flash-latest')

# --- 3. CLOUD MEMORY SETUP ---
# We still use this for UPLOADING, because that part works fine.
vector_store = SupabaseVectorStore(
    client=supabase,
    embedding=embed_model,
    table_name="documents",
    query_name="match_documents"
)

# --- 4. UPLOAD LOGIC ---
print("\n" + "="*50)
choice = input("📂 Do you want to upload a NEW Syllabus? (yes/no): ").lower().strip()

if choice in ["yes", "y"]:
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
            
            # Batch Processing to prevent crashes
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

# --- 5. CHAT FUNCTION (FIXED: Uses Direct RPC) ---
def ask_tutor(question):
    console.print(f"\n[bold cyan]❓ Question:[/bold cyan] {question}")
    
    try:
        # 1. Convert Question to Vector (Math)
        query_vector = embed_model.embed_query(question)
        
        # 2. Call Supabase Directly (Bypassing broken LangChain wrapper)
        response = supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_vector,
                "match_threshold": 0.5, # Adjust this if results are too loose
                "match_count": 4
            }
        ).execute()
        
        # 3. Extract Text from Results
        matches = response.data
        if not matches:
            context = "No relevant info found in syllabus."
        else:
            context = "\n\n".join([match['content'] for match in matches])

        # 4. Generate Answer
        prompt = f"""
        You are a strict but helpful Digital Dean.
        
        Context from Syllabus:
        {context}
        
        Student Question: {question}
        
        Instructions:
        1. Answer based on the syllabus context first.
        2. If the info is missing, use general knowledge but warn the student ("This isn't in your syllabus, but...").
        3. Format nicely with Markdown.
        """
        
        ai_response = chat_model.generate_content(prompt)
        console.print(Panel(Markdown(ai_response.text), title="🤖 Digital Dean", border_style="blue"))
        
    except Exception as e:
         console.print(f"[bold red]Error: {e}[/bold red]")
    print("-" * 50)

# --- 6. INTERACTIVE LOOP ---
print("\n💬 DIGITAL DEAN IS ONLINE. (Type 'exit' to stop)")
print("-" * 50)

while True:
    try:
        user_question = input("Student: ")
    except KeyboardInterrupt:
        break
    
    if user_question.lower() in ["exit", "quit", "stop"]:
        print("👋 Class dismissed.")
        break
        
    if user_question.strip():
        ask_tutor(user_question)