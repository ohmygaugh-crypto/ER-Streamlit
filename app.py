# Hugging Face Spaces entry point
# This file imports and runs the main Streamlit application

import subprocess
import sys

if __name__ == "__main__":
    # Run the main Streamlit app
    subprocess.run([sys.executable, "-m", "streamlit", "run", "visualize_ER_networks_from_csv.py", "--server.port", "7860", "--server.address", "0.0.0.0"])
