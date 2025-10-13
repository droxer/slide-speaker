# Podcast Filename Handling Fix

## Issue
There was an inconsistency in how podcast filenames were handled in the podcast generation pipeline:
- Local files were named `{file_id}_podcast.mp3`
- Storage files were named `{task_id}.mp3` or `{file_id}.mp3`

This inconsistency could cause confusion and potential issues with file management.

## Fix
Modified the `compose_podcast_step` function in `api/slidespeaker/pipeline/steps/podcast/pdf/compose.py` to use consistent task-first naming for both local and storage files:

1. Updated local file naming to use the same base ID as storage files
2. Consolidated the task ID resolution logic to avoid duplication
3. Ensured both local and storage filenames follow the same naming convention

## Changes Made
- Local files are now named `{base_id}.mp3` where base_id is the task_id when available, falling back to file_id
- Storage files continue to use `{base_id}.mp3` with the same base_id
- Maintained backward compatibility in routes by keeping legacy filename patterns as fallbacks

## Files Modified
- `api/slidespeaker/pipeline/steps/podcast/pdf/compose.py`