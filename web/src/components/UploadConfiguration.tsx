'use client';

import React, { useCallback, useMemo } from 'react';
import UploadPanel from '@/components/UploadPanel';
import { useI18n } from '@/i18n/hooks';
import type { UploadConfigurationProps } from './types';

export const UploadConfiguration: React.FC<UploadConfigurationProps> = ({
  uploadMode,
  setUploadMode,
  pdfOutputMode,
  setPdfOutputMode,
  file,
  onFileChange,
  voiceLanguage,
  setVoiceLanguage,
  subtitleLanguage,
  setSubtitleLanguage,
  transcriptLanguage,
  setTranscriptLanguage,
  setTranscriptLangTouched,
  videoResolution,
  setVideoResolution,
  uploading,
  onCreate,
  getFileTypeHint,
}) => {
  const { t } = useI18n();

  return (
    <UploadPanel
      uploadMode={uploadMode}
      setUploadMode={setUploadMode}
      pdfOutputMode={pdfOutputMode}
      setPdfOutputMode={setPdfOutputMode}
      file={file}
      onFileChange={onFileChange}
      voiceLanguage={voiceLanguage}
      setVoiceLanguage={setVoiceLanguage}
      subtitleLanguage={subtitleLanguage}
      setSubtitleLanguage={setSubtitleLanguage}
      transcriptLanguage={transcriptLanguage}
      setTranscriptLanguage={setTranscriptLanguage}
      setTranscriptLangTouched={setTranscriptLangTouched}
      videoResolution={videoResolution}
      setVideoResolution={setVideoResolution}
      uploading={uploading}
      onCreate={onCreate}
      getFileTypeHint={getFileTypeHint}
    />
  );
};