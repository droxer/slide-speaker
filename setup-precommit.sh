#!/bin/bash

# Pre-commit setup script for SlideSpeaker

set -e

echo "🔧 Setting up pre-commit hooks for SlideSpeaker..."

# Install pre-commit for API
echo "📦 Installing pre-commit for Python API..."
cd api
uv sync --extra=dev
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
cd ..

# Install pre-commit for Web (if using npm/pnpm)
echo "📦 Installing pre-commit for React Web..."
cd web
if command -v pnpm &> /dev/null; then
    pnpm install
    pnpm dlx pre-commit install || true
elif command -v npm &> /dev/null; then
    npm install
    npx pre-commit install || true
fi
cd ..

echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "🔍 To run pre-commit on all files:"
echo "   cd api && pre-commit run --all-files"
echo "   cd web && pre-commit run --all-files"
echo ""
echo "📝 To manually test:"
echo "   git add . && git commit -m 'test pre-commit'"