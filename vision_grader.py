import os
import sys
import time
from dotenv import load_dotenv

# --- 0. SETUP ---
import warnings
warnings.filterwarnings("ignore")
import logging
logging.getLogger("absl").setLevel(logging.ERROR)

print("⚙️ Loading Vision Engine...")
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
console = Console()

# AI & DB Tools
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from supabase.client import Client, create_client
import google.generativeai as genai
import PIL.Image

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

print(f"✅ Connected to 'Smart Study Buddy' Database")

# --- 1. CONFIGURATION ---
embed_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
# We use the FLASH model because it handles images very quickly and cheaply
vision_model = genai.GenerativeModel('gemini-flash-latest')

# --- 2. THE GRADING FUNCTION ---
def grade_submission(topic, image_path):
    console.print(f"\n[bold yellow]🔍 1. Searching Syllabus for '{topic}'...[/bold yellow]")
    
    # A. Retrieve the "Golden Source" (The correct answer from Syllabus)
    try:
        query_vector = embed_model.embed_query(topic)
        response = supabase.rpc("match_documents", {"query_embedding": query_vector, "match_threshold": 0.4, "match_count": 3}).execute()
        
        matches = response.data
        if not matches:
            console.print("[bold red]❌ No syllabus data found for this topic! I can't grade you fairly.[/bold red]")
            return

        syllabus_context = "\n\n".join([m['content'] for m in matches])
        console.print("[green]   -> Found official source material.[/green]")

    except Exception as e:
        console.print(f"[bold red]Error retrieving context: {e}[/bold red]")
        return

    # B. Load the Image
    console.print(f"[bold yellow]📸 2. Analyzing Handwriting...[/bold yellow]")
    try:
        # Clean path (remove quotes if drag-and-dropped)
        clean_path = image_path.strip('"').strip("'").strip()
        img = PIL.Image.open(clean_path)
    except Exception as e:
        console.print(f"[bold red]❌ Could not open image: {e}[/bold red]")
        return

    # C. The Grading Prompt
    prompt = f"""
    You are a strict University Professor.
    
    Task: Grade the student's handwritten answer.
    
    1. THE OFFICIAL SYLLABUS (The Truth):
    {syllabus_context}
    
    2. INSTRUCTIONS:
    - Read the handwriting in the image provided.
    - Compare it strictly against the Syllabus Context above.
    - If the student writes something correct that is NOT in the syllabus context, give partial credit but warn them.
    - If the student contradicts the syllabus, penalize heavily.
    
    3. OUTPUT FORMAT:
    - Start with a "GRADE: X/10".
    - Provide a "Critique" section explaining exactly what they missed compared to the syllabus.
    - Be harsh but constructive.
    """

    # D. Send to Gemini Vision
    console.print("[bold cyan]🤖 Grading in progress...[/bold cyan]")
    try:
        response = vision_model.generate_content([prompt, img])
        console.print(Panel(Markdown(response.text), title="📝 Digital Dean's Report", border_style="red"))
    except Exception as e:
        console.print(f"[bold red]AI Grading Error: {e}[/bold red]")

# --- 3. MAIN LOOP ---
print("\n👁️  VISION GRADING MODULE ONLINE.")
print("👉 Provide a topic and a photo of your written answer.")
print("👉 Type 'exit' to quit.")
print("-" * 50)

while True:
    try:
        topic_input = Prompt.ask("\n[bold cyan]1. What topic did you write about?[/bold cyan] (e.g. 'Ohm's Law')").strip()
        if topic_input.lower() in ["exit", "quit"]: break
        
        image_input = Prompt.ask("[bold cyan]2. Drag & Drop Image File[/bold cyan]").strip()
        if image_input.lower() in ["exit", "quit"]: break
        
        if topic_input and image_input:
            grade_submission(topic_input, image_input)
            
    except KeyboardInterrupt:
        print("\n👋 Exiting.")
        break