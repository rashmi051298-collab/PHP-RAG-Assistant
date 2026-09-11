#!/bin/bash
# Setup script for PHP RAG Assistant (Unix/Linux/macOS)

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║  PHP RAG Assistant - Setup Script                     ║"
echo "║  Version 1.0                                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
	echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
	exit 1
fi

PYTHON_CMD="python3"
echo "✓ Python found: $($PYTHON_CMD --version)"

# Step 1: Create virtual environment
VENV_DIR="venv"
echo ""
echo "════════════════════════════════════════════════════════"
echo "📦 Creating virtual environment..."
echo "════════════════════════════════════════════════════════"

if [ -d "$VENV_DIR" ]; then
	echo "✓ Virtual environment already exists at $VENV_DIR/"
else
	$PYTHON_CMD -m venv $VENV_DIR
	echo "✓ Virtual environment created"
fi

# Step 2: Activate virtual environment
source $VENV_DIR/bin/activate
echo "✓ Virtual environment activated"

# Step 3: Upgrade pip
echo ""
echo "════════════════════════════════════════════════════════"
echo "📦 Upgrading pip, setuptools, and wheel..."
echo "════════════════════════════════════════════════════════"

python -m pip install --upgrade pip setuptools wheel > /dev/null 2>&1 || echo "⚠ pip upgrade had issues, continuing..."

# Step 4: Install requirements
echo ""
echo "════════════════════════════════════════════════════════"
echo "📦 Installing Python dependencies..."
echo "════════════════════════════════════════════════════════"

if python -m pip install -r requirements.txt; then
	echo "✓ Dependencies installed successfully"
else
	echo "❌ Failed to install dependencies"
	exit 1
fi

# Step 5: Create directories
echo ""
echo "════════════════════════════════════════════════════════"
echo "📁 Creating project directories..."
echo "════════════════════════════════════════════════════════"

mkdir -p data/laravel-crm-2.2
mkdir -p vectorstore
echo "✓ Created data/laravel-crm-2.2"
echo "✓ Created vectorstore"

# Success message
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║     Setup Completed Successfully! ✓                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

echo "📋 Next Steps:"
echo ""
echo "1. ✓ Virtual environment is ALREADY ACTIVATED"
echo "   (You see 'venv' at the start of your terminal)"
echo ""
echo "2. ADD YOUR PHP FILES:"
echo "   Copy your PHP files to: data/laravel-crm-2.2/"
echo ""
echo "3. INGEST DATA:"
echo "   python ingest.py"
echo ""
echo "4. RUN STREAMLIT APP:"
echo "   streamlit run app.py"
echo ""
echo "📚 Documentation: See README.md for detailed instructions"
echo "⚡ Quick tips: See QUICKSTART.md for fast setup guide"
echo ""
echo "════════════════════════════════════════════════════════"
