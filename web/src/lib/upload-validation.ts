export const MAX_UPLOAD_FILE_BYTES = 10 * 1024 * 1024;

export function findOversizedFile(files: File[]) {
  return files.find((file) => file.size > MAX_UPLOAD_FILE_BYTES) ?? null;
}
