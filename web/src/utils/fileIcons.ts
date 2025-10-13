export const getFileTypeIcon = (fileExt: string): string => {
  if (!fileExt) return '📄';

  const ext = fileExt.toLowerCase().replace(/^\./, '');

  const iconMap: Record<string, string> = {
    pdf: '📑',
    ppt: '📊', pptx: '📊',
    doc: '📝', docx: '📝',
    xls: '📈', xlsx: '📈',
    jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', svg: '🖼️',
    mp4: '🎬', avi: '🎬', mov: '🎬', wmv: '🎬',
    mp3: '🎵', wav: '🎵', aac: '🎵', flac: '🎵',
  };

  return iconMap[ext] || '📄';
};

export const isPdf = (fileExt?: string): boolean => {
  if (!fileExt) return false;
  const ext = fileExt.toLowerCase().replace(/^\./, '');
  return ext === 'pdf';
};

export const isPowerPoint = (fileExt?: string): boolean => {
  if (!fileExt) return false;
  const ext = fileExt.toLowerCase().replace(/^\./, '');
  return ext === 'ppt' || ext === 'pptx';
};

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