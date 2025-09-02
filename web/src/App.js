import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [fileId, setFileId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [processingDetails, setProcessingDetails] = useState(null);
  const [language, setLanguage] = useState('english');
  const [subtitleLanguage, setSubtitleLanguage] = useState('english');
  const [generateAvatar, setGenerateAvatar] = useState(true);
  const [generateSubtitles, setGenerateSubtitles] = useState(true);
  const [previewData, setPreviewData] = useState(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
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
      setStatus('processing');
      setProgress(0);
      
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
      setUploading(false);
      setStatus('idle');
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
    }
  };

  const resetForm = () => {
    setFile(null);
    setFileId(null);
    setStatus('idle');
    setUploading(false);
    setProgress(0);
    setProcessingDetails(null);
    setSubtitleLanguage('english');
    setGenerateAvatar(true);
    setGenerateSubtitles(true);
    setPreviewData(null);
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
            
            // Fetch preview data
            try {
              const previewResponse = await axios.get(`/api/preview/${fileId}`);
              setPreviewData(previewResponse.data);
            } catch (previewError) {
              console.error('Preview data fetch error:', previewError);
            }
          } else if (response.data.status === 'processing' || response.data.status === 'uploaded') {
            setStatus('processing');
            setProgress(response.data.progress);
          } else if (response.data.status === 'failed') {
            setStatus('error');
            setUploading(false);
          } else {
            setStatus('error');
            setUploading(false);
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

  const formatStepName = (step) => {
    const stepNames = {
      'extract_slides': 'Extracting Content',
      'analyze_slide_images': 'Analyzing Visuals',
      'generate_scripts': 'Generating Narratives',
      'review_scripts': 'Reviewing Scripts',
      'generate_audio': 'Creating Audio',
      'generate_avatar_videos': 'Generating Avatars',
      'convert_slides_to_images': 'Converting Slides',
      'compose_video': 'Composing Video',
      'unknown': 'Initializing'
    };
    return stepNames[step] || step;
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>SlideSpeaker AI</h1>
        <p>Turn your slides into captivating AI-powered videos with natural voice narration and expressive avatars</p>
      </header>

      <main className="main-content">
        <div className="card-container">
          <div className="content-card">
            {status === 'idle' && (
              <div className="upload-view">
                <h2>Transform Your Slides Into AI Magic</h2>
                <p className="subtitle">Upload your presentation and watch as AI brings it to life with natural voice narration and engaging avatars</p>
                
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
                
                <div className="advanced-options-toggle">
                  <button 
                    className="advanced-options-button"
                    onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                    aria-label={showAdvancedOptions ? "Hide advanced options" : "Show advanced options"}
                  >
                    <span className="advanced-options-icon">
                      {showAdvancedOptions ? '−' : '⋯'}
                    </span>
                  </button>
                </div>
                
                {showAdvancedOptions && (
                  <div className="options-section">
                    <div className="option-group">
                      <div className="option-item">
                        <input
                          type="checkbox"
                          id="generate-avatar"
                          checked={generateAvatar}
                          onChange={(e) => setGenerateAvatar(e.target.checked)}
                        />
                        <label htmlFor="generate-avatar">AI Avatar Video</label>
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
                )}
                
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
                <h3>Uploading File</h3>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="progress-text">{progress}% Complete</p>
              </div>
            )}

            {status === 'processing' && (
              <div className="processing-view">
                <div className="spinner"></div>
                <h3>Bringing Your Presentation to Life</h3>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="progress-text">{progress}% Complete</p>
                
                {processingDetails && (
                  <div className="steps-container">
                    <h4>Processing Steps</h4>
                    <div className="steps-grid">
                      {['extract_slides', 'convert_slides_to_images', 'analyze_slide_images', 'generate_scripts', 'review_scripts', 'generate_audio', 'generate_avatar_videos', 'compose_video'].map((stepName) => {
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
                
                {previewData && previewData.preview_available && (
                  <div className="preview-info">
                    <h4>Video Information</h4>
                    <ul>
                      <li><strong>File Size:</strong> {(previewData.video.file_size / (1024 * 1024)).toFixed(2)} MB</li>
                      <li><strong>Subtitles:</strong> {generateSubtitles && previewData.subtitles.srt_content ? 'Available' : generateSubtitles ? 'Not available' : 'Not generated (disabled)'}</li>
                      <li><strong>AI Avatar:</strong> {generateAvatar ? 'Generated' : 'Not generated (disabled)'}</li>
                    </ul>
                  </div>
                )}
                
                <div className="action-buttons">
                  <button onClick={() => window.open(`/api/preview-page/${fileId}`, '_blank')} className="primary-btn">
                    Preview
                  </button>
                  <button onClick={downloadVideo} className="secondary-btn">
                    Save Your Masterpiece
                  </button>
                  {generateSubtitles && previewData && previewData.subtitles && (
                    <>
                      {previewData.subtitles.srt_content && (
                        <button onClick={() => {
                          // Create a temporary link element
                          const link = document.createElement('a');
                          link.href = `/api/subtitles/${fileId}/srt`;
                          link.download = `presentation_${fileId}.srt`;
                          link.target = '_blank';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }} className="secondary-btn">
                          Get SRT Captions
                        </button>
                      )}
                      {previewData.subtitles.vtt_content && (
                        <button onClick={() => {
                          // Create a temporary link element
                          const link = document.createElement('a');
                          link.href = `/api/subtitles/${fileId}/vtt`;
                          link.download = `presentation_${fileId}.vtt`;
                          link.target = '_blank';
                          document.body.appendChild(link);
                          link.click();
                          document.body.removeChild(link);
                        }} className="secondary-btn">
                          Get VTT Captions
                        </button>
                      )}
                    </>
                  )}
                  <button onClick={resetForm} className="secondary-btn">
                    Create Another Magic
                  </button>
                </div>
                
                <div className="video-preview">
                  <h4>Quick Preview</h4>
                  <p className="preview-note">Click the "Preview" button above for the full experience with all features</p>
                  <video 
                    ref={videoRef}
                    controls
                    src={`/api/video/${fileId}`}
                    className="preview-video"
                  />
                  {generateSubtitles && previewData && previewData.subtitles && previewData.subtitles.vtt_url && (
                    <track 
                      kind="subtitles" 
                      src={previewData.subtitles.vtt_url} 
                      srcLang="en" 
                      label="Subtitles" 
                      default
                    />
                  )}
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