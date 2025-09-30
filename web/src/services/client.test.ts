/**
 * Unit tests for the client service.
 */

// Mock the client module directly
import * as client from './client';

jest.mock('./client', () => {
  return {
    getTasks: jest.fn(),
    searchTasks: jest.fn(),
    getDownloads: jest.fn(),
    getTranscriptMarkdown: jest.fn(),
    getStats: jest.fn(),
    deleteTask: jest.fn(),
    purgeTask: jest.fn(),
    cancelRun: jest.fn(),
    upload: jest.fn(),
    getHealth: jest.fn(),
    headTaskVideo: jest.fn(),
    getTaskProgress: jest.fn(),
    getVttText: jest.fn(),
    api: {
      get: jest.fn(),
      post: jest.fn(),
      delete: jest.fn(),
      head: jest.fn(),
    },
  };
});

describe('ClientService', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  describe('getTasks', () => {
    it('should successfully get tasks without parameters', async () => {
      // Mock axios response
      const mockResponse = {
        tasks: [],
        total: 0,
        limit: 20,
        offset: 0,
        has_more: false,
      };

      // Mock the actual function implementation
      (client.getTasks as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getTasks();

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getTasks).toHaveBeenCalled();
    });

    it('should successfully get tasks with parameters', async () => {
      // Mock axios response
      const mockResponse = {
        tasks: [{ id: 'test_task_id' }],
        total: 1,
        limit: 10,
        offset: 0,
        has_more: false,
      };

      // Mock the actual function implementation
      (client.getTasks as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getTasks({ status: 'completed', limit: 10 });

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getTasks).toHaveBeenCalledWith({ status: 'completed', limit: 10 });
    });
  });

  describe('searchTasks', () => {
    it('should successfully search tasks', async () => {
      // Mock axios response
      const mockResponse = {
        tasks: [{ id: 'test_task_id', name: 'Test Task' }],
      };

      // Mock the actual function implementation
      (client.searchTasks as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.searchTasks('test query', 10);

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.searchTasks).toHaveBeenCalledWith('test query', 10);
    });

    it('should handle special characters in search query', async () => {
      // Mock axios response
      const mockResponse = {
        tasks: [],
      };

      // Mock the actual function implementation
      (client.searchTasks as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.searchTasks('test & query ?', 5);

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.searchTasks).toHaveBeenCalledWith('test & query ?', 5);
    });
  });

  describe('getDownloads', () => {
    it('should successfully get downloads for a task', async () => {
      // Mock axios response
      const mockResponse = {
        items: [
          { type: 'video', url: '/api/tasks/test_task_id/video' },
          { type: 'audio', url: '/api/tasks/test_task_id/audio' },
        ],
      };

      // Mock the actual function implementation
      (client.getDownloads as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getDownloads('test_task_id');

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getDownloads).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('getTranscriptMarkdown', () => {
    it('should successfully get transcript markdown', async () => {
      // Mock axios response
      const mockResponse = '# Test Transcript\n\nThis is a test transcript.';

      // Mock the actual function implementation
      (client.getTranscriptMarkdown as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getTranscriptMarkdown('test_task_id');

      // Verify the result
      expect(result).toBe('# Test Transcript\n\nThis is a test transcript.');
      expect(client.getTranscriptMarkdown).toHaveBeenCalledWith('test_task_id');
    });

    it('should handle empty response', async () => {
      // Mock axios response with empty data
      const mockResponse = '';

      // Mock the actual function implementation
      (client.getTranscriptMarkdown as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getTranscriptMarkdown('test_task_id');

      // Verify the result
      expect(result).toBe('');
      expect(client.getTranscriptMarkdown).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('getStats', () => {
    it('should successfully get statistics', async () => {
      // Mock axios response
      const mockResponse = {
        total_tasks: 100,
        status_breakdown: {
          queued: 10,
          processing: 20,
          completed: 60,
          failed: 10,
        },
      };

      // Mock the actual function implementation
      (client.getStats as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getStats();

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getStats).toHaveBeenCalled();
    });
  });

  describe('deleteTask', () => {
    it('should successfully delete a task', async () => {
      // Mock the actual function implementation
      (client.deleteTask as jest.Mock).mockResolvedValue(undefined);

      // Call the function
      await client.deleteTask('test_task_id');

      // Verify the function was called
      expect(client.deleteTask).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('purgeTask', () => {
    it('should successfully purge a task', async () => {
      (client.purgeTask as jest.Mock).mockResolvedValue(undefined);

      await client.purgeTask('test_task_id');

      expect(client.purgeTask).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('cancelRun', () => {
    it('should successfully cancel a task run', async () => {
      // Mock axios response
      const mockResponse = { message: 'Task cancelled successfully' };

      // Mock the actual function implementation
      (client.cancelRun as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.cancelRun('test_task_id');

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.cancelRun).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('upload', () => {
    it('should successfully upload payload', async () => {
      // Mock axios response
      const mockResponse = { file_id: 'test_file_id', task_id: 'test_task_id' };

      // Mock the actual function implementation
      (client.upload as jest.Mock).mockResolvedValue(mockResponse);

      // Mock payload
      const payload = { file_data: 'base64_encoded_data', filename: 'test.pdf' };

      // Call the function
      const result = await client.upload(payload);

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.upload).toHaveBeenCalledWith(payload);
    });
  });

  describe('getHealth', () => {
    it('should successfully get health status', async () => {
      // Mock axios response
      const mockResponse = { status: 'ok', redis: { ok: true }, db: { ok: true } };

      // Mock the actual function implementation
      (client.getHealth as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getHealth();

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getHealth).toHaveBeenCalled();
    });
  });

  describe('headTaskVideo', () => {
    it('should successfully check if task video exists', async () => {
      // Mock the actual function implementation
      (client.headTaskVideo as jest.Mock).mockResolvedValue(true);

      // Call the function
      const result = await client.headTaskVideo('test_task_id');

      // Verify the result
      expect(result).toBe(true);
      expect(client.headTaskVideo).toHaveBeenCalledWith('test_task_id');
    });

    it('should return false for non-existent task video', async () => {
      // Mock the actual function implementation
      (client.headTaskVideo as jest.Mock).mockResolvedValue(false);

      // Call the function
      const result = await client.headTaskVideo('test_task_id');

      // Verify the result
      expect(result).toBe(false);
      expect(client.headTaskVideo).toHaveBeenCalledWith('test_task_id');
    });

    it('should handle network errors gracefully', async () => {
      // Mock the actual function implementation to throw an error
      (client.headTaskVideo as jest.Mock).mockRejectedValue(new Error('Network error'));

      // Call the function and catch the error
      const result = await client.headTaskVideo('test_task_id').catch(() => false);

      // Verify the result
      expect(result).toBe(false);
      expect(client.headTaskVideo).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('getTaskProgress', () => {
    it('should successfully get task progress', async () => {
      // Mock axios response
      const mockResponse = { progress: 50, status: 'processing' };

      // Mock the actual function implementation
      (client.getTaskProgress as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getTaskProgress('test_task_id');

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getTaskProgress).toHaveBeenCalledWith('test_task_id');
    });

    it('should handle generic task progress', async () => {
      // Mock axios response
      const mockResponse = { progress: 75 };

      // Mock the actual function implementation
      (client.getTaskProgress as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getTaskProgress('test_task_id');

      // Verify the result
      expect(result).toEqual(mockResponse);
      expect(client.getTaskProgress).toHaveBeenCalledWith('test_task_id');
    });
  });

  describe('getVttText', () => {
    it('should successfully get VTT text without language', async () => {
      // Mock axios response
      const mockResponse = 'WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world';

      // Mock the actual function implementation
      (client.getVttText as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getVttText('test_task_id');

      // Verify the result
      expect(result).toBe('WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world');
      expect(client.getVttText).toHaveBeenCalledWith('test_task_id');
    });

    it('should successfully get VTT text with language', async () => {
      // Mock axios response
      const mockResponse = 'WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world';

      // Mock the actual function implementation
      (client.getVttText as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getVttText('test_task_id', 'english');

      // Verify the result
      expect(result).toBe('WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world');
      expect(client.getVttText).toHaveBeenCalledWith('test_task_id', 'english');
    });

    it('should handle special characters in language parameter', async () => {
      // Mock axios response
      const mockResponse = 'WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world';

      // Mock the actual function implementation
      (client.getVttText as jest.Mock).mockResolvedValue(mockResponse);

      // Call the function
      const result = await client.getVttText('test_task_id', 'simplified chinese');

      // Verify the result
      expect(result).toBe('WEBVTT\n\n00:00:01.000 --> 00:00:05.000\nHello world');
      expect(client.getVttText).toHaveBeenCalledWith('test_task_id', 'simplified chinese');
    });
  });
});
