# SlideSpeaker Dataflow Documentation

This document describes the data flow for all processing pipelines in SlideSpeaker, including PDF to Video, PDF to Podcast, and Slides to Video.

## Overview

SlideSpeaker processes three types of inputs:
1. **PDF Documents** - Can generate videos or podcasts
2. **Presentation Files (PPT/PPTX)** - Generate videos only
3. **Task-based Processing** - All outputs are associated with task IDs

## 1. PDF to Video Dataflow

### Input
- PDF file with content to be converted to a presentation video

### Processing Steps
1. **PDF Segmentation**
   - Input: PDF file
   - Process: Analyze and segment PDF into logical chapters
   - Output: Chapter data (titles, descriptions, key points)

2. **Transcript Generation**
   - Input: Chapter data
   - Process: Generate initial transcripts for each chapter
   - Output: Raw chapter transcripts

3. **Transcript Revision**
   - Input: Raw transcripts
   - Process: Refine and improve transcript quality
   - Output: Revised transcripts

4. **Translation (Optional)**
   - Input: Revised transcripts, target language
   - Process: Translate transcripts for voice and/or subtitles
   - Output: Translated transcripts

5. **Image Generation**
   - Input: Chapter data
   - Process: Generate visual representations for each chapter
   - Output: Chapter images

6. **Audio Generation**
   - Input: Revised/translated transcripts, voice settings
   - Process: Generate text-to-speech audio for each chapter
   - Output: Chapter audio files

7. **Subtitle Generation (Optional)**
   - Input: Revised/translated transcripts, language settings
   - Process: Generate subtitle files (VTT/SRT)
   - Output: Subtitle files

8. **Video Composition**
   - Input: Chapter images, audio files, subtitle files
   - Process: Combine all elements into final video
   - Output: Final MP4 video file

### Output Files
- `{task_id}.mp4` - Final video
- `{task_id}_{language}.vtt` - Video subtitles (optional)
- `{task_id}_{language}.srt` - Video subtitles (optional)
- `{task_id}_transcript.md` - Video transcript

## 2. PDF to Podcast Dataflow

### Input
- PDF file with content to be converted to an audio podcast

### Processing Steps
1. **PDF Segmentation**
   - Input: PDF file
   - Process: Analyze and segment PDF into logical chapters
   - Output: Chapter data (titles, descriptions, key points)

2. **Podcast Script Generation**
   - Input: Chapter data
   - Process: Generate 2-person conversation script in English
   - Output: Structured dialogue: [{"speaker": "Host|Guest", "text": "..."}]

3. **Podcast Script Translation (Optional)**
   - Input: English podcast script, target language
   - Process: Translate script while preserving speaker roles
   - Output: Translated podcast script

4. **Podcast Audio Generation**
   - Input: Podcast script (translated if needed), voice settings
   - Process: Generate multi-voice audio with distinct host/guest voices
   - Output: Individual MP3 segments for each dialogue line

5. **Podcast Composition**
   - Input: Individual audio segments
   - Process: Combine all segments into final podcast
   - Output: Final MP3 podcast file

### Output Files
- `{task_id}.mp3` - Final podcast
- `{task_id}_podcast_transcript.md` - Podcast transcript
- `{task_id}_podcast_script.json` - Structured podcast dialogue

## 3. Slides to Video Dataflow

### Input
- Presentation file (PPT/PPTX) to be converted to a presentation video

### Processing Steps
1. **Slide Extraction**
   - Input: Presentation file
   - Process: Extract individual slides
   - Output: Slide data

2. **Slide Conversion**
   - Input: Slide data
   - Process: Convert slides to image format
   - Output: Slide images

3. **Slide Analysis (Optional)**
   - Input: Slide images
   - Process: Analyze visual content using AI
   - Output: Analyzed slide content

4. **Transcript Generation**
   - Input: Analyzed slide content
   - Process: Generate transcripts for each slide
   - Output: Slide transcripts

5. **Transcript Revision**
   - Input: Raw transcripts
   - Process: Refine and improve transcript quality
   - Output: Revised transcripts

6. **Translation (Optional)**
   - Input: Revised transcripts, target language
   - Process: Translate transcripts for voice and/or subtitles
   - Output: Translated transcripts

7. **Audio Generation**
   - Input: Revised/translated transcripts, voice settings
   - Process: Generate text-to-speech audio for each slide
   - Output: Slide audio files

8. **Avatar Generation (Optional)**
   - Input: Slide data, avatar settings
   - Process: Generate AI avatar videos
   - Output: Avatar video files

9. **Subtitle Generation (Optional)**
   - Input: Revised/translated transcripts, language settings
   - Process: Generate subtitle files (VTT/SRT)
   - Output: Subtitle files

10. **Video Composition**
    - Input: Slide images, audio files, avatar videos, subtitle files
    - Process: Combine all elements into final video
    - Output: Final MP4 video file

### Output Files
- `{task_id}.mp4` - Final video
- `{task_id}_{language}.vtt` - Video subtitles (optional)
- `{task_id}_{language}.srt` - Video subtitles (optional)
- `{task_id}_transcript.md` - Video transcript

## Task State Management

All processing steps update the task state in Redis:
- Step status (pending, processing, completed, failed, skipped)
- Step output data
- Error information if applicable
- Overall task progress

## Storage System

Files are stored using a unified storage system:
- **Local Filesystem**: Default option in `output/` directory
- **AWS S3**: Cloud storage option
- **Aliyun OSS**: Alternative cloud storage option

Filename conventions:
- `{task_id}.mp4` - Final video
- `{task_id}.mp3` - Final podcast
- `{task_id}_{language}.vtt|srt` - Subtitle files
- `{task_id}_transcript.md` - Transcripts
- `{task_id}_podcast_script.json` - Podcast scripts

## API Endpoints

Task-based endpoints for accessing outputs:
- `GET /api/tasks/{task_id}/video` - Download final video
- `GET /api/tasks/{task_id}/audio` - Download final audio
- `GET /api/tasks/{task_id}/podcast` - Download final podcast
- `GET /api/tasks/{task_id}/subtitles/vtt` - Download VTT subtitles
- `GET /api/tasks/{task_id}/subtitles/srt` - Download SRT subtitles
- `GET /api/tasks/{task_id}/podcast/script` - Get podcast script

## Error Handling

Each step includes error handling:
- Detailed error tracking for failed steps
- Task cancellation at any point during processing
- Graceful handling of partial failures
- Automatic retry mechanisms where appropriate