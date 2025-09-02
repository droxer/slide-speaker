# SlideSpeaker

SlideSpeaker is an AI-powered application that transforms PDF and PowerPoint presentations into engaging video presentations with AI-generated narration and avatars.

## Architecture

For detailed information about the SlideSpeaker architecture, see the [Architecture Documentation](docs/architecture.md).

## Key Features

- **Distributed Processing**: Background task processing with Redis queue for scalability
- **Real-time Progress Tracking**: Live updates on video generation progress
- **Instant Task Cancellation**: Immediate cancellation of processing tasks with resource cleanup
- **Multi-language Support**: Generate content in English, Chinese, Japanese, Korean, and Thai
- **AI Avatar Integration**: HeyGen-powered virtual presenters
- **Text-to-Speech**: Natural voice narration with OpenAI and ElevenLabs
- **Subtitle Generation**: Automatic subtitle creation in multiple languages
- **Responsive Web Interface**: Modern React frontend with real-time feedback

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
- [API Documentation](docs/api.md)
- [Architecture Documentation](docs/architecture.md)

## License

This project is licensed under the MIT License.