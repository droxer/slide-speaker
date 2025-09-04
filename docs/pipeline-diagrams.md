# Pipeline Diagrams

## Overview

SlideSpeaker processes presentations through a series of well-defined steps, each responsible for a specific aspect of transforming slides into an engaging video presentation. The pipeline is designed to be resilient, allowing processing to resume from the last completed step in case of failures.

## Complete Processing Pipeline

```mermaid
graph TD
    A[User Uploads Presentation] --> B[Extract Slides]
    B --> C[Convert Slides to Images]
    C --> D[Analyze Slide Images]
    D --> E[Generate AI Narratives]
    E --> F[Review and Refine Scripts]
    
    F --> G{Subtitle Language Different?}
    G -->|Yes| H[Generate Subtitle Scripts]
    H --> I[Review Subtitle Scripts]
    G -->|No| J[Generate Audio]
    I --> J
    
    J --> K{Generate Avatar?}
    K -->|Yes| L[Generate AI Avatar Videos]
    K -->|No| M[Generate Subtitles]
    L --> M
    
    M --> N[Compose Final Video]
    N --> O[Processing Complete]
    
    style A fill:#e1f5fe
    style O fill:#c8e6c9
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#f3e5f5
    style F fill:#f3e5f5
    style H fill:#f3e5f5
    style I fill:#f3e5f5
    style J fill:#e8f5e8
    style L fill:#e8f5e8
    style M fill:#fce4ec
    style N fill:#fce4ec
```

## Detailed Step-by-Step Pipeline

### 1. Extract Slides
Extracts content from PDF or PowerPoint presentations.
- Input: Original presentation file
- Output: Structured slide data with text content

### 2. Convert Slides to Images
Converts each slide to high-quality image format for processing.
- Input: Structured slide data
- Output: Image files for each slide

### 3. Analyze Slide Images
Uses AI to analyze visual content in slides.
- Input: Slide images
- Output: Visual content descriptions and metadata

### 4. Generate AI Narratives
Creates AI-generated scripts for each slide.
- Input: Slide content and visual analysis
- Output: Narration scripts in selected language

### 5. Review and Refine Scripts
Reviews and refines scripts for consistency and quality.
- Input: Initial narration scripts
- Output: Polished narration scripts

### 6. Generate Subtitle Scripts (Conditional)
Creates scripts for subtitles when subtitle language differs from audio language.
- Input: Slide content and visual analysis
- Output: Subtitle scripts in selected language

### 7. Review Subtitle Scripts (Conditional)
Reviews and refines subtitle scripts for consistency.
- Input: Initial subtitle scripts
- Output: Polished subtitle scripts

### 8. Generate Audio
Synthesizes voice audio from narration scripts.
- Input: Polished narration scripts
- Output: Audio files for each slide

### 9. Generate AI Avatar Videos (Conditional)
Creates AI avatar videos synchronized with audio.
- Input: Audio files
- Output: Avatar video clips for each slide

### 10. Generate Subtitles
Creates subtitle files in selected language.
- Input: Script content
- Output: SRT and VTT subtitle files

### 11. Compose Final Video
Combines all elements into the final presentation video.
- Input: Slide images, audio files, avatar videos, subtitles
- Output: Complete presentation video

## Task Processing Architecture

```mermaid
graph LR
    A[Web Client] -->|HTTP Request| B[API Server]
    B --> C[Redis Task Queue]
    C --> D[Master Worker]
    D --> E[Worker Process 1]
    D --> F[Worker Process 2]
    D --> G[Worker Process N]
    
    E --> H[External APIs]
    F --> H
    G --> H
    
    H --> I[OpenAI/Qwen/ElevenLabs/HeyGen/DALL-E]
    
    style A fill:#bbdefb
    style B fill:#e3f2fd
    style C fill:#f3e5f5
    style D fill:#e8f5e8
    style E fill:#fff3e0
    style F fill:#fff3e0
    style G fill:#fff3e0
    style H fill:#fce4ec
    style I fill:#c8e6c9
```

## Error Handling and Recovery

```mermaid
graph TD
    A[Processing Step] --> B{Step Successful?}
    B -->|Yes| C[Continue to Next Step]
    B -->|No| D[Log Error]
    D --> E[Update Task Status]
    E --> F{Retry Possible?}
    F -->|Yes| G[Queue for Retry]
    F -->|No| H[Mark as Failed]
    G --> A
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#c8e6c9
    style D fill:#ffebee
    style E fill:#ffebee
    style F fill:#fff3e0
    style G fill:#e3f2fd
    style H fill:#ffcdd2
```

## Service Configuration Options

The pipeline now supports multiple AI service providers, allowing users to mix and match based on their preferences and API key availability:

### Script Generation Services
- **OpenAI**: GPT models for high-quality script generation
- **Qwen**: Alibaba's Qwen model, particularly effective for Chinese content

### Text-to-Speech Services  
- **OpenAI TTS**: Uses the same OpenAI API key for voice synthesis
- **ElevenLabs**: Premium voices with high quality
- **Local TTS**: Fallback option using local text-to-speech engines

### Avatar Generation Services
- **HeyGen**: Realistic AI presenters with natural movements
- **DALL-E**: Custom AI-generated avatars using OpenAI's image generation

## Memory-Optimized Video Composition

```mermaid
flowchart TD
    A[Start Video Composition] --> B[Validate Avatar Videos]
    B --> C[Calculate Memory Requirements]
    C --> D[Process Slide 1]
    D --> E{More Slides?}
    E -->|Yes| F[Cleanup Resources]
    F --> G[Process Next Slide]
    G --> E
    E -->|No| H[Finalize Video]
    H --> I[Complete]
    
    style A fill:#e3f2fd
    style B fill:#fff3e0
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#fff3e0
    style F fill:#ffebee
    style G fill:#e8f5e8
    style H fill:#e8f5e8
    style I fill:#c8e6c9
```

## Cancellation Flow

```mermaid
graph TD
    A[User Requests Cancellation] --> B[Update Task Status]
    B --> C[Set Cancellation Flag]
    C --> D[Notify Worker]
    D --> E{Worker State}
    E -->|Processing Step| F[Stop at Next Checkpoint]
    E -->|In Queue| G[Remove from Queue]
    F --> H[Cleanup Resources]
    G --> H
    H --> I[Mark as Cancelled]
    
    style A fill:#bbdefb
    style B fill:#e3f2fd
    style C fill:#e3f2fd
    style D fill:#f3e5f5
    style E fill:#fff3e0
    style F fill:#ffebee
    style G fill:#ffebee
    style H fill:#ffebee
    style I fill:#c8e6c9
```