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
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', language);
    
    try {
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setProgress(percentCompleted);
        },
      });
      
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

  // Remove the pollStatus function as we'll use useEffect instead

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
      'extract_slides': 'Extracting Presentation Content',
      'analyze_slide_images': 'Analyzing Visual Content',
      'generate_scripts': 'Generating AI Narratives',
      'review_scripts': 'Reviewing & Refining Scripts',
      'generate_audio': 'Synthesizing Voice Audio',
      'generate_avatar_videos': 'Creating AI Presenter Videos',
      'convert_slides_to_images': 'Converting Slides to Images',
      'compose_video': 'Composing Final Presentation',
      'unknown': 'Initializing Process'
    };
    return stepNames[step] || step;
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>SlideSpeaker</h1>
        <p>Transform your slides into engaging AI-powered presentations</p>
      </header>

      <main className="main-content">
        <div className="upload-section">
          <div className="upload-card">
            <h2>Upload Your Slides</h2>
            
            {status === 'idle' && (
              <>
                <div className="file-input-container">
                  <input
                    type="file"
                    id="file-upload"
                    accept=".pdf,.pptx,.ppt"
                    onChange={handleFileChange}
                    className="file-input"
                  />
                  <label htmlFor="file-upload" className="file-input-label">
                    {file ? file.name : 'Choose PDF or PowerPoint file'}
                  </label>
                </div>
                
                <div className="language-selector">
                  <label htmlFor="language-select">Audio Language:</label>
                  <select 
                    id="language-select" 
                    value={language} 
                    onChange={(e) => setLanguage(e.target.value)}
                    className="language-select"
                  >
                    <option value="english">English</option>
                    <option value="chinese">Chinese (中文)</option>
                    <option value="japanese">Japanese (日本語)</option>
                    <option value="korean">Korean (한국어)</option>
                  </select>
                </div>
                
                {file && (
                  <button 
                    onClick={handleUpload} 
                    className="upload-btn"
                    disabled={uploading}
                  >
                    Start AI Processing
                  </button>
                )}
              </>
            )}

            {status === 'uploading' && (
              <div className="progress-container">
                <p>Uploading file... {progress}%</p>
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
            )}

            {status === 'processing' && (
              <div className="processing-container">
                <div className="loading-spinner"></div>
                <p>AI is processing your presentation... {progress}%</p>
                
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                
                {processingDetails && (
                  <div className="processing-details">
                    
                    <div className="steps-grid">
                      {['extract_slides', 'convert_slides_to_images', 'analyze_slide_images', 'generate_scripts', 'review_scripts', 'generate_audio', 'generate_avatar_videos', 'compose_video'].map((stepName) => {
                        const stepData = processingDetails.steps[stepName] || { status: 'pending' };
                        return (
                          <div key={stepName} className={`step-item ${stepData.status}`}>
                            <span className="step-status">
                              {stepData.status === 'completed' ? '✓' : 
                               stepData.status === 'processing' ? '⏳' : 
                               stepData.status === 'failed' ? '❌' : '◯'}
                            </span>
                            <span className="step-name">{formatStepName(stepName)}</span>
                          </div>
                        );
                      })}
                    </div>
                    
                    {processingDetails.errors && processingDetails.errors.length > 0 && (
                      <div className="error-details">
                        <p className="error-title">Errors encountered:</p>
                        {processingDetails.errors.map((error, index) => (
                          <div key={index} className="error-item">
                            <strong>{formatStepName(error.step)}:</strong> {error.error}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {status === 'completed' && (
              <div className="completed-container">
                <div className="success-icon">✓</div>
                <p>Presentation ready!</p>
                <button onClick={downloadVideo} className="download-btn">
                  Download Video
                </button>
                <button onClick={resetForm} className="reset-btn">
                  Create Another
                </button>
                
                <div className="video-preview">
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
              <div className="error-container">
                <div className="error-icon">⚠️</div>
                <p>Something went wrong. Please try again.</p>
                <button onClick={resetForm} className="reset-btn">
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