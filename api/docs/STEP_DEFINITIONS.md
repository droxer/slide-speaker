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
   - **Description**: Generates a two-person conversation script based on PDF content
   - **Input**: Chapter data from segmentation
   - **Output**: Structured conversation script with host/guest dialog
   - **Dependencies**: segment_pdf_content
   - **Status**: Always required for podcast generation

2. **translate_podcast_script** *(Optional)*
   - **Description**: Translates podcast script to target language
   - **Input**: English podcast script, target language
   - **Output**: Translated podcast script
   - **Dependencies**: generate_podcast_script
   - **Status**: Required when transcript_language != "english"

3. **generate_podcast_audio**
   - **Description**: Generates multi-voice audio from podcast script
   - **Input**: Podcast script, voice settings
   - **Output**: Multi-track audio files
   - **Dependencies**: generate_podcast_script (and translation step if applicable)
   - **Status**: Always required for podcast generation

4. **compose_podcast**
   - **Description**: Combines audio tracks into final podcast MP3
   - **Input**: Multi-track audio files
   - **Output**: Final MP3 podcast file
   - **Dependencies**: generate_podcast_audio
   - **Status**: Always required for podcast generation

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