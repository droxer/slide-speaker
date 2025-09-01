# Development Guide

## API Development

### Makefile Commands

The API directory includes a Makefile with convenient development commands:

```bash
cd api

# Install dependencies
make install

# Start development server with auto-reload
make dev

# Start production server
make start

# Run tests
make test

# Code linting
make lint

# Format code
make format

# Clean temporary files
make clean

# Start Redis server (macOS)
make redis-start

# Stop Redis server (macOS)
make redis-stop

# Initial setup (install deps + start redis)
make setup

# Show current status
make status
```

### Manual Commands

If you prefer to run commands manually:

```bash
# Install dependencies
uv sync

# Start development server
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
uv run python -m pytest tests/ -v

# Code linting
uv run python -m ruff check .

# Format code
uv run python -m ruff format .
```

## Web Development

### NPM Scripts

```bash
cd web

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test

# Eject from Create React App (if needed)
npm run eject
```

### Project Structure

```
web/
├── public/              # Static assets
├── src/                 # Source code
│   ├── App.js           # Main application component
│   ├── App.css          # Styles
│   └── index.js         # Entry point
├── package.json         # Dependencies and scripts
└── README.md            # Create React App documentation
```