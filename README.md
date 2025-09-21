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