# SlideSpeaker

Turn slides/PDFs into narrated videos — transcripts, TTS, subtitles, and optional avatars.

SlideSpeaker is an AI-powered platform that transforms your presentations into engaging video content. Whether you have PowerPoint slides or PDF documents, SlideSpeaker can automatically generate narrated videos with optional AI avatars, synchronized subtitles, and professional-quality audio.

## 🚀 Quick Start

### Backend (API)
```bash
cd api
uv sync                      # Install base dependencies
cp .env.example .env         # Create config file
# Edit .env to add your API keys
make dev                     # Start development server (port 8000)
```

### Frontend (Web UI)
```bash
cd web
pnpm install                 # Install dependencies (prefer pnpm)
pnpm start                   # Start development server (port 3000)
```

Visit:
- `http://localhost:3000` - Web UI
- `http://localhost:8000/docs` - API documentation

## 🛠️ Configuration

### Essential API Keys
- **LLM (OpenAI)** - Required for transcript generation
  - `OPENAI_API_KEY` (required)
  - Optional: `OPENAI_BASE_URL` (for custom endpoints)
  - Optional: `OPENAI_TIMEOUT`, `OPENAI_RETRIES`, `OPENAI_BACKOFF`

- **Text-to-Speech**
  - `TTS_SERVICE=openai|elevenlabs` (defaults to openai)
  - ElevenLabs requires `ELEVENLABS_API_KEY`

- **Avatar Generation** (optional)
  - HeyGen: `HEYGEN_API_KEY`
  - OpenAI DALL-E: Uses your `OPENAI_API_KEY`

- **Storage**
  - Defaults to local filesystem
  - For cloud storage, configure S3 or OSS in `.env`

### Storage Options
SlideSpeaker supports multiple storage backends:
- **Local** - Default, stores files in `api/output/`
- **AWS S3** - Configure `AWS_S3_BUCKET_NAME` and credentials
- **Aliyun OSS** - Configure `OSS_BUCKET_NAME` and credentials

## 🎯 What It Does

SlideSpeaker processes your presentations through an AI pipeline:

1. **Content Analysis**
   - Extracts text and images from slides/PDFs
   - Segments content into logical sections

2. **Script Generation**
   - Creates engaging narratives with OpenAI
   - Optional script revision for better flow

3. **Audio Production**
   - Generates natural-sounding speech via OpenAI TTS or ElevenLabs
   - Supports multiple languages

4. **Subtitle Creation**
   - Automatically generates subtitles in your selected language
   - Multiple format support (VTT, SRT)

5. **Video Composition**
   - Combines slides, audio, and subtitles into final video
   - Optional AI avatar presenter (HeyGen/DALL-E)

6. **Task Management**
   - Real-time progress tracking
   - Task monitoring and management
   - Downloadable assets (video, audio, transcripts, subtitles)

## 📡 API Endpoints

All downloads use task-based URLs for stability:

- `GET /api/tasks/{task_id}/video` - Final composed video
- `GET /api/tasks/{task_id}/audio` - Final mixed audio
- `GET /api/tasks/{task_id}/podcast` - 2-person podcast (PDF mode)
- `GET /api/tasks/{task_id}/transcripts/markdown` - Generated transcript
- `GET /api/tasks/{task_id}/subtitles/vtt` - Subtitles (VTT format)
- `GET /api/tasks/{task_id}/subtitles/srt` - Subtitles (SRT format)

## 📁 Project Structure

```
slide-speaker/
├── api/                    # FastAPI backend
│   ├── slidespeaker/       # Core application code
│   │   ├── core/           # State management, task queue
│   │   ├── pipeline/       # Processing steps (PDF/slides)
│   │   ├── processing/     # Audio/video/subtitle generation
│   │   ├── services/       # External API integrations
│   │   ├── storage/        # Unified storage system
│   │   └── routes/         # API endpoints
│   └── server.py           # Main entry point
└── web/                    # React frontend
    └── src/                # UI components and logic
```

## 🧪 Development

### Backend Development
```bash
cd api
make install             # Install dependencies
make dev                 # Start dev server with hot reload
make lint                # Code linting
make typecheck           # Type checking
make check               # Lint + typecheck
```

### Frontend Development
```bash
cd web
make install             # Install dependencies
make dev                 # Start dev server
make lint                # Code linting
make typecheck           # Type checking
make check               # Lint + typecheck
```

## 📚 Documentation

- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [API Documentation](docs/api.md) - Complete API reference
- [Configuration](api/.env.example) - Environment variables reference

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

## 🆘 Support

For issues and feature requests, please [open an issue](../../issues) on GitHub.