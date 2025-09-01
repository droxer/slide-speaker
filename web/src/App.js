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
          language: language
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
      window.open(`/api/video/${fileId}`, '_blank');
    }
  };

  const resetForm = () => {
    setFile(null);
    setFileId(null);
    setStatus('idle');
    setUploading(false);
    setProgress(0);
    setProcessingDetails(null);
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
      
      // Set up interval to check status every 2 seconds
      intervalId = setInterval(checkStatus, 2000);
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
        <h1>SlideSpeaker</h1>
        <p>Transform presentations into engaging AI-powered videos</p>
      </header>

      <main className="main-content">
        <div className="card-container">
          <div className="content-card">
            {status === 'idle' && (
              <div className="upload-view">
                <h2>Convert Your Presentation</h2>
                <p className="subtitle">Upload a PDF or PowerPoint file to create an AI-powered video presentation</p>
                
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
                
                <div className="language-selector">
                  <label htmlFor="language-select">Audio Language</label>
                  <select 
                    id="language-select" 
                    value={language} 
                    onChange={(e) => setLanguage(e.target.value)}
                    className="language-select"
                  >
                    <option value="english">English</option>
                    <option value="chinese">中文 (Chinese)</option>
                    <option value="japanese">日本語 (Japanese)</option>
                    <option value="korean">한국어 (Korean)</option>
                    <option value="thai">ไทย (Thai)</option>
                  </select>
                </div>
                
                {file && (
                  <button 
                    onClick={handleUpload} 
                    className="primary-btn"
                    disabled={uploading}
                  >
                    Convert to Video
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
                <h3>Your Speaker is Getting Ready…</h3>
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
                               stepData.status === 'failed' ? '✗' : '○'}
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
                <h3>Video Ready!</h3>
                <p className="success-message">Your AI-powered presentation video has been generated successfully.</p>
                
                <div className="action-buttons">
                  <button onClick={downloadVideo} className="primary-btn">
                    Download Video
                  </button>
                  <button onClick={resetForm} className="secondary-btn">
                    Convert Another
                  </button>
                </div>
                
                <div className="video-preview">
                  <h4>Preview</h4>
                  <video 
                    ref={videoRef}
                    controls
                    src={`/api/video/${fileId}`}
                    className="preview-video"
                  />
                </div>
              </div>
            )}

            {status === 'error' && (
              <div className="error-view">
                <div className="error-icon">⚠️</div>
                <h3>Processing Failed</h3>
                <p className="error-message">Something went wrong during processing. Please try again.</p>
                <button onClick={resetForm} className="primary-btn">
                  Try Again
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>Powered by SlideSpeaker AI Technology</p>
      </footer>
    </div>
  );
}

export default App;