import os
import subprocess
import threading
import time
from pathlib import Path

# Function to start the FastAPI backend
def start_fastapi():
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)

# Function to modify Streamlit app for deployment
def update_streamlit_for_spaces():
    streamlit_file = Path("app/streamlit/app.py")
    content = streamlit_file.read_text()
    
    # Change localhost:8000 to connect to the FastAPI backend on the same instance
    modified_content = content.replace(
        "http://localhost:8000", 
        "http://localhost:8000"  # For Spaces, this still works because it's on the same instance
    )
    
    streamlit_file.write_text(modified_content)

# Update the Streamlit app
update_streamlit_for_spaces()

# Start FastAPI in a separate thread
threading.Thread(target=start_fastapi, daemon=True).start()

# Wait a moment for FastAPI to start
time.sleep(5)

# Start Streamlit
os.system("streamlit run app/streamlit/app.py")