# SlideSpeaker

Turn slides/PDFs into narrated videos — transcripts, TTS, subtitles, and optional avatars.

SlideSpeaker is an AI-powered platform that transforms your presentations into engaging video content. Whether you have PowerPoint slides or PDF documents, SlideSpeaker can automatically generate narrated videos with optional AI avatars, synchronized subtitles, and professional-quality audio.

## ⚠️ Project Status

SlideSpeaker is under active development. Expect rapid iteration, breaking changes, and incomplete tooling while we work toward production readiness.

## ✨ Features

- Automated script generation from slide decks or PDFs
- Natural-sounding text-to-speech narration with configurable voices
- Optional AI avatars synced to narration for presenter-style videos
- Podcast-ready audio exports for sharing beyond video platforms
- Subtitle outputs in VTT/SRT formats aligned to the narration
- Task-based API that coordinates the full processing pipeline end-to-end
- Responsive light, dark, and auto themes with per-user preferences
- Global language switcher with localized UI labels and stored preferences
- Hybrid authentication powered by NextAuth (Google OAuth + email/password) backed by FastAPI endpoints
- WCAG 2.1 AA compliance with enhanced accessibility features
- High contrast themes for both light and dark modes
- Support for additional languages: Thai, Korean, and Japanese
- Optimized task creation page and improved processing display
- Enhanced web performance for better user experience

## 🚀 Quick Start

### Backend (API)
```bash
cd api
uv sync                      # Install base dependencies
cp .env.example .env         # Create config file
# Edit .env to add your API keys
make dev                     # Start development server (port 8000)
```

#### User Management CLI
```bash
cd api
python scripts/user_cli.py list
python scripts/user_cli.py create --email you@example.com --password secret --name "You"
```
Use `--help` on any subcommand to see additional options (`show`, `set-password`, `delete`).

### Frontend (Web UI)
```bash
cd web
pnpm install                 # Install dependencies (prefer pnpm)
pnpm start                   # Start development server (port 3000)
```

## ♿ Accessibility

SlideSpeaker is committed to providing an inclusive experience for all users:
- WCAG 2.1 AA compliance for web accessibility standards
- High contrast themes available for both light and dark modes
- Enhanced focus indicators for keyboard navigation
- Screen reader friendly interface
- Support for multiple languages to serve a diverse user base

Visit:
- `http://localhost:3000` - Web UI
- `http://localhost:8000/docs` - API documentation

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

### Authentication
- **API (FastAPI)**
  - Password hashing uses PBKDF2-HMAC-SHA256; no additional secrets required.
- **Next.js (web/.env)**
  - `NEXTAUTH_SECRET` – signing key for NextAuth JWT sessions
  - `NEXTAUTH_URL` – base URL of the Next.js app (e.g. `http://localhost:3000`)
  - `NEXT_PUBLIC_API_BASE_URL` – base URL of the FastAPI backend (defaults to `http://localhost:8000` for local dev)
- **NextAuth providers**
  - Optional Google OAuth: set `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`

## 📚 Documentation

- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [API Documentation](docs/api.md) - Complete API reference
- [Configuration](api/.env.example) - Environment variables reference
- [High Contrast Themes Improvements](high-contrast-themes-improvements.md) - Details about accessibility enhancements

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
