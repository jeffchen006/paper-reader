#!/bin/bash
# Run all tests for Literature Review Tool

echo "="
echo "🧪 Running Test Suite"
echo "="
echo ""

# Check if pytest is installed
if ! python -c "import pytest" 2>/dev/null; then
    echo "⚠️  pytest not found. Installing test dependencies..."
    pip install pytest pytest-cov
    echo ""
fi

echo "Available test options:"
echo "  1. Quick verification (recommended first)"
echo "  2. Configuration tests only"
echo "  3. Retriever tests (arXiv, Semantic Scholar, local DB)"
echo "  4. Generator tests (makes real LLM API calls)"
echo "  5. All unit tests"
echo ""

read -p "Select option (1-5): " choice

case $choice in
    1)
        echo ""
        echo "Running quick verification..."
        python verify_setup.py
        ;;
    2)
        echo ""
        echo "Running configuration tests..."
        python -m pytest tests/test_config.py -v
        ;;
    3)
        echo ""
        echo "Running retriever tests..."
        python -m pytest tests/test_retrievers.py -v
        ;;
    4)
        echo ""
        echo "Running generator tests (will make API calls)..."
        python -m pytest tests/test_generator.py -v
        ;;
    5)
        echo ""
        echo "Running all tests..."
        python -m pytest tests/ -v
        ;;
    *)
        echo "Invalid option. Running quick verification..."
        python verify_setup.py
        ;;
esac

echo ""
echo "="
echo "✨ Tests complete!"
echo "="
