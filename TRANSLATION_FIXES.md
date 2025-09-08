# Translation Workflow Fixes

## Summary of Changes

Fixed the duplicate translation functions in coordinators that were overriding the actual translation service implementations.

### Issues Identified

1. Both `pdf_coordinator.py` and `slide_coordinator.py` had duplicate `_translate_scripts_step` functions that were overriding the proper translation service step implementations
2. These duplicate functions were not using the actual translation service and were causing translation workflow issues
3. The coordinators were calling these duplicate functions instead of the proper translation step functions

### Changes Made

1. **Removed duplicate `_translate_scripts_step` functions** from both coordinators:
   - Removed from `/api/slidespeaker/pipeline/pdf_coordinator.py`
   - Removed from `/api/slidespeaker/pipeline/slide_coordinator.py`

2. **Updated coordinator execution functions** to call the proper translation step functions directly:
   - In `slide_coordinator.py`: Replaced calls to `_translate_scripts_step` with direct calls to `translate_voice_scripts_step` and `translate_subtitle_scripts_step`
   - In `pdf_coordinator.py`: Replaced calls to `_translate_scripts_step` with direct calls to `translate_voice_scripts_step` and `translate_subtitle_scripts_step`

3. **Fixed type checking errors** in `server.py`:
   - Replaced incorrect `config.storage_local_path` references with `config.output_dir`

### Verification

- All code quality checks pass (linting and type checking)
- Translation workflow now properly uses the translation service implementations
- Both PPTX and PDF processing should now correctly handle translations

### How the Translation Workflow Now Works

1. **PPTX/Presentation Processing**:
   - Scripts are generated in English
   - If voice language is not English, `translate_voice_scripts_step` is called
   - If subtitle language is specified and not English, `translate_subtitle_scripts_step` is called
   - These steps use the actual `TranslationService` to perform translations
   - Translated scripts are stored in state and used by subsequent steps

2. **PDF Processing**:
   - PDF content is segmented into chapters
   - Scripts are generated in English
   - If voice language is not English, `translate_voice_scripts_step` is called
   - If subtitle language is specified and not English, `translate_subtitle_scripts_step` is called
   - These steps use the actual `TranslationService` to perform translations
   - Translated scripts are stored in state and used by subsequent steps

### Files Modified

- `/api/slidespeaker/pipeline/pdf_coordinator.py`
- `/api/slidespeaker/pipeline/slide_coordinator.py`
- `/api/server.py` (type checking fixes)