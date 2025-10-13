/**
 * Unified file type icon utility
 * Provides consistent file type icons across all components
 */

/**
 * Get the appropriate emoji icon for a file extension
 * @param fileExt - File extension (with or without leading dot)
 * @returns Emoji string for the file type
 */
export const getFileTypeIcon = (fileExt: string): string => {
  if (!fileExt) return '📄'; // Default document icon

  const ext = fileExt.toLowerCase().replace(/^\./, ''); // Remove leading dot and normalize

  switch (ext) {
    case 'pdf':
      return '📑'; // Document icon for PDF
    case 'ppt':
    case 'pptx':
      return '📊'; // Presentation icon for PowerPoint
    case 'doc':
    case 'docx':
      return '📝'; // Document icon for Word
    case 'xls':
    case 'xlsx':
      return '📈'; // Spreadsheet icon for Excel
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'svg':
      return '🖼️'; // Image icon
    case 'mp4':
    case 'avi':
    case 'mov':
    case 'wmv':
      return '🎬'; // Video icon
    case 'mp3':
    case 'wav':
    case 'aac':
    case 'flac':
      return '🎵'; // Audio icon
    default:
      return '📄'; // Default document icon
  }
};

/**
 * Check if a file extension is a PDF
 * @param fileExt - File extension (with or without leading dot)
 * @returns true if PDF, false otherwise
 */
export const isPdf = (fileExt?: string): boolean => {
  if (!fileExt) return false;
  return fileExt.toLowerCase().replace(/^\./, '') === 'pdf';
};

/**
 * Check if a file extension is a PowerPoint file
 * @param fileExt - File extension (with or without leading dot)
 * @returns true if PowerPoint, false otherwise
 */
export const isPowerPoint = (fileExt?: string): boolean => {
  if (!fileExt) return false;
  const ext = fileExt.toLowerCase().replace(/^\./, '');
  return ext === 'ppt' || ext === 'pptx';
};

/**
 * Get file type category for styling purposes
 * @param fileExt - File extension (with or without leading dot)
 * @returns CSS class suffix for styling
 */
export const getFileTypeCategory = (fileExt?: string): string => {
  if (!fileExt) return 'generic';

  const ext = fileExt.toLowerCase().replace(/^\./, '');

  if (ext === 'pdf') return 'pdf';
  if (ext === 'ppt' || ext === 'pptx') return 'ppt';
  if (ext === 'doc' || ext === 'docx') return 'doc';
  if (ext === 'xls' || ext === 'xlsx') return 'xls';
  if (['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(ext)) return 'image';
  if (['mp4', 'avi', 'mov', 'wmv'].includes(ext)) return 'video';
  if (['mp3', 'wav', 'aac', 'flac'].includes(ext)) return 'audio';

  return 'generic';
};