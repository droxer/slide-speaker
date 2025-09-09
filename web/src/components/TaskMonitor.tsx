import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './TaskMonitor.scss';

// Function to check if subtitle file exists with better error handling
const checkSubtitleExists = async (url: string): Promise<{exists: boolean, error?: string}> => {
  try {
    const response = await fetch(url, { 
      method: 'HEAD',
      headers: {
        'Accept': 'text/vtt,text/plain,*/*'
      }
    });
    
    if (response.ok) {
      console.log('✅ Subtitle file found:', url);
      return { exists: true };
    } else if (response.status === 404) {
      console.log('❌ Subtitle file not found (404):', url);
      return { exists: false, error: 'Subtitle file not found' };
    } else {
      console.log('⚠️ Subtitle file check failed:', response.status, url);
      return { exists: false, error: `HTTP ${response.status}` };
    }
  } catch (error) {
    console.log('❌ Subtitle file check error:', error, url);
    return { exists: false, error: 'Network error' };
  }
};

// Types for task monitoring
interface TaskState {
  status: string;
  current_step: string;
  filename?: string;
  voice_language: string;
  subtitle_language?: string;
  generate_avatar: boolean;
  generate_subtitles: boolean;
  created_at: string;
  updated_at: string;
  errors: string[];
}

interface Task {
  task_id: string;
  file_id: string;
  task_type: string;
  status: string;
  created_at: string;
  updated_at: string;
  kwargs: {
    file_id: string;
    file_ext: string;
    filename?: string;
    voice_language: string;
    subtitle_language?: string;
    generate_avatar: boolean;
    generate_subtitles: boolean;
  };
  state?: TaskState;
  detailed_state?: any;
  completion_percentage?: number;
}

interface TaskStatistics {
  total_tasks: number;
  status_breakdown: Record<string, number>;
  language_stats: Record<string, number>;
  recent_activity: {
    last_24h: number;
    last_7d: number;
    last_30d: number;
  };
  processing_stats: {
    avg_processing_time_minutes?: number;
    success_rate: number;
    failed_rate: number;
  };
}

interface TaskMonitorProps {
  apiBaseUrl: string; // kept for compatibility; media uses relative paths
}

