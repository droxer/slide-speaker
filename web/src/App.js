import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [fileId, setFileId] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [processingDetails, setProcessingDetails] = useState(null);
  const [language, setLanguage] = useState('english');
  const [subtitleLanguage, setSubtitleLanguage] = useState('english');
  const [generateAvatar, setGenerateAvatar] = useState(false);
  const [generateSubtitles, setGenerateSubtitles] = useState(false);
  const videoRef = useRef(null);
  
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const ext = selectedFile.name.toLowerCase().split('.').pop();
      if (['pdf', 'pptx', 'ppt'].includes(ext)) {
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
      const base64File = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
      
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
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setProgress(percentCompleted);
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
      const response = await axios.post(`/api/task/${taskId}/cancel`);
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
    setGenerateSubtitles(false);
    if (videoRef.current) {
      videoRef.current.src = '';
    }
  };

  // Poll for status updates when processing
  useEffect(() => {
    let intervalId = null;
    
    if (status === 'processing' && fileId) {
      const checkStatus = async () => {
        try {
          const response = await axios.get(`/api/progress/${fileId}`);
          setProcessingDetails(response.data);
          
          if (response.data.status === 'completed') {
            setStatus('completed');
            setUploading(false);
            setProgress(100);
            setTaskId(null); // Clear task ID when completed
            
            // Preview data is no longer needed for client-side popup approach
          } else if (response.data.status === 'processing' || response.data.status === 'uploaded') {
            setStatus('processing');
            setProgress(response.data.progress);
          } else if (response.data.status === 'failed') {
            setStatus('error');
            setUploading(false);
            setTaskId(null); // Clear task ID when failed
          } else {
            setStatus('error');
            setUploading(false);
            setTaskId(null); // Clear task ID when error
          }
        } catch (error) {
          console.error('Status check error:', error);
          setStatus('error');
          setUploading(false);
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
    if (status === 'completed' && generateSubtitles && videoRef.current) {
      const addSubtitles = () => {
        if (videoRef.current) {
          // Remove existing tracks
          const existingTracks = videoRef.current.querySelectorAll('track');
          existingTracks.forEach(track => track.remove());
          
          // Add VTT subtitle track if subtitles are enabled
          const track = document.createElement('track');
          track.kind = 'subtitles';
          track.src = `/api/subtitles/${fileId}/vtt`;
          track.srcLang = subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 
                         subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : 
                         subtitleLanguage === 'japanese' ? 'ja' : 
                         subtitleLanguage === 'korean' ? 'ko' : 
                         subtitleLanguage === 'thai' ? 'th' : 'en';
          track.label = 'Subtitles';
          track.default = true;
          
          track.addEventListener('load', () => {
            console.log('Subtitle track loaded successfully');
            if (videoRef.current && videoRef.current.textTracks.length > 0) {
              videoRef.current.textTracks[0].mode = 'showing';
            }
          });
          
          track.addEventListener('error', (e) => {
            console.error('Subtitle track loading error:', e);
          });
          
          videoRef.current.appendChild(track);
        }
      };
      
      if (videoRef.current.readyState >= 2) {
        addSubtitles();
      } else {
        videoRef.current.addEventListener('loadeddata', addSubtitles, { once: true });
      }
    }
  }, [status, generateSubtitles, subtitleLanguage, fileId]);

  const formatStepName = (step) => {
    const stepNames = {
      'extract_slides': 'Extracting Content',
      'analyze_slide_images': 'Analyzing Visuals',
      'generate_scripts': 'Creating Narratives',
      'review_scripts': 'Refining Content',
      'generate_subtitle_scripts': 'Generating Subtitles',
      'review_subtitle_scripts': 'Refining Subtitles',
      'generate_audio': 'Synthesizing Audio',
      'generate_avatar_videos': 'Generating Avatars',
      'convert_slides_to_images': 'Converting Slides',
      'compose_video': 'Composing Video',
      'unknown': 'Initializing'
    };
    return stepNames[step] || step;
  };

  const getLanguageDisplayName = (languageCode) => {
    const languageNames = {
      'english': 'English',
      'simplified_chinese': '简体中文',
      'traditional_chinese': '繁體中文',
      'japanese': '日本語',
      'korean': '한국어',
      'thai': 'ไทย'
    };
    return languageNames[languageCode] || languageCode;
  };

  const getProcessingStatusMessage = () => {
    if (!processingDetails) return 'Bringing Your Presentation to Life';
    
    const activeSteps = Object.entries(processingDetails.steps || {})
      .filter(([_, step]) => step.status === 'processing');
    
    if (activeSteps.length > 0) {
      const stepName = formatStepName(activeSteps[0][0]);
      const statusMessages = {
        'Extracting Content': 'Analyzing your presentation structure...',
        'Analyzing Visuals': 'Examining slide visuals and content...',
        'Creating Narratives': 'Crafting engaging AI narratives...',
        'Refining Content': 'Polishing the script for perfect delivery...',
        'Generating Subtitles': 'Creating subtitle translations...',
        'Refining Subtitles': 'Perfecting subtitle timing and accuracy...',
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
                <div className="file-upload-area">
                  <input
                    type="file"
                    id="file-upload"
                    accept=".pdf,.pptx,.ppt"
                    onChange={handleFileChange}
                    className="file-input"
                  />
                  <label htmlFor="file-upload" className="file-upload-label">
                    <div className="upload-icon">📁</div>
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
                
                <div className="options-section">
                  <div className="option-group">
                    <div className="option-item">
                      <input
                        type="checkbox"
                        id="generate-avatar"
                        checked={generateAvatar}
                        onChange={(e) => setGenerateAvatar(e.target.checked)}
                      />
                      <label htmlFor="generate-avatar">AI Avatar</label>
                    </div>
                    
                    <div className="option-item">
                      <input
                        type="checkbox"
                        id="generate-subtitles"
                        checked={generateSubtitles}
                        onChange={(e) => setGenerateSubtitles(e.target.checked)}
                      />
                      <label htmlFor="generate-subtitles">Subtitles</label>
                    </div>
                  </div>
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
                  {/* <p className="progress-text">{progress}% Complete</p>
                  <p className="processing-status">
                    {progress < 30 ? 'Initializing AI magic...' : 
                     progress < 60 ? 'Transforming your content...' : 
                     progress < 90 ? 'Finalizing your masterpiece...' : 
                     'Almost there! Polishing details...'}
                  </p> */}
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
                      {['extract_slides', 'convert_slides_to_images', 'analyze_slide_images', 'generate_scripts', 'review_scripts', 'generate_subtitle_scripts', 'review_subtitle_scripts', 'generate_audio', 'generate_avatar_videos', 'compose_video'].map((stepName) => {
                        const stepData = processingDetails.steps[stepName] || { status: 'pending' };
                        return (
                          <div key={stepName} className={`step-item ${stepData.status}`}>
                            <span className="step-icon">
                              {stepData.status === 'completed' ? '✓' : 
                               stepData.status === 'processing' ? '●' : 
                               stepData.status === 'failed' ? '✗' : 
                               stepData.status === 'skipped' ? '⊘' : '○'}
                            </span>
                            <span className="step-name">{formatStepName(stepName)}</span>
                          </div>
                        );
                      })}
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
                          <span className="info-value">{processingDetails.audio_language ? getLanguageDisplayName(processingDetails.audio_language) : 'English'}</span>
                        </div>
                        <div className="info-item">
                          <span className="info-label">Subtitle Language:</span>
                          <span className="info-value">{processingDetails.subtitle_language ? getLanguageDisplayName(processingDetails.subtitle_language) : 'English'}</span>
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
                      
                      {/* Resource Section with URLs and Download Buttons */}
                      <div className="resource-section">
                        
                        {/* Video Resource */}
                        <div className="resource-item">
                          <div className="resource-info">
                            <label>Video:</label>
                            <input 
                              type="text" 
                              value={`${window.location.origin}/api/video/${fileId}`}
                              readOnly 
                              className="url-input"
                            />
                          </div>
                          <div className="resource-actions">
                            <button 
                              onClick={() => {
                                navigator.clipboard.writeText(`${window.location.origin}/api/video/${fileId}`);
                                alert('Video URL copied to clipboard!');
                              }}
                              className="copy-btn"
                            >
                              Copy URL
                            </button>
                            <button onClick={downloadVideo} className="download-btn">
                              Download
                            </button>
                          </div>
                        </div>
                        
                        {/* Subtitle Resources */}
                        {generateSubtitles && fileId && (
                          <>
                            <div className="resource-item">
                              <div className="resource-info">
                                <label>SRT Subtitles:</label>
                                <input 
                                  type="text" 
                                  value={`${window.location.origin}/api/subtitles/${fileId}/srt`}
                                  readOnly 
                                  className="url-input"
                                />
                              </div>
                              <div className="resource-actions">
                                <button 
                                  onClick={() => {
                                    navigator.clipboard.writeText(`${window.location.origin}/api/subtitles/${fileId}/srt`);
                                    alert('SRT URL copied to clipboard!');
                                  }}
                                  className="copy-btn"
                                >
                                  Copy URL
                                </button>
                                <button 
                                  onClick={() => {
                                    if (fileId) {
                                      const link = document.createElement('a');
                                      link.href = `/api/subtitles/${fileId}/srt`;
                                      link.download = `presentation_${fileId}.srt`;
                                      link.target = '_blank';
                                      document.body.appendChild(link);
                                      link.click();
                                      document.body.removeChild(link);
                                    } else {
                                      alert('Subtitles not available for download. Please try again.');
                                    }
                                  }} 
                                  className="download-btn"
                                >
                                  Download
                                </button>
                              </div>
                            </div>
                            
                            <div className="resource-item">
                              <div className="resource-info">
                                <label>VTT Subtitles:</label>
                                <input 
                                  type="text" 
                                  value={`${window.location.origin}/api/subtitles/${fileId}/vtt`}
                                  readOnly 
                                  className="url-input"
                                />
                              </div>
                              <div className="resource-actions">
                                <button 
                                  onClick={() => {
                                    navigator.clipboard.writeText(`${window.location.origin}/api/subtitles/${fileId}/vtt`);
                                    alert('VTT URL copied to clipboard!');
                                  }}
                                  className="copy-btn"
                                >
                                  Copy URL
                                </button>
                                <button 
                                  onClick={() => {
                                    if (fileId) {
                                      const link = document.createElement('a');
                                      link.href = `/api/subtitles/${fileId}/vtt`;
                                      link.download = `presentation_${fileId}.vtt`;
                                      link.target = '_blank';
                                      document.body.appendChild(link);
                                      link.click();
                                      document.body.removeChild(link);
                                    } else {
                                      alert('Subtitles not available for download. Please try again.');
                                    }
                                  }} 
                                  className="download-btn"
                                >
                                  Download
                                </button>
                              </div>
                            </div>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="action-buttons">
                  <button onClick={resetForm} className="secondary-btn">
                    Create Another Presentation
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