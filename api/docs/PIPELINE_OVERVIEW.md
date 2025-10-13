# SlideSpeaker Pipeline Overview

This document provides a comprehensive overview of the SlideSpeaker processing pipeline, showing how all steps fit together to transform input files into final videos or podcasts.

## Pipeline Architecture

SlideSpeaker supports three main processing paths:
1. **PDF to Video** - Converts PDF documents into presentation videos
2. **PDF to Podcast** - Converts PDF documents into audio podcasts
3. **Slides to Video** - Converts presentation files (PPT/PPTX) into presentation videos

## Input Processing Flow

### PDF Processing Pipeline

```
Input PDF File
    ↓
[segment_pdf_content] - Analyze and segment PDF into chapters
    ↓
[revise_pdf_transcripts] - Refine chapter transcripts
    ↓
[Optional: translate_voice_transcripts] - Translate for voice generation
    ↓
[Optional: translate_subtitle_transcripts] - Translate for subtitles
    ↓
[generate_pdf_chapter_images] - Create images for each chapter
    ↓
[generate_pdf_audio] - Generate audio narration
    ↓
[Optional: generate_pdf_subtitles] - Generate subtitle files
    ↓
[compose_video] - Combine all elements into final video
```

### PDF Podcast Pipeline

```
Input PDF File
    ↓
[segment_pdf_content] - Analyze and segment PDF into chapters
    ↓
[generate_podcast_script] - Create 2-person conversation script in English
    ↓
[Optional: translate_podcast_script] - Translate script to target language if needed
    ↓
[generate_podcast_audio] - Generate multi-voice audio with host/guest voices
    ↓
[compose_podcast] - Combine audio tracks into final podcast MP3
```

The PDF podcast pipeline converts documents into engaging audio conversations:

1. **Content Segmentation**: The PDF is first analyzed and segmented into logical chapters with key points
2. **Script Generation**: A natural 2-person conversation script is generated in English, with alternating Host and Guest dialogue
3. **Translation**: If a non-English language is requested, the script is translated while preserving speaker roles
4. **Audio Generation**: Multi-voice audio is created using distinct voices for Host and Guest roles
5. **Composition**: All audio segments are combined into a single podcast MP3 file

The podcast script generation uses AI to create engaging conversations that explain complex topics clearly, avoiding references to visual elements since podcasts are audio-only.

### Slides Processing Pipeline

```
Input Presentation File (PPT/PPTX)
    ↓
[extract_slides] - Extract individual slides
    ↓
[convert_slides] - Convert slides to images
    ↓
[Optional: analyze_slides] - Analyze slide content
    ↓
[generate_transcripts] - Create transcripts for each slide
    ↓
[revise_transcripts] - Refine slide transcripts
    ↓
[Optional: translate_voice_transcripts] - Translate for voice generation
    ↓
[Optional: translate_subtitle_transcripts] - Translate for subtitles
    ↓
[generate_audio] - Generate audio narration
    ↓
[Optional: generate_avatar] - Create AI avatar videos
    ↓
[Optional: generate_subtitles] - Generate subtitle files
    ↓
[compose_video] - Combine all elements into final video
```

## State Management

Each pipeline step updates the processing state in Redis, tracking:
- Step status (pending, processing, completed, failed, skipped)
- Step output data
- Error information if applicable
- Overall task progress

## Conditional Steps

Several steps are conditionally executed based on user preferences:
- Translation steps only run when target language differs from English
- Avatar generation is optional and can be disabled
- Subtitle generation can be enabled/disabled
- Visual analysis step can be disabled via configuration

## Error Handling and Resumption

The pipeline supports:
- Automatic resumption from completed steps
- Detailed error tracking for failed steps
- Task cancellation at any point during processing
- Graceful handling of partial failures (e.g., avatar generation for some but not all slides)

## Storage and Output

Final outputs are stored in the configured storage provider:
- Videos: MP4 format with optional subtitles
- Podcasts: MP3 format
- Intermediate files: Stored locally during processing
- Metadata: Markdown transcripts and processing logs

## Task Coordination

The pipeline uses a coordinator pattern:
- Main coordinator delegates to specialized PDF/Slides/Podcast coordinators
- Each coordinator manages its specific step sequence
- State-aware processing allows for task resumption
- Real-time progress tracking through WebSocket updates