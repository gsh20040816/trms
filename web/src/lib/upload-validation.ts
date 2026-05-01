export const MAX_UPLOAD_FILE_MIB = 64;
export const MAX_UPLOAD_FILE_BYTES = MAX_UPLOAD_FILE_MIB * 1024 * 1024;
export const MAX_UPLOAD_FILE_SIZE_LABEL = `${MAX_UPLOAD_FILE_MIB}MB`;

export function findOversizedFile(files: File[]) {
  return files.find((file) => file.size > MAX_UPLOAD_FILE_BYTES) ?? null;
}
