"""
Main Streamlit App: Ontology-Driven Knowledge Graph Discovery
Entry point for the lightweight ontology extraction system
"""

import streamlit as st
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from ontology_graph_app import OntologyGraphApp

def main():
    """Main entry point for the ontology discovery app"""
    
    # Initialize and run the app
    app = OntologyGraphApp()
    app.run()

if __name__ == "__main__":
    main()


