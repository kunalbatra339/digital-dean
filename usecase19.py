import os
import sys
import time
import warnings

# --- 0. SUPPRESS WARNINGS (Must be at the very top) ---
warnings.filterwarnings("ignore")
import logging
logging.getLogger("absl").setLevel(logging.ERROR)

# --- 1. SETUP & CREDENTIALS ---
from dotenv import load_dotenv

print("⚙️ Loading configuration...")
load_dotenv() # Load the .env file

# Fetch Keys
api_key = os.getenv("GOOGLE_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Safety Check
if not api_key:
    sys.exit("❌ Error: GOOGLE_API_KEY not found. Check your .env file.")
if not supabase_url or not supabase_key:
    sys.exit("❌ Error: Supabase keys not found. Check your .env file.")

print("✅ Secrets loaded!")
print(f"   -> Connected to Supabase Project: {supabase_url}")

# --- 2. IMPORT LIBRARIES ---
print("⚙️ Importing AI libraries...")

# UI Tools
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
console = Console()

# AI & Data Tools
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=api_key)

print("✅ Libraries ready.")

# --- 3. LOCAL FILE SELECTION ---
print("\n" + "="*50)
pdf_filename = input("📂 Drag & Drop your PDF file here (or paste path): ").strip('"').strip("'").strip()

if not os.path.exists(pdf_filename):
    console.print(f"[bold red]❌ Error: File not found at '{pdf_filename}'[/bold red]")
    sys.exit(1)
else:
    console.print(f"[bold green]✅ File found: {pdf_filename}[/bold green]")

# --- 4. INITIALIZE AI MODELS ---
print("\n⚙️ Configuring AI Models...")
embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
chat_model = genai.GenerativeModel('gemini-flash-latest')

# --- 5. READ & INDEX THE PDF (Using Local FAISS for now) ---
vector_store = None
try:
    print(f"📖 Reading PDF...")
    loader = PyMuPDFLoader(pdf_filename)
    pages = loader.load()
    
    # Split text
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    chunks = text_splitter.split_documents(pages)
    print(f"   -> Split into {len(chunks)} chunks.")
    
    # Create Index
    print("🗂️ Indexing (Creating Memory)...")
    vector_store = FAISS.from_documents(chunks, embed_model)
    console.print("[bold green]✅ Success! The 'Smart Study Buddy' is ready.[/bold green]")

except Exception as e:
    console.print(f"[bold red]❌ Error during indexing: {e}[/bold red]")
    sys.exit(1)

# --- 6. CHAT FUNCTION ---
def ask_pdf(question):
    console.print(f"\n[bold cyan]❓ Question:[/bold cyan] {question}")
    
    # Search
    docs = vector_store.similarity_search(question, k=3)
    context = "\n\n".join([d.page_content for d in docs])
    
    # Answer Logic
    prompt = f"""
    You are a highly intelligent and helpful tutor. 
    
    Your Goal: Answer the student's question comprehensively.
    
    Instructions:
    1. First, look at the 'Context from PDF' below. If the answer is there, use it.
    2. CRITICAL: If the PDF does not have the answer, or if the student asks for external resources, USE YOUR OWN GENERAL KNOWLEDGE.
    3. Format your answer nicely using Markdown (bullet points, bold text, and tables).
    
    Context from PDF:
    {context}
    
    Question: {question}
    """
    try:
        response = chat_model.generate_content(prompt)
        console.print(Panel(Markdown(response.text), title="🤖 AI Answer", border_style="green"))
    except Exception as e:
         console.print(f"[bold red]Error generating answer: {e}[/bold red]")
    print("-" * 50)

# --- 7. INTERACTIVE LOOP ---
if vector_store:
    print("\n💬 SMART CHAT SESSION STARTED! (Type 'exit' to stop)")
    print("-" * 50)
    
    while True:
        try:
            user_question = input("Enter your question: ")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        
        if user_question.lower() in ["exit", "quit", "stop", "bye"]:
            print("👋 Goodbye! Happy studying.")
            break
            
        if user_question.strip() == "":
            continue
            
        ask_pdf(user_question)
else:
    print("❌ Setup failed. Cannot start chat.")