const FILE_TYPES = {
  pdf: ['.pdf'],
  slides: ['.pptx', '.ppt'],
} as const;

const MAX_FILE_SIZES = {
  pdf: 100 * 1024 * 1024, // 100 MB
  slides: 200 * 1024 * 1024, // 200 MB
} as const;

export const validateFile = (
  file: File,
  fileType: keyof typeof FILE_TYPES
): { isValid: boolean; errorMessage?: string } => {
  const extension = '.' + file.name.toLowerCase().split('.').pop();

  // Type guard to check if extension is valid for the given fileType
  const isExtensionValid = (ext: string): boolean => {
    if (fileType === 'pdf') {
      return FILE_TYPES.pdf.includes(ext as any);
    } else if (fileType === 'slides') {
      return FILE_TYPES.slides.includes(ext as any);
    }
    return false;
  };

  if (!isExtensionValid(extension)) {
    const supported = FILE_TYPES[fileType];
    return {
      isValid: false,
      errorMessage: `Invalid file type. Supported types for ${fileType}: ${supported.join(', ')}`,
    };
  }

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

export const getFileType = (fileName: string): 'pdf' | 'slides' | null => {
  const extension = '.' + fileName.toLowerCase().split('.').pop();

  if (FILE_TYPES.pdf.includes(extension as any)) return 'pdf';
  if (FILE_TYPES.slides.includes(extension as any)) return 'slides';

  return null;
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
