"""
Setup script for RAG vs GraphRAG demo
Downloads required models and initializes the system
"""
import subprocess
import sys
import os
from pathlib import Path

def install_spacy_model():
    """Download spaCy English model"""
    try:
        print("Downloading spaCy English model...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✅ spaCy model installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing spaCy model: {e}")
        return False
    return True

def create_directories():
    """Create necessary directories"""
    directories = [
        "data",
        "src", 
        "notebooks",
        "assets",
        "graph_db"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ Directories created")

def check_data_files():
    """Check if sample data files exist"""
    data_dir = Path("data")
    required_files = [
        "meeting_notes_q4_planning.txt",
        "product_spec_auth_service.txt", 
        "support_tickets_enterprise.txt",
        "engineering_decisions_log.txt"
    ]
    
    missing_files = []
    for file in required_files:
        if not (data_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing data files: {missing_files}")
        return False
    
    print("✅ All data files present")
    return True

def main():
    """Main setup function"""
    print("🚀 Setting up RAG vs GraphRAG Demo...")
    
    # Create directories
    create_directories()
    
    # Check data files
    if not check_data_files():
        print("Please ensure all sample data files are in the data/ directory")
        return False
    
    # Install spaCy model
    if not install_spacy_model():
        print("Warning: spaCy model installation failed. Entity extraction may use fallback methods.")
    
    print("\n✅ Setup complete!")
    print("\nTo run the demo:")
    print("1. Activate virtual environment: source venv/bin/activate")
    print("2. Set OpenAI API key: export OPENAI_API_KEY='your-key-here'")
    print("3. Run Streamlit app: streamlit run app.py")
    
    return True

if __name__ == "__main__":
    main()
