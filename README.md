# SlideSpeaker

SlideSpeaker is an AI-powered application that transforms PDF and PowerPoint presentations into engaging video presentations with AI-generated narration and avatars.

## Quick Start

1. **API Setup**
   ```bash
   cd api
   uv sync
   # Create .env with your API keys (OpenAI, ElevenLabs, HeyGen)
   make dev
   ```

2. **Web Setup**
   ```bash
   cd web
   npm install
   npm start
   ```

3. **Visit** `http://localhost:3000` to upload presentations and create AI-powered videos

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Installation Guide](docs/installation.md)
- [Development Guide](docs/development.md)
- [API Documentation](docs/api.md)
- [Architecture Overview](docs/architecture.md)

## License

This project is licensed under the MIT License.