const TaskMonitor: React.FC<TaskMonitorProps> = ({ apiBaseUrl }) => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statistics, setStatistics] = useState<TaskStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [tasksPerPage] = useState(10);
  const [selectedTaskForPreview, setSelectedTaskForPreview] = useState<Task | null>(null);
  const [subtitleAvailable, setSubtitleAvailable] = useState<boolean>(false);
  const [subtitleLoading, setSubtitleLoading] = useState<boolean>(false);
  const [videoLoading, setVideoLoading] = useState<boolean>(true);
  const [videoError, setVideoError] = useState<string | null>(null);
  const modalVideoRef = React.useRef<HTMLVideoElement | null>(null);
  const [removingTaskIds, setRemovingTaskIds] = useState<Set<string>>(new Set());

  // Debug log for preview state
  useEffect(() => {
    console.log('Selected task for preview:', selectedTaskForPreview);
  }, [selectedTaskForPreview]);

  // Debug API base URL
  useEffect(() => {
    console.log('TaskMonitor apiBaseUrl:', apiBaseUrl);
  }, [apiBaseUrl]);

  // Check subtitle availability when task is selected for preview
  useEffect(() => {
    const checkSubtitles = async () => {
      if (selectedTaskForPreview) {
        setSubtitleLoading(true);
        const subtitleUrl = `${apiBaseUrl}/api/subtitles/${selectedTaskForPreview.file_id}/vtt`;
        const result = await checkSubtitleExists(subtitleUrl);
        setSubtitleAvailable(result.exists);
        console.log('Subtitle availability check:', { url: subtitleUrl, ...result });
        setSubtitleLoading(false);
      } else {
        setSubtitleAvailable(false);
        setSubtitleLoading(false);
      }
    };
    
    checkSubtitles();
  }, [selectedTaskForPreview, apiBaseUrl]);

  // Ensure the modal video actually loads and plays when a task is selected
  useEffect(() => {
    if (selectedTaskForPreview && modalVideoRef.current) {
      const url = `${apiBaseUrl}/api/video/${selectedTaskForPreview.file_id}`;
      try {
        console.log('Assigning modal video src:', url);
        modalVideoRef.current.src = url;
        // Force a load cycle to ensure network request is issued
        modalVideoRef.current.load();
        // Attempt autoplay (may be blocked with sound until interaction)
        const p = modalVideoRef.current.play();
        if (p && typeof p.then === 'function') {
          p.catch((err) => console.log('Autoplay blocked (expected until user interaction):', err));
        }
      } catch (e) {
        console.warn('Failed to initialize modal video element:', e);
      }
    }
  }, [selectedTaskForPreview, apiBaseUrl]);

  // Fetch tasks and statistics
  const fetchTasks = React.useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch task list
      const params = new URLSearchParams();
      if (statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      params.append('limit', tasksPerPage.toString());
      params.append('offset', ((currentPage - 1) * tasksPerPage).toString());

      const tasksResponse = await axios.get(`${apiBaseUrl}/api/tasks?${params}`);
      setTasks(tasksResponse.data.tasks);

      // Fetch statistics
      const statsResponse = await axios.get(`${apiBaseUrl}/api/tasks/statistics`);
      setStatistics(statsResponse.data);
    } catch (err) {
      setError('Failed to fetch task data');
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, currentPage, statusFilter, tasksPerPage]);

  // Search tasks
  const searchTasks = async (query: string) => {
    if (!query.trim()) {
      fetchTasks();
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${apiBaseUrl}/api/tasks/search?query=${encodeURIComponent(query)}`);
      setTasks(response.data.tasks);
    } catch (err) {
      setError('Failed to search tasks');
      console.error('Error searching tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  // Cancel task
  const cancelTask = async (taskId: string) => {
    try {
      await axios.delete(`${apiBaseUrl}/api/tasks/${taskId}`);
      // Refresh task list
      fetchTasks();
    } catch (err) {
      console.error('Error cancelling task:', err);
      alert('Failed to cancel task');
    }
  };

  // Delete task (purge from backend)
  const deleteTask = async (taskId: string) => {
    if (!window.confirm('This will permanently remove the task and its state. Continue?')) {
      return;
    }
    try {
      // Trigger removal animation first
      setRemovingTaskIds((prev) => new Set(prev).add(taskId));

      // Perform deletion request in parallel
      const doDelete = axios.delete(`${apiBaseUrl}/api/tasks/${taskId}/purge`);

      // Allow CSS transition to play before we refresh the list
      setTimeout(async () => {
        try {
          await doDelete;
        } catch (e) {
          console.error('Error deleting task:', e);
          alert('Failed to delete task');
        } finally {
          // Refresh task list and clear removing flag
          await fetchTasks();
          setRemovingTaskIds((prev) => {
            const next = new Set(prev);
            next.delete(taskId);
            return next;
          });
        }
      }, 280);
    } catch (err) {
      console.error('Error deleting task:', err);
      alert('Failed to delete task');
    }
  };

  // Preview task - show generated video
  const previewTask = (task: Task) => {
    console.log('Preview task called with:', task);
    // Only show preview for completed tasks that have videos
    if (task.status === 'completed') {
      setSelectedTaskForPreview(task);
    } else {
      alert('Video preview is only available for completed tasks.');
    }
  };

  // Close preview
  const closePreview = () => {
    setSelectedTaskForPreview(null);
  };

  // ESC key handler for closing modal
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && selectedTaskForPreview) {
        event.preventDefault();
        closePreview();
      }
    };

    if (selectedTaskForPreview) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset'; // Restore scrolling
    };
  }, [selectedTaskForPreview]);

  // Get task status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed';
      case 'processing':
        return 'status-processing';
      case 'queued':
        return 'status-queued';
      case 'failed':
        return 'status-failed';
      case 'cancelled':
        return 'status-cancelled';
      default:
        return 'status-default';
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  // Get language display name
  const getLanguageDisplayName = (languageCode: string): string => {
    const languageNames: Record<string, string> = {
      'english': 'English',
      'simplified_chinese': '简体中文',
      'traditional_chinese': '繁體中文',
      'japanese': '日本語',
      'korean': '한국어',
      'thai': 'ไทย'
    };
    return languageNames[languageCode] || languageCode || 'Unknown';
  };

  // Format step name for better readability
  const formatStepName = (step: string): string => {
    const stepNames: Record<string, string> = {
      // Common steps
      'extract_slides': 'Extracting Slides',
      'analyze_slide_images': 'Analyzing Content',
      'generate_transcripts': 'Generating Transcripts',
      'revise_transcripts': 'Revising Transcripts',
      'translate_voice_transcripts': 'Translating Voice Transcripts',
      'translate_subtitle_transcripts': 'Translating Subtitle Transcripts',
      'generate_subtitle_transcripts': 'Generating Subtitle Transcripts',
      'revise_subtitle_transcripts': 'Revising Subtitle Transcripts',
      'generate_audio': 'Generating Audio',
      'generate_avatar_videos': 'Creating Avatar',
      'convert_slides_to_images': 'Converting Slides',
      'generate_subtitles': 'Creating Subtitles',
      'compose_video': 'Composing Video',
      
      // PDF-specific steps
      'segment_pdf_content': 'Segmenting Content',
      'analyze_pdf_content': 'Analyzing Content',
      'revise_pdf_transcripts': 'Revising Transcripts',
      'generate_pdf_chapter_images': 'Creating Chapter Images',
      'generate_pdf_audio': 'Generating Audio',
      'generate_pdf_subtitles': 'Creating Subtitles',
      'compose_pdf_video': 'Composing Video',
      
      'unknown': 'Initializing'
    };
    return stepNames[step] || step;
  };

  // Get file type display name
  const getFileTypeDisplayName = (fileExt: string): string => {
    const ext = fileExt?.toLowerCase();
    switch (ext) {
      case '.pdf':
        return 'PDF Document';
      case '.pptx':
        return 'PowerPoint Presentation';
      case '.ppt':
        return 'PowerPoint 97-2003 Presentation';
      default:
        return `${ext?.toUpperCase() || 'Unknown'} File`;
    }
  };

  // Check if file is PDF
  const isPdfFile = (fileExt: string): boolean => {
    return fileExt?.toLowerCase() === '.pdf';
  };

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchTasks(searchQuery);
    } else {
      fetchTasks();
    }
  };

  // Handle status filter change
  const handleStatusFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setCurrentPage(1);
  };

  useEffect(() => {
    fetchTasks();
  }, [currentPage, statusFilter, fetchTasks]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      fetchTasks();
    }
  }, [searchQuery, fetchTasks]);

  if (loading && tasks.length === 0) {
    return (
      <div className="task-monitor">
        <div className="loading">Loading tasks...</div>
      </div>
    );
  }

  if (error && tasks.length === 0) {
    return (
      <div className="task-monitor">
        <div className="error">{error}</div>
        <button onClick={fetchTasks} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="task-monitor">
      <div className="monitor-header">
        <h2>Task Monitor</h2>
        <div className="monitor-controls">
          <form onSubmit={handleSearch} className="search-form">
            <input
              type="text"
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
            <button type="submit" className="search-button">
              Search
            </button>
          </form>
          
          <select
            value={statusFilter}
            onChange={handleStatusFilterChange}
            className="status-filter"
          >
            <option value="all">All Status</option>
            <option value="queued">Queued</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Enhanced Statistics Summary */}
      {statistics && (
        <div className="statistics-summary">
          <div className="stat-section">
            <h3 className="stat-section-title">📊 System Overview</h3>
            <div className="stat-cards-row">
              <div className="stat-card primary">
                <div className="stat-icon">📋</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.total_tasks}</div>
                  <div className="stat-label">Total Tasks</div>
                </div>
              </div>
              
              <div className="stat-card success">
                <div className="stat-icon">✅</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.processing_stats.success_rate.toFixed(1)}%</div>
                  <div className="stat-label">Success Rate</div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="stat-section">
            <h3 className="stat-section-title">⚡ Real-time Status</h3>
            <div className="stat-cards-row">
              <div className="stat-card info processing">
                <div className="stat-icon">⚡</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.status_breakdown.processing || 0}</div>
                  <div className="stat-label">Currently Running</div>
                  <div className="stat-description">Tasks in progress</div>
                </div>
              </div>
              
              <div className="stat-card warning queued">
                <div className="stat-icon">⏸️</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.status_breakdown.queued || 0}</div>
                  <div className="stat-label">In Queue</div>
                  <div className="stat-description">Waiting to start</div>
                </div>
              </div>
              
              <div className="stat-card danger failed">
                <div className="stat-icon">❌</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.status_breakdown.failed || 0}</div>
                  <div className="stat-label">Failed Tasks</div>
                  <div className="stat-description">Need attention</div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="stat-section">
            <h3 className="stat-section-title">📈 Activity Insights</h3>
            <div className="stat-cards-row">
              <div className="stat-card activity">
                <div className="stat-icon">📅</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.recent_activity.last_24h}</div>
                  <div className="stat-label">Last 24 Hours</div>
                </div>
              </div>
              
              <div className="stat-card activity">
                <div className="stat-icon">📊</div>
                <div className="stat-content">
                  <div className="stat-value">{statistics.recent_activity.last_7d}</div>
                  <div className="stat-label">Last 7 Days</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Task List */}
      <div className="task-list">
        {tasks.length === 0 ? (
          <div className="no-tasks">No tasks found</div>
        ) : (
          tasks.map((task) => (
            <div key={task.task_id} className={`task-item ${getStatusColor(task.status)} ${removingTaskIds.has(task.task_id) ? 'removing' : ''}`}>
              <div className="task-header">
                <div className="task-id">Task: {task.task_id}</div>
                <div className={`task-status ${getStatusColor(task.status)}`}>
                  {task.status === 'completed' ? 'Completed' : 
                   task.status === 'processing' ? '⏳ Processing' :
                   task.status === 'queued' ? '⏸️ Queued' :
                   task.status === 'failed' ? '❌ Failed' :
                   task.status === 'cancelled' ? '🚫 Cancelled' : task.status}
                </div>
              </div>
              
              <div className="task-details">
                <div className="task-info">
                  <span className="info-label">File ID:</span>
                  <span className="info-value">{task.file_id}</span>
                </div>

                {/* Original filename */}
                {(() => {
                  const originalName = task.kwargs?.filename || task.state?.filename;
                  return originalName ? (
                    <div className="task-info">
                      <span className="info-label">Filename:</span>
                      <span className="info-value" title={originalName}>{originalName}</span>
                    </div>
                  ) : null;
                })()}
                
                {/* Language Information - Consistent with other fields */}
                <div className="task-info">
                  <span className="info-label">Voice Language:</span>
                  <span className="info-value">
                    {(() => {
                      const voiceLang =
                        task.kwargs?.voice_language ||
                        task.state?.voice_language ||
                        'english';
                      return getLanguageDisplayName(voiceLang);
                    })()}
                  </span>
                </div>
                
                {(() => {
                  const voiceLang =
                    task.kwargs?.voice_language ||
                    task.state?.voice_language ||
                    'english';
                  const subtitleLang =
                    task.kwargs?.subtitle_language ||
                    task.state?.subtitle_language ||
                    voiceLang; // default subtitles to voice language when unspecified
                  return (
                    <div className="task-info">
                      <span className="info-label">Subtitle Language:</span>
                      <span className="info-value">
                        {getLanguageDisplayName(subtitleLang)}
                      </span>
                    </div>
                  );
                })()}
                
                {/* File type information */}
                <div className="task-info">
                  <span className="info-label">Document Type:</span>
                  <span className={`file-type-badge ${isPdfFile(task.kwargs?.file_ext) ? 'pdf' : 'ppt'}`}>
                    {getFileTypeDisplayName(task.kwargs?.file_ext)}
                  </span>
                </div>
                
                {/* Current Step or Status - Hide Status for completed tasks */}
                {task.status !== 'completed' && task.state && (
                  <div className="task-info">
                    <span className="info-label">Current Step:</span>
                    <span className="info-value">{formatStepName(task.state.current_step)}</span>
                  </div>
                )}
                
                {task.completion_percentage !== undefined && task.status !== 'completed' && (
                  <div className="task-info">
                    <span className="info-label">Progress:</span>
                    <span className="info-value">{task.completion_percentage}%</span>
                  </div>
                )}
                
                <div className="task-info">
                  <span className="info-label">Created:</span>
                  <span className="info-value">{formatDate(task.created_at)}</span>
                </div>
                
                <div className="task-info">
                  <span className="info-label">Updated:</span>
                  <span className="info-value">{formatDate(task.updated_at)}</span>
                </div>
              </div>
              
              <div className="task-actions">
                {task.status === 'completed' && (
                  <button
                    onClick={(e) => {
                      console.log('Watch Video button clicked', e);
                      console.log('Task data:', task);
                      e.preventDefault();
                      e.stopPropagation();
                      previewTask(task);
                    }}
                    className="preview-button"
                    title="Watch Generated Video"
                    type="button"
                  >
                    ▶️ Watch
                  </button>
                )}
                {(task.status === 'queued' || task.status === 'processing') && (
                  <button
                    onClick={() => cancelTask(task.task_id)}
                    className="cancel-button"
                  >
                    Cancel
                  </button>
                )}
                <button
                  onClick={() => deleteTask(task.task_id)}
                  className="delete-button"
                  title="Delete task"
                  type="button"
                  aria-label="Delete task"
                >
                  <svg
                    className="icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                    aria-hidden="true"
                  >
                    <path
                      d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.343.052.682.106 1.018.162m-1.018-.162L19.5 19.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 19.5L5.77 5.79m13.458 0a48.108 48.108 0 0 0-3.478-.397m-12 .559c.336-.056.675-.11 1.018-.162m0 0A48.11 48.11 0 0 1 9.25 5.25m5.5 0a48.11 48.11 0 0 1 3.482.342m-8.982-.342V4.5A1.5 1.5 0 0 1 10.25 3h3.5A1.5 1.5 0 0 1 15.25 4.5v.75m-8.982 0a48.667 48.667 0 0 0-3.538.397"
                      stroke="currentColor"
                      strokeWidth="1.8"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      <div className="pagination">
        <button
          onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
          disabled={currentPage === 1}
          className="page-button"
        >
          Previous
        </button>
        <span className="page-info">
          Page {currentPage}
        </span>
        <button
          onClick={() => setCurrentPage(currentPage + 1)}
          disabled={tasks.length < tasksPerPage}
          className="page-button"
        >
          Next
        </button>
      </div>

      {/* Video Preview Modal */}
      {selectedTaskForPreview && (
        <div 
          className="video-preview-modal" 
          onClick={closePreview}
          role="dialog"
          aria-modal="true"
        >
          <div 
            className="video-preview-content" 
            onClick={(e) => e.stopPropagation()}
            role="document"
          >
            {/* Close button */}
            <button 
              onClick={closePreview} 
              className="video-close-button"
              title="Close Preview"
              type="button"
              aria-label="Close video preview"
            >
              ✕
            </button>
            
            {/* Video Player */}
            <div className="video-player-container">
              {(() => {
                const videoUrl = `${apiBaseUrl}/api/video/${selectedTaskForPreview.file_id}`;
                const subtitleUrl = `${apiBaseUrl}/api/subtitles/${selectedTaskForPreview.file_id}/vtt`;
                const voiceLanguage = selectedTaskForPreview.kwargs?.voice_language || selectedTaskForPreview.state?.voice_language || 'english';
                const subtitleLanguage = selectedTaskForPreview.kwargs?.subtitle_language || selectedTaskForPreview.state?.subtitle_language || voiceLanguage;
                
                console.log('Video preview debug:', {
                  hasSubtitlesFlag: selectedTaskForPreview.kwargs?.generate_subtitles,
                  subtitleLanguage: subtitleLanguage,
                  subtitleAvailable: subtitleAvailable,
                  subtitleLoading: subtitleLoading,
                  subtitleUrl: subtitleUrl,
                  fileId: selectedTaskForPreview.file_id
                });
                
                return (
                  <div className="modal-video-wrapper">
                    <video 
                      key={selectedTaskForPreview.file_id}
                      ref={modalVideoRef}
                      controls 
                      autoPlay
                      playsInline
                      preload="auto"
                      className="video-player"
                      crossOrigin="anonymous"
                      onLoadStart={() => {
                        console.log('Video loading started:', videoUrl, 'ref exists?', !!modalVideoRef.current);
                        setVideoLoading(true);
                        setVideoError(null);
                      }}
                      onLoadedData={() => {
                        console.log('Video data loaded successfully');
                        setVideoLoading(false);
                      }}
                      onCanPlay={() => {
                        console.log('Video can play');
                        setVideoLoading(false);
                      }}
                      onCanPlayThrough={() => {
                        console.log('Video can play through');
                        setVideoLoading(false);
                      }}
                      onStalled={() => {
                        console.warn('Video stalled');
                      }}
                      onWaiting={() => {
                        console.log('Video waiting (buffering)');
                      }}
                      onError={(e) => {
                        console.error('Video loading error:', e);
                        setVideoError('Failed to load video');
                        setVideoLoading(false);
                      }}
                      onPlay={() => console.log('Video playback started')}
                      onPause={() => console.log('Video playback paused')}
                      onLoadedMetadata={(e) => {
                        console.log('Video metadata loaded');
                        const video = e.currentTarget as HTMLVideoElement;
                        // Attempt playback; browsers may require interaction if audio is unmuted
                        video.play().catch(error => {
                          console.log('Autoplay prevented, user interaction may be required:', error);
                        });
                      }}
                    >
                      {/* No <source> tag needed; using src on <video> */}
                      {subtitleAvailable && !subtitleLoading && (
                        <track
                          kind="subtitles"
                          src={subtitleUrl}
                          srcLang={subtitleLanguage === 'simplified_chinese' ? 'zh-Hans' : 
                                   subtitleLanguage === 'traditional_chinese' ? 'zh-Hant' : 
                                   subtitleLanguage === 'japanese' ? 'ja' : 
                                   subtitleLanguage === 'korean' ? 'ko' : 
                                   subtitleLanguage === 'thai' ? 'th' : 'en'}
                          label={getLanguageDisplayName(subtitleLanguage)}
                          default
                          onError={(e) => console.error('Subtitle track loading error:', e)}
                        />
                      )}
                      Your browser does not support the video tag.
                    </video>
                    
                    {/* File type information in preview */}
                    <div className="preview-file-info">
                      <div className={`file-type-badge ${isPdfFile(selectedTaskForPreview.kwargs?.file_ext) ? 'pdf' : 'ppt'}`}>
                        {getFileTypeDisplayName(selectedTaskForPreview.kwargs?.file_ext)}
                      </div>
                    </div>
                    
                    {/* Video loading and error states */}
                    {videoLoading && (
                      <div className="video-status-overlay loading">
                        <div className="loading-spinner"></div>
                        <p>Loading video...</p>
                      </div>
                    )}
                    
                    {videoError && (
                      <div className="video-status-overlay error">
                        <p>❌ {videoError}</p>
                        <button 
                          onClick={() => {
                            setVideoError(null);
                            setVideoLoading(true);
                            // Force video reload by changing src slightly
                            const video = document.querySelector('.video-player') as HTMLVideoElement;
                            if (video) {
                              video.load();
                              video.play().catch(err => console.log('Play failed:', err));
                            }
                          }} 
                          className="retry-button"
                        >
                          Retry
                        </button>
                      </div>
                    )}
                    
                    {/* Subtitle status indicator */}
                    {subtitleLoading && (
                      <div className="subtitle-indicator loading">
                        💬 Checking subtitles...
                      </div>
                    )}
                    
                    
                    {!subtitleAvailable && !subtitleLoading && selectedTaskForPreview.kwargs?.generate_subtitles && (
                      <div className="subtitle-indicator not-available">
                        💬 Subtitles not found for this video
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TaskMonitor;
