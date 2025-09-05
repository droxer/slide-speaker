# SlideSpeaker

From slides to videos with AI voices and avatars.

## Architecture

For detailed information about the SlideSpeaker architecture, see the [Architecture Documentation](docs/architecture.md).

## Key Features

- **Memory-Efficient Video Processing**: Optimized video composition to prevent hanging with AI avatars
- **Distributed Processing**: Background task processing with Redis queue for scalability
- **Real-time Progress Tracking**: Live updates on video generation progress
- **Instant Task Cancellation**: Immediate cancellation of processing tasks with resource cleanup
- **Multi-language Support**: Generate content in English, Chinese, Japanese, Korean, and Thai
- **Multiple AI Services**: OpenAI and Qwen for script generation, HeyGen and DALL-E for avatars
- **Flexible TTS Options**: OpenAI TTS, ElevenLabs, and local TTS providers
- **Script Review**: AI-powered script refinement for better presentation flow
- **Subtitle Generation**: Automatic subtitle creation in multiple languages
- **Responsive Web Interface**: Modern React frontend with real-time feedback
- **Video Validation**: Automatic validation of avatar videos before processing
- **State Persistence**: Local storage prevents data loss on page refresh
- **Enhanced UI**: Improved user experience with better error handling

## Quick Start

1. **API Setup**
   ```bash
   cd api
   uv sync
   # Create .env with your API keys (OpenAI, Qwen, ElevenLabs, HeyGen)
   make dev
   ```

2. **Web Setup**
   ```bash
   cd web
   pnpm install  # or npm install
   pnpm start    # or npm start
   ```

3. **Visit** `http://localhost:3000` to upload presentations and create AI-powered videos

## Documentation

For detailed documentation, see the [docs](docs/) directory:

- [Installation Guide](docs/installation.md)
- [API Documentation](docs/api.md)

## License

This project is licensed under the MIT License.