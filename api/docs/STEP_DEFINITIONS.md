# SlideSpeaker Pipeline Step Definitions

This document provides clear definitions for all processing steps in the SlideSpeaker pipeline, organized by processing type.

## PDF Processing Steps

### PDF Video Pipeline Steps

1. **segment_pdf_content**
   - **Description**: Analyzes and segments PDF content into logical chapters
   - **Input**: PDF file path
   - **Output**: List of chapters with titles, descriptions, key points, and scripts
   - **Dependencies**: None
   - **Status**: Always required for PDF processing

2. **revise_pdf_transcripts**
   - **Description**: Revises and refines chapter transcripts for better flow and clarity
   - **Input**: Raw chapter transcripts from segmentation step
   - **Output**: Improved chapter transcripts
   - **Dependencies**: segment_pdf_content
   - **Status**: Always required for PDF processing

3. **translate_voice_transcripts** *(Optional)*
   - **Description**: Translates voice transcripts from English to target language
   - **Input**: English transcripts, target language
   - **Output**: Translated transcripts for voice generation
   - **Dependencies**: revise_pdf_transcripts
   - **Status**: Required when voice_language != "english"

4. **translate_subtitle_transcripts** *(Optional)*
   - **Description**: Translates subtitle transcripts from English to target language
   - **Input**: English transcripts, target language
   - **Output**: Translated transcripts for subtitle generation
   - **Dependencies**: revise_pdf_transcripts
   - **Status**: Required when subtitle_language != "english"

5. **generate_pdf_chapter_images**
   - **Description**: Generates images for each PDF chapter
   - **Input**: Chapter data with descriptions
   - **Output**: Image files for each chapter
   - **Dependencies**: segment_pdf_content
   - **Status**: Required for video generation

6. **generate_pdf_audio**
   - **Description**: Generates audio narration for each chapter
   - **Input**: Chapter scripts, voice settings
   - **Output**: Audio files for each chapter
   - **Dependencies**: revise_pdf_transcripts (and translation steps if applicable)
   - **Status**: Required for video generation

7. **generate_pdf_subtitles** *(Optional)*
   - **Description**: Generates subtitle files for the video
   - **Input**: Chapter scripts, language settings
   - **Output**: SRT/VTT subtitle files
   - **Dependencies**: revise_pdf_transcripts (and translation steps if applicable)
   - **Status**: Required when generate_subtitles = True

8. **compose_video**
   - **Description**: Combines images, audio, and subtitles into final video
   - **Input**: Chapter images, audio files, subtitle files
   - **Output**: Final MP4 video file
   - **Dependencies**: generate_pdf_chapter_images, generate_pdf_audio
   - **Status**: Required for video generation

### PDF Podcast Pipeline Steps

1. **generate_podcast_script**
   - **Description**: Generates a natural two-person conversation script (Host and Guest) based on PDF chapter content
   - **Input**: Chapter data from segmentation step, including titles, descriptions, and key points
   - **Output**: Structured conversation script as a list of dialogue items: [{"speaker": "Host|Guest", "text": "..."}]
   - **Dependencies**: segment_pdf_content
   - **Status**: Always required for podcast generation
   - **Details**: Uses AI to create engaging conversations that explain complex topics clearly. Always generates in English first, avoiding references to visual elements since podcasts are audio-only.

2. **translate_podcast_script** *(Optional)*
   - **Description**: Translates the English podcast script to the target language while preserving speaker roles
   - **Input**: English podcast script, target language
   - **Output**: Translated podcast script with same structure as input
   - **Dependencies**: generate_podcast_script
   - **Status**: Required when transcript_language != "english"
   - **Details**: Maintains Host/Guest speaker labels and dialogue structure during translation

3. **generate_podcast_audio**
   - **Description**: Generates multi-voice audio from podcast script using distinct voices for Host and Guest
   - **Input**: Podcast script (translated if needed), voice language settings
   - **Output**: Individual MP3 audio segments for each dialogue line, plus metadata about selected voices
   - **Dependencies**: generate_podcast_script (and translation step if applicable)
   - **Status**: Always required for podcast generation
   - **Details**: Automatically selects appropriate voices for host/guest roles. Generates per-line audio segments that are later composed into final podcast.

4. **compose_podcast**
   - **Description**: Combines individual audio segments into a single final podcast MP3 file
   - **Input**: Individual MP3 audio segments from generate_podcast_audio step
   - **Output**: Final MP3 podcast file ready for download
   - **Dependencies**: generate_podcast_audio
   - **Status**: Always required for podcast generation
   - **Details**: Concatenates all audio segments in order and applies final processing to create the complete podcast

### Podcast Script Storage and Retrieval

The podcast script is stored in two formats for different uses:
- **Markdown Format**: `{task_id}_podcast_transcript.md` - For human-readable display in the UI
- **JSON Format**: `{task_id}_podcast_script.json` - For programmatic access via API

The script can be retrieved via the API endpoint: `GET /api/tasks/{task_id}/podcast/script`
This endpoint returns the structured dialogue data that was used for audio generation, including information about the selected host and guest voices.

## Slides Processing Steps

### Slides Video Pipeline Steps

1. **extract_slides**
   - **Description**: Extracts individual slides from presentation file
   - **Input**: PPT/PPTX file path
   - **Output**: Extracted slide data
   - **Dependencies**: None
   - **Status**: Always required for slides processing

2. **convert_slides**
   - **Description**: Converts extracted slides to image format
   - **Input**: Extracted slide data
   - **Output**: Image files for each slide
   - **Dependencies**: extract_slides
   - **Status**: Always required for slides processing

3. **analyze_slides**
   - **Description**: Analyzes slide images for content understanding
   - **Input**: Slide images
   - **Output**: Analyzed slide content data
   - **Dependencies**: convert_slides
   - **Status**: Optional (skipped when visual analysis is disabled)

4. **generate_transcripts**
   - **Description**: Generates transcripts for each slide
   - **Input**: Slide content data
   - **Output**: Slide transcripts
   - **Dependencies**: analyze_slides
   - **Status**: Always required for slides processing

5. **revise_transcripts**
   - **Description**: Revises and refines slide transcripts
   - **Input**: Raw slide transcripts
   - **Output**: Improved slide transcripts
   - **Dependencies**: generate_transcripts
   - **Status**: Always required for slides processing

6. **translate_voice_transcripts** *(Optional)*
   - **Description**: Translates voice transcripts from English to target language
   - **Input**: English transcripts, target language
   - **Output**: Translated transcripts for voice generation
   - **Dependencies**: revise_transcripts
   - **Status**: Required when voice_language != "english"

7. **translate_subtitle_transcripts** *(Optional)*
   - **Description**: Translates subtitle transcripts from English to target language
   - **Input**: English transcripts, target language
   - **Output**: Translated transcripts for subtitle generation
   - **Dependencies**: revise_transcripts
   - **Status**: Required when subtitle_language != "english"

8. **generate_audio**
   - **Description**: Generates audio narration for slides
   - **Input**: Slide transcripts, voice settings
   - **Output**: Audio files for each slide
   - **Dependencies**: revise_transcripts (and translation steps if applicable)
   - **Status**: Always required for slides processing

9. **generate_avatar** *(Optional)*
   - **Description**: Generates AI avatar videos for presentation
   - **Input**: Slide data, avatar settings
   - **Output**: Avatar video files
   - **Dependencies**: generate_transcripts
   - **Status**: Required when generate_avatar = True

10. **generate_subtitles** *(Optional)*
    - **Description**: Generates subtitle files for the video
    - **Input**: Slide transcripts, language settings
    - **Output**: SRT/VTT subtitle files
    - **Dependencies**: revise_transcripts (and translation steps if applicable)
    - **Status**: Required when generate_subtitles = True

11. **compose_video**
    - **Description**: Combines slides, audio, avatar, and subtitles into final video
    - **Input**: Slide images, audio files, avatar videos, subtitle files
    - **Output**: Final MP4 video file
    - **Dependencies**: convert_slides, generate_audio
    - **Status**: Always required for slides processing

## Common Processing Steps

These steps are used across multiple pipeline types:

### Translation Steps
- **translate_voice_transcripts**: Used in both PDF and Slides pipelines for voice translation
- **translate_subtitle_transcripts**: Used in both PDF and Slides pipelines for subtitle translation

### Audio Generation Steps
- Audio generation is handled by common modules but called from pipeline-specific steps

### Composition Steps
- Video and podcast composition steps use common underlying modules but are pipeline-specific