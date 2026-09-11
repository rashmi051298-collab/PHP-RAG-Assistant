#!/usr/bin/env python
"""
Setup script for PHP RAG Assistant.
Creates virtual environment and installs dependencies.
"""

import os
import sys
import subprocess
import platform


def run_command(command, description):
    """Run a shell command and report status."""
    print(f"\n{'=' * 60}")
    print(f"📦 {description}")
    print(f"{'=' * 60}")

    try:
        if isinstance(command, str):
            result = subprocess.run(command, shell=True, check=True)
        else:
            result = subprocess.run(command, check=True)

        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e}")
        return False


def main():
    """Main setup function."""
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║     PHP RAG Assistant - Setup Script                ║
    ║     Version 1.0                                      ║
    ╚══════════════════════════════════════════════════════╝
    """)

    # Detect OS
    os_name = platform.system()
    is_windows = os_name == "Windows"

    # Step 1: Create virtual environment
    venv_dir = "venv"
    if os.path.exists(venv_dir):
        print(f"✓ Virtual environment already exists at {venv_dir}/")
    else:
        if not run_command(
            f"{sys.executable} -m venv {venv_dir}",
            "Creating virtual environment"
        ):
            print("Failed to create virtual environment")
            return False

    # Step 2: Get Python executable path in venv
    if is_windows:
        python_exe = os.path.join(venv_dir, "Scripts", "python.exe")
        activate_cmd = os.path.join(venv_dir, "Scripts", "activate.bat")
    else:
        python_exe = os.path.join(venv_dir, "bin", "python")
        activate_cmd = os.path.join(venv_dir, "bin", "activate")

    print(f"\n✓ Virtual environment path: {python_exe}")
    print(f"✓ Activation command: {activate_cmd}")

    # Step 3: Upgrade pip
    if not run_command(
        f"{python_exe} -m pip install --upgrade pip setuptools wheel",
        "Upgrading pip, setuptools, and wheel"
    ):
        print("Warning: pip upgrade failed, continuing anyway...")

    # Step 4: Install requirements
    if not run_command(
        f"{python_exe} -m pip install -r requirements.txt",
        "Installing Python dependencies from requirements.txt"
    ):
        print("Failed to install dependencies")
        return False

    # Step 5: Create necessary directories
    print(f"\n{'=' * 60}")
    print("📁 Creating project directories")
    print(f"{'=' * 60}")

    directories = [
        "data/laravel-crm-2.2",
        "vectorstore",
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created/verified directory: {directory}")

    # Step 6: Installation summary
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║           Setup Completed Successfully! ✓            ║
    ╚══════════════════════════════════════════════════════╝
    """)

    print("\n📋 Next Steps:\n")
    print("1. ACTIVATE VIRTUAL ENVIRONMENT:")
    if is_windows:
        print(f"   {activate_cmd}")
    else:
        print(f"   source {activate_cmd}")

    print("\n2. ADD YOUR PHP FILES:")
    print("   Copy your PHP files to: data/laravel-crm-2.2/")

    print("\n3. INGEST DATA:")
    print(f"   {python_exe} ingest.py")

    print("\n4. RUN STREAMLIT APP:")
    print(f"   {python_exe} -m streamlit run app.py")

    print("\n📚 Documentation: See README.md for detailed instructions")
    print("\n" + "=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
