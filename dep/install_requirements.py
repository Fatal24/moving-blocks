import sys
import subprocess
import os

def install_requirements():
    # 1. Get the folder where THIS script is located
    script_folder = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Build the full path to requirements.txt
    requirements_file = os.path.join(script_folder, "requirements.txt")

    # 3. Check if the file exists using the full path
    if not os.path.exists(requirements_file):
        print(f"❌ Error: The file '{requirements_file}' was not found.")
        return

    print(f"📦 Installing libraries from {requirements_file}...")

    try:
        # 4. Run pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("\n✅ Success! All libraries installed.")
        
    except subprocess.CalledProcessError:
        print("\n❌ Error: Failed to install one or more libraries.")

if __name__ == "__main__":
    install_requirements()