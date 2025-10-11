/**
 * File validation utilities for the SlideSpeaker web application.
 */

// Supported file types
const SUPPORTED_FILE_TYPES = {
  pdf: ['.pdf'],
  slides: ['.pptx', '.ppt'],
} as const;

// Maximum file sizes (in bytes)
const MAX_FILE_SIZES = {
  pdf: 100 * 1024 * 1024, // 100 MB
  slides: 200 * 1024 * 1024, // 200 MB
} as const;

/**
 * Validates a file based on its type and size.
 * @param file The file to validate
 * @param fileType The expected file type ('pdf' or 'slides')
 * @returns Object with isValid flag and optional error message
 */
export const validateFile = (
  file: File,
  fileType: keyof typeof SUPPORTED_FILE_TYPES
): { isValid: boolean; errorMessage?: string } => {
  // Check file extension
  const extension = '.' + file.name.toLowerCase().split('.').pop();
  const supportedExtensions = SUPPORTED_FILE_TYPES[fileType];

  if (!supportedExtensions.some((ext) => ext === extension)) {
    return {
      isValid: false,
      errorMessage: `Invalid file type. Supported types for ${fileType}: ${supportedExtensions.join(', ')}`,
    };
  }

  // Check file size
  const maxSize = MAX_FILE_SIZES[fileType];
  if (file.size > maxSize) {
    const maxSizeMB = maxSize / (1024 * 1024);
    return {
      isValid: false,
      errorMessage: `File size exceeds the maximum limit of ${maxSizeMB} MB.`,
    };
  }

  return { isValid: true };
};

/**
 * Gets the file type based on its extension.
 * @param fileName The name of the file
 * @returns The file type ('pdf', 'slides', or null if unsupported)
 */
export const getFileType = (fileName: string): 'pdf' | 'slides' | null => {
  const extension = '.' + fileName.toLowerCase().split('.').pop();

  if (SUPPORTED_FILE_TYPES.pdf.some((ext) => ext === extension)) {
    return 'pdf';
  }
  
  if (SUPPORTED_FILE_TYPES.slides.some((ext) => ext === extension)) {
    return 'slides';
  }
  
  return null;
};

/**
 * Formats file size in a human-readable format.
 * @param bytes The file size in bytes
 * @returns Formatted file size string
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
