import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.scss';

// Constants for local storage keys
const LOCAL_STORAGE_KEYS = {
  TASK_STATE: 'slidespeaker_task_state',
  FILE_ID: 'slidespeaker_file_id',
  TASK_ID: 'slidespeaker_task_id',
  STATUS: 'slidespeaker_status',
  PROCESSING_DETAILS: 'slidespeaker_processing_details',
  LATEST_TASK_TIMESTAMP: 'slidespeaker_latest_task_timestamp'
};

// Define TypeScript interfaces
interface StepDetails {
  status: string;
  data?: any;
}

interface ProcessingError {
  step: string;
  error: string;
  timestamp: string;
}

interface ProcessingDetails {
  status: string;
  progress: number;
  current_step: string;
  steps: Record<string, StepDetails>;
  errors: ProcessingError[];
  audio_language?: string;
  subtitle_language?: string;
  created_at: string;
  updated_at: string;
}

type AppStatus = 'idle' | 'uploading' | 'processing' | 'completed' | 'error';

// Local storage utility functions
const localStorageUtils = {
  saveTaskState: (state: {
    fileId: string | null;
    taskId: string | null;
    status: AppStatus;
    processingDetails: ProcessingDetails | null;
    language: string;
    subtitleLanguage: string;
    generateAvatar: boolean;
    generateSubtitles: boolean;
  }) => {
    try {
      const stateToSave = {
        ...state,
        timestamp: new Date().toISOString()
      };
      localStorage.setItem(LOCAL_STORAGE_KEYS.TASK_STATE, JSON.stringify(stateToSave));
      localStorage.setItem(LOCAL_STORAGE_KEYS.LATEST_TASK_TIMESTAMP, new Date().toISOString());
    } catch (error) {
      console.warn('Failed to save task state to local storage:', error);
    }
  },

  loadTaskState: () => {
    try {
      const savedState = localStorage.getItem(LOCAL_STORAGE_KEYS.TASK_STATE);
      if (savedState) {
        const parsed = JSON.parse(savedState);
        // Validate the timestamp to ensure it's recent (within 24 hours)
        const timestamp = new Date(parsed.timestamp);
        const now = new Date();
        const hoursDiff = (now.getTime() - timestamp.getTime()) / (1000 * 60 * 60);
        
        if (hoursDiff < 24) {
          return parsed;
        } else {
          // Clean up old data
          localStorageUtils.clearTaskState();
          return null;
        }
      }
      return null;
    } catch (error) {
      console.warn('Failed to load task state from local storage:', error);
      return null;
    }
  },

  clearTaskState: () => {
    try {
      Object.values(LOCAL_STORAGE_KEYS).forEach(key => {
        localStorage.removeItem(key);
      });
    } catch (error) {
      console.warn('Failed to clear task state from local storage:', error);
    }
  },

  saveFileId: (fileId: string) => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEYS.FILE_ID, fileId);
    } catch (error) {
      console.warn('Failed to save file ID to local storage:', error);
    }
  },

  loadFileId: (): string | null => {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.FILE_ID);
    } catch (error) {
      console.warn('Failed to load file ID from local storage:', error);
      return null;
    }
  },

  saveTaskId: (taskId: string) => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEYS.TASK_ID, taskId);
    } catch (error) {
      console.warn('Failed to save task ID to local storage:', error);
    }
  },

  loadTaskId: (): string | null => {
    try {
      return localStorage.getItem(LOCAL_STORAGE_KEYS.TASK_ID);
    } catch (error) {
      console.warn('Failed to load task ID from local storage:', error);
      return null;
    }
  }
};

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [fileId, setFileId] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<AppStatus>('idle');
  const [progress, setProgress] = useState<number>(0);
  const [processingDetails, setProcessingDetails] = useState<ProcessingDetails | null>(null);
  const [language, setLanguage] = useState<string>('english');
  const [subtitleLanguage, setSubtitleLanguage] = useState<string>('english');
  const [generateAvatar, setGenerateAvatar] = useState<boolean>(false);
  const [generateSubtitles, setGenerateSubtitles] = useState<boolean>(true);
  const [isResumingTask, setIsResumingTask] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const ext = selectedFile.name.toLowerCase().split('.').pop();
      if (ext && ['pdf', 'pptx', 'ppt'].includes(ext)) {
        setFile(selectedFile);
      } else {
        alert('Please select a PDF or PowerPoint file');
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    
    setUploading(true);
    setStatus('uploading');
    
    try {
      // Read file as array buffer for base64 encoding
      const arrayBuffer = await file.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      const base64File = btoa(String.fromCharCode.apply(null, Array.from(uint8Array)));
      
      // Send as JSON
      const response = await axios.post('/api/upload', 
        {
          filename: file.name,
          file_data: base64File,
          language: language,
          subtitle_language: subtitleLanguage,
          generate_avatar: generateAvatar,
          generate_subtitles: generateSubtitles
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const percentCompleted = Math.round(
                (progressEvent.loaded * 100) / progressEvent.total
              );
              setProgress(percentCompleted);
            }
          },
        }
      );
      
      setFileId(response.data.file_id);
      setTaskId(response.data.task_id);
      setStatus('processing');
      setProgress(0);
      
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
      setUploading(false);
      setStatus('idle');
    }
  };

  const handleStopProcessing = async () => {
    if (!taskId) return;
    
    try {
      const response = await axios.post<{ message: string }>(`/api/task/${taskId}/cancel`);
      console.log('Stop processing response:', response.data);
      alert('Processing has been stopped.');
      setStatus('idle');
      setUploading(false);
      setProgress(0);
      setProcessingDetails(null);
      setTaskId(null);
    } catch (error) {
      console.error('Stop processing error:', error);
      alert('Failed to stop processing. The task may have already completed or failed.');
    }
  };

  const downloadVideo = () => {
    if (fileId) {
      // Create a temporary link element
      const link = document.createElement('a');
      link.href = `/api/video/${fileId}`;
      link.download = `presentation_${fileId}.mp4`;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      alert('Video not available for download. Please try again.');
    }
  };

  const resetForm = () => {
    setFile(null);
    setFileId(null);
    setTaskId(null);
    setStatus('idle');
    setUploading(false);
    setProgress(0);
    setProcessingDetails(null);
    // Keep the current subtitle language selection
    setGenerateAvatar(false);
    setGenerateSubtitles(true);
    if (videoRef.current) {
      videoRef.current.src = '';
    }
    
    // Clear local storage
    localStorageUtils.clearTaskState();
  };

  // Load saved task state on component mount
  useEffect(() => {
    const loadSavedState = async () => {
      const savedState = localStorageUtils.loadTaskState();
      if (savedState) {
        setIsResumingTask(true);
        
        // Restore the saved state
        setFileId(savedState.fileId);
        setTaskId(savedState.taskId);
        setStatus(savedState.status);
        setProgress(savedState.processingDetails?.progress || 0);
        setProcessingDetails(savedState.processingDetails);
        setLanguage(savedState.language);
        setSubtitleLanguage(savedState.subtitleLanguage);
        setGenerateAvatar(savedState.generateAvatar);
        setGenerateSubtitles(savedState.generateSubtitles);
        
        console.log('Resuming task from local storage:', {
          fileId: savedState.fileId,
          taskId: savedState.taskId,
          status: savedState.status
        });
        
        setIsResumingTask(false);
      }
    };

    loadSavedState();
  }, []);

  // Save task state to local storage whenever relevant state changes
  useEffect(() => {
    if (status !== 'idle' && !isResumingTask) {
      localStorageUtils.saveTaskState({
        fileId,
        taskId,
        status,
        processingDetails,
        language,
        subtitleLanguage,
        generateAvatar,
        generateSubtitles
      });
    }
  }, [
    fileId,
    taskId,
    status,
    processingDetails,
    language,
    subtitleLanguage,
    generateAvatar,
    generateSubtitles,
    isResumingTask
  ]);

  // Poll for status updates when processing
  useEffect(() => {
    let intervalId: NodeJS.Timeout | null = null;
    
    if (status === 'processing' && fileId) {
      const checkStatus = async () => {
        try {
          const response = await axios.get<ProcessingDetails>(`/api/progress/${fileId}`);
          setProcessingDetails(response.data);
          
          if (response.data.status === 'completed') {
            setStatus('completed');
            setUploading(false);
            setProgress(100);
            setTaskId(null);
            
            // Clear local storage when completed
            localStorageUtils.clearTaskState();
            
          } else if (response.data.status === 'processing' || response.data.status === 'uploaded') {
            setStatus('processing');
            setProgress(response.data.progress);
          } else if (response.data.status === 'failed') {
            setStatus('error');
            setUploading(false);
            setTaskId(null);
            
            // Clear local storage when failed
            localStorageUtils.clearTaskState();
          } else {
            setStatus('error');
            setUploading(false);
            setTaskId(null);
            
            // Clear local storage when error
            localStorageUtils.clearTaskState();
          }
        } catch (error) {
          console.error('Status check error:', error);
          setStatus('error');
          setUploading(false);
          
          // Clear local storage on error
          localStorageUtils.clearTaskState();
        }
      };
      
      // Check status immediately
      checkStatus();
      
      // Set up interval to check status every 10 seconds
      intervalId = setInterval(checkStatus, 10000);
    }
    
    // Cleanup function to clear interval
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [status, fileId]);

  // Add subtitle tracks when video is loaded
  useEffect(() => {
    if (status === 'completed' && generateSubtitles && fileId && videoRef.current) {
      const addSubtitles = () => {
        if (videoRef.current) {
          // Remove existing tracks
          const existingTracks = videoRef.current.querySelectorAll('track');
          existingTracks.forEach(track => track.remove());
          
          // Ensure video has loaded metadata before adding track
          if (videoRef.current.readyState === 0) {
            console.log('Video not ready, waiting for metadata...');
            return;
          }
          
          // Add VTT subtitle track if subtitles are enabled
          const track = document.createElement('track');
          track.kind = 'subtitles';
          track.src = `/api/subtitles/${fileId}/vtt`;
          track.setAttribute('srclang', subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 
                         subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : 
                         subtitleLanguage === 'japanese' ? 'ja' : 
                         subtitleLanguage === 'korean' ? 'ko' : 
                         subtitleLanguage === 'thai' ? 'th' : 'en');
          track.label = getLanguageDisplayName(subtitleLanguage);
          track.default = true;
          
          track.addEventListener('load', () => {
            console.log('Subtitle track loaded successfully');
            if (videoRef.current && videoRef.current.textTracks.length > 0) {
              const textTrack = videoRef.current.textTracks[0];
              textTrack.mode = 'showing';
              console.log('Subtitles are now showing');
            }
          });
          
          track.addEventListener('error', (e) => {
            console.error('Subtitle track loading error:', e);
            // Fallback: try loading with absolute URL
            const absoluteUrl = `${window.location.origin}/api/subtitles/${fileId}/vtt`;
            console.log('Trying absolute URL:', absoluteUrl);
            track.src = absoluteUrl;
          });
          
          videoRef.current.appendChild(track);
          
          // Force reload if track fails
          setTimeout(() => {
            if (videoRef.current && videoRef.current.textTracks.length === 0) {
              console.log('Retrying subtitle loading...');
              const retryTrack = document.createElement('track');
              retryTrack.kind = 'subtitles';
              retryTrack.src = `${window.location.origin}/api/subtitles/${fileId}/vtt`;
              retryTrack.setAttribute('srclang', subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 'en');
              retryTrack.label = 'Subtitles';
              retryTrack.default = true;
              videoRef.current.appendChild(retryTrack);
            }
          }, 1000);
        }
      };
      
      // Wait for video to be fully loaded
      const handleLoadedMetadata = () => {
        console.log('Video metadata loaded, adding subtitles...');
        addSubtitles();
      };
      
      if (videoRef.current.readyState >= 1) {
        // Metadata already loaded
        addSubtitles();
      } else {
        // Wait for metadata to load
        videoRef.current.addEventListener('loadedmetadata', handleLoadedMetadata, { once: true });
        videoRef.current.addEventListener('loadeddata', addSubtitles, { once: true });
      }
    }
  }, [status, generateSubtitles, subtitleLanguage, fileId]);

  const formatStepName = (step: string): string => {
    const stepNames: Record<string, string> = {
      'extract_slides': 'Extracting Content',
      'analyze_slide_images': 'Analyzing Visuals',
      'generate_scripts': 'Creating Narratives',
      'review_scripts': 'Refining Content',
      'generate_subtitle_scripts': 'Generating subtitle narratives',
      'review_subtitle_scripts': 'Reviewing subtitle scripts',
      'generate_audio': 'Synthesizing Audio',
      'generate_avatar_videos': 'Generating Avatars',
      'convert_slides_to_images': 'Converting Slides',
      'generate_subtitles': 'Generating subtitles',
      'compose_video': 'Composing Video',
      'unknown': 'Initializing'
    };
    return stepNames[step] || step;
  };

  const getLanguageDisplayName = (languageCode: string): string => {
    const languageNames: Record<string, string> = {
      'english': 'English',
      'simplified_chinese': '简体中文',
      'traditional_chinese': '繁體中文',
      'japanese': '日本語',
      'korean': '한국어',
      'thai': 'ไทย'
    };
    return languageNames[languageCode] || languageCode;
  };

  const getProcessingStatusMessage = (): string => {
    if (!processingDetails) return 'Bringing Your Presentation to Life';
    
    const activeSteps = Object.entries(processingDetails.steps || {})
      .filter(([_, step]) => step.status === 'processing');
    
    if (activeSteps.length > 0) {
      const stepName = formatStepName(activeSteps[0][0]);
      const statusMessages: Record<string, string> = {
        'Extracting Content': 'Analyzing your presentation structure...',
        'Analyzing Visuals': 'Examining slide visuals and content...',
        'Creating Narratives': 'Crafting engaging AI narratives...',
        'Refining Content': 'Polishing the script for perfect delivery...',
        'Generating subtitle narratives': 'Creating subtitle translations...',
        'Reviewing subtitle scripts': 'Perfecting subtitle timing and accuracy...',
        'Synthesizing Audio': 'Creating natural voice narration...',
        'Generating Avatars': 'Bringing AI presenters to life...',
        'Converting Slides': 'Preparing slides for video composition...',
        'Composing Video': 'Assembling your final masterpiece...'
      };
      return statusMessages[stepName] || `Working on: ${stepName}`;
    }
    
    return 'Bringing Your Presentation to Life';
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>SlideSpeaker AI</h1>
        <p>Transform slides into AI-powered videos</p>
      </header>

      <main className="main-content">
        <div className="card-container">
          <div className={`content-card ${status === 'completed' ? 'wide' : ''}`}>
            {status === 'idle' && (
              <div className="upload-view">
                {isResumingTask && (
                  <div className="resume-indicator">
                    <div className="spinner"></div>
                    <p>Resuming your last task...</p>
                  </div>
                )}
                
                <div className="file-upload-area">
                  <input
                    type="file"
                    id="file-upload"
                    accept=".pdf,.pptx,.ppt"
                    onChange={handleFileChange}
                    className="file-input"
                    disabled={isResumingTask}
                  />
                  <label htmlFor="file-upload" className={`file-upload-label ${isResumingTask ? 'disabled' : ''}`}>
                    <div className="upload-icon">📄</div>
                    <div className="upload-text">
                      {file ? file.name : 'Choose a file'}
                    </div>
                    <div className="upload-hint">
                      Supports PDF, PPTX, and PPT files
                    </div>
                  </label>
                </div>
                
                <div className="language-section">
                  <h3 className="language-section-title">Language Settings</h3>
                  <div className="language-group">
                    <div className="language-selector">
                      <label htmlFor="language-select">Audio Language</label>
                      <select 
                        id="language-select" 
                        value={language} 
                        onChange={(e) => setLanguage(e.target.value)}
                        className="language-select"
                      >
                        <option value="english">English</option>
                        <option value="simplified_chinese">简体中文 (Simplified Chinese)</option>
                        <option value="traditional_chinese">繁體中文 (Traditional Chinese)</option>
                        <option value="japanese">日本語 (Japanese)</option>
                        <option value="korean">한국어 (Korean)</option>
                        <option value="thai">ไทย (Thai)</option>
                      </select>
                    </div>
                    
                    <div className="language-selector">
                      <label htmlFor="subtitle-language-select">Subtitle Language</label>
                      <select 
                        id="subtitle-language-select" 
                        value={subtitleLanguage} 
                        onChange={(e) => setSubtitleLanguage(e.target.value)}
                        className="language-select"
                      >
                        <option value="english">English</option>
                        <option value="simplified_chinese">简体中文 (Simplified Chinese)</option>
                        <option value="traditional_chinese">繁體中文 (Traditional Chinese)</option>
                        <option value="japanese">日本語 (Japanese)</option>
                        <option value="korean">한국어 (Korean)</option>
                        <option value="thai">ไทย (Thai)</option>
                      </select>
                    </div>
                  </div>
                </div>
                
                <div className="option-item minimal">
                  <input
                    type="checkbox"
                    id="generate-avatar"
                    checked={generateAvatar}
                    onChange={(e) => setGenerateAvatar(e.target.checked)}
                  />
                  <label htmlFor="generate-avatar" className="minimal-label">AI Avatar</label>
                </div>
                
                {/* Subtle AI Disclaimer in Upload View */}
                <div className="ai-notice-subtle">
                  AI-generated content may contain inaccuracies. Review carefully.
                </div>
                
                {file && (
                  <button 
                    onClick={handleUpload} 
                    className="primary-btn"
                    disabled={uploading}
                  >
                    Transform to AI Magic
                  </button>
                )}
              </div>
            )}

            {status === 'uploading' && (
              <div className="processing-view">
                <div className="spinner"></div>
                <h3>Uploading Your Presentation</h3>
                <div className="progress-container">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                  <p className="progress-text">{progress}% Uploaded</p>
                  <p className="processing-status">
                    Preparing your content for AI transformation...
                  </p>
                </div>
              </div>
            )}

            {status === 'processing' && (
              <div className="processing-view">
                <div className="spinner"></div>
                <h3>{getProcessingStatusMessage()}</h3>
                <div className="progress-container">
                  <div className="progress-bar">
                    <div 
                      className="progress-fill" 
                      style={{ width: `${progress}%` }}
                    ></div>
                  </div>
                </div>
                       
                <button 
                  onClick={handleStopProcessing} 
                  className="stop-btn"
                >
                  Stop Processing
                </button>
         
                
                {processingDetails && (
                  <div className="steps-container">
                    <h4>Processing Steps</h4>
                    <div className="steps-grid">
                      {[
                        'extract_slides',
                        'convert_slides_to_images', 
                        'analyze_slide_images',
                        'generate_scripts',
                        'review_scripts',
                        'generate_audio',
                        'generate_avatar_videos',
                        'generate_subtitles',
                        'compose_video'
                      ].map((stepName) => {
                        const stepData = processingDetails.steps[stepName] || { status: 'pending' };
                        // Hide skipped steps from UI
                        if (stepData.status === 'skipped') {
                          return null;
                        }
                        return (
                          <div key={stepName} className={`step-item ${stepData.status}`}>
                            <span className="step-icon">
                              {stepData.status === 'completed' ? '✓' : 
                               stepData.status === 'processing' ? '⏳' : 
                               stepData.status === 'failed' ? '✗' : '○'}
                            </span>
                            <span className="step-name">{formatStepName(stepName)}</span>
                          </div>
                        );
                      }).filter(Boolean)}
                    </div>
                    
                    {processingDetails.errors && processingDetails.errors.length > 0 && (
                      <div className="error-section">
                        <h4>Errors Encountered</h4>
                        <div className="error-list">
                          {processingDetails.errors.map((error, index) => (
                            <div key={index} className="error-item">
                              <strong>{formatStepName(error.step)}:</strong> {error.error}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {status === 'completed' && (
              <div className="completed-view">
                <div className="success-icon">✓</div>
                <h3>Your AI Presentation is Ready!</h3>
                <p className="success-message">Congratulations! Your presentation has been transformed into an engaging AI-powered video.</p>
                
                <div className="preview-container">
                  <div className="video-main">
                    <div className="video-wrapper">
                      <video 
                        ref={videoRef}
                        controls
                        src={`/api/video/${fileId}`}
                        className="preview-video-large"
                      >
                        {/* Video tracks will be added dynamically via useEffect */}
                      </video>
                    </div>
                    <div className="preview-info-compact">
                      <div className="info-grid">
                        <div className="info-item">
                          <span className="info-label">Audio Language:</span>
                          <span className="info-value">{processingDetails?.audio_language ? getLanguageDisplayName(processingDetails.audio_language) : 'English'}</span>
                        </div>
                        <div className="info-item">
                          <span className="info-label">Subtitle Language:</span>
                          <span className="info-value">{processingDetails?.subtitle_language ? getLanguageDisplayName(processingDetails.subtitle_language) : 'English'}</span>
                        </div>
                        <div className="info-item">
                          <span className="info-label">AI Avatar:</span>
                          <span className="info-value">{generateAvatar ? '✓ Generated' : '✗ Disabled'}</span>
                        </div>
                        <div className="info-item">
                          <span className="info-label">Subtitles:</span>
                          <span className="info-value">{generateSubtitles ? '✓ Enabled' : '✗ Disabled'}</span>
                        </div>
                      </div>
                      
                      {/* Resource URLs */}
                      <div className="resource-links">
                        <div className="url-copy-row">
                          <span className="resource-label-inline">Video</span>
                          <input 
                            type="text" 
                            value={`${window.location.origin}/api/video/${fileId}`}
                            readOnly 
                            className="url-input-enhanced"
                          />
                          <button 
                            onClick={() => {
                              navigator.clipboard.writeText(`${window.location.origin}/api/video/${fileId}`);
                              alert('Video URL copied!');
                            }}
                            className="copy-btn-enhanced"
                          >
                            Copy
                          </button>
                        </div>
                        
                        {generateSubtitles && fileId && (
                          <>
                            <div className="url-copy-row">
                              <span className="resource-label-inline">SRT</span>
                              <input 
                                type="text" 
                                value={`${window.location.origin}/api/subtitles/${fileId}/srt`}
                                readOnly 
                                className="url-input-enhanced"
                              />
                              <button 
                                onClick={() => {
                                  navigator.clipboard.writeText(`${window.location.origin}/api/subtitles/${fileId}/srt`);
                                  alert('SRT URL copied!');
                                }}
                                className="copy-btn-enhanced"
                              >
                                Copy
                              </button>
                            </div>
                            
                            <div className="url-copy-row">
                              <span className="resource-label-inline">VTT</span>
                              <input 
                                type="text" 
                                value={`${window.location.origin}/api/subtitles/${fileId}/vtt`}
                                readOnly 
                                className="url-input-enhanced"
                              />
                              <button 
                                onClick={() => {
                                  navigator.clipboard.writeText(`${window.location.origin}/api/subtitles/${fileId}/vtt`);
                                  alert('VTT URL copied!');
                                }}
                                className="copy-btn-enhanced"
                              >
                                Copy
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="action-buttons">
                  <button onClick={resetForm} className="primary-btn create-new-btn">
                    Create New Video
                  </button>
                </div>
              </div>
            )}

            {status === 'error' && (
              <div className="error-view">
                <div className="error-icon">⚠️</div>
                <h3>Processing Failed</h3>
                <p className="error-message">Something went wrong during video generation. Please try again with a different file.</p>
                <button onClick={resetForm} className="primary-btn">
                  Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Powered by SlideSpeaker AI • Where presentations meet AI magic</p>
      </footer>
    </div>
  );
}

export default App;