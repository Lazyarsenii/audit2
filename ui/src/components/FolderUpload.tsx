'use client';

import { useState, useRef, useCallback } from 'react';
import { API_BASE, apiFetch } from '@/lib/api';

interface FolderUploadProps {
  onUploadComplete: (result: { uploadId: string; path: string; fileCount: number }) => void;
  onError?: (error: string) => void;
}

interface UploadProgress {
  phase: 'reading' | 'uploading' | 'done';
  current: number;
  total: number;
  message: string;
}

// Check if browser supports File System Access API
const supportsDirectoryPicker = typeof window !== 'undefined' && 'showDirectoryPicker' in window;

// Files to skip during upload
const SKIP_PATTERNS = [
  /^\.git\//,
  /^node_modules\//,
  /^__pycache__\//,
  /^\.venv\//,
  /^venv\//,
  /^\.env$/,
  /^\.env\./,
  /\.pyc$/,
  /^dist\//,
  /^build\//,
  /^\.next\//,
  /^coverage\//,
];

function shouldSkipFile(path: string): boolean {
  return SKIP_PATTERNS.some(pattern => pattern.test(path));
}

export default function FolderUpload({ onUploadComplete, onError }: FolderUploadProps) {
  const apiUrl = API_BASE || 'http://localhost:8000';
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const zipInputRef = useRef<HTMLInputElement>(null);

  // Read all files from a directory using File System Access API
  const readDirectory = useCallback(async (dirHandle: FileSystemDirectoryHandle, basePath = ''): Promise<{ path: string; file: File }[]> => {
    const files: { path: string; file: File }[] = [];

    // @ts-ignore
    for await (const [name, entry] of dirHandle.entries()) {
      const entryPath = basePath ? `${basePath}/${name}` : name;

      if (shouldSkipFile(entryPath)) {
        continue;
      }

      if (entry.kind === 'file') {
        const fileHandle = entry as FileSystemFileHandle;
        const file = await fileHandle.getFile();
        files.push({ path: entryPath, file });
      } else if (entry.kind === 'directory') {
        const subDirHandle = entry as FileSystemDirectoryHandle;
        const subFiles = await readDirectory(subDirHandle, entryPath);
        files.push(...subFiles);
      }
    }

    return files;
  }, []);

  // Upload files to backend
  const uploadFiles = useCallback(async (files: { path: string; file: File }[]) => {
    setIsUploading(true);
    setProgress({ phase: 'uploading', current: 0, total: files.length, message: 'Uploading files...' });

    try {
      const formData = new FormData();

      // Add files and paths
      files.forEach(({ path, file }) => {
        formData.append('files', file);
        formData.append('paths', path);
      });

      const response = await apiFetch(`${apiUrl}/api/upload/files`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Upload failed');
      }

      const result = await response.json();

      setProgress({ phase: 'done', current: files.length, total: files.length, message: 'Upload complete!' });

      onUploadComplete({
        uploadId: result.upload_id,
        path: result.path,
        fileCount: result.file_count,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      onError?.(message);
    } finally {
      setIsUploading(false);
      setTimeout(() => setProgress(null), 2000);
    }
  }, [apiUrl, onUploadComplete, onError]);

  // Handle folder picker (File System Access API)
  const handleSelectFolder = useCallback(async () => {
    if (!supportsDirectoryPicker) {
      onError?.('Your browser does not support folder selection. Please use ZIP upload.');
      return;
    }

    try {
      // @ts-expect-error - showDirectoryPicker is not in TS types yet
      const dirHandle = await window.showDirectoryPicker();

      setIsUploading(true);
      setProgress({ phase: 'reading', current: 0, total: 0, message: 'Reading files...' });

      const files = await readDirectory(dirHandle);

      if (files.length === 0) {
        onError?.('No files found in selected folder');
        setIsUploading(false);
        setProgress(null);
        return;
      }

      setProgress({ phase: 'reading', current: files.length, total: files.length, message: `Found ${files.length} files` });

      await uploadFiles(files);
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        // User cancelled - not an error
        return;
      }
      const message = error instanceof Error ? error.message : 'Failed to read folder';
      onError?.(message);
      setIsUploading(false);
      setProgress(null);
    }
  }, [readDirectory, uploadFiles, onError]);

  // Handle ZIP upload
  const handleZipUpload = useCallback(async (file: File) => {
    if (!file.name.endsWith('.zip')) {
      onError?.('Please select a ZIP file');
      return;
    }

    setIsUploading(true);
    setProgress({ phase: 'uploading', current: 0, total: 1, message: 'Uploading ZIP file...' });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await apiFetch(`${apiUrl}/api/upload/zip`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Upload failed');
      }

      const result = await response.json();

      setProgress({ phase: 'done', current: 1, total: 1, message: 'Upload complete!' });

      onUploadComplete({
        uploadId: result.upload_id,
        path: result.path,
        fileCount: result.file_count,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Upload failed';
      onError?.(message);
    } finally {
      setIsUploading(false);
      setTimeout(() => setProgress(null), 2000);
    }
  }, [apiUrl, onUploadComplete, onError]);

  // Handle drag & drop for ZIP files
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const items = e.dataTransfer.items;
    if (items.length === 0) return;

    const item = items[0];

    // Check if it's a ZIP file
    if (item.type === 'application/zip' || item.type === 'application/x-zip-compressed') {
      const file = item.getAsFile();
      if (file) {
        await handleZipUpload(file);
      }
    } else {
      onError?.('Please drop a ZIP file');
    }
  };

  return (
    <div className="w-full">
      {/* Main upload area */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all ${
          isDragging
            ? 'border-primary-500 bg-primary-50'
            : isUploading
            ? 'border-slate-300 bg-slate-50'
            : 'border-slate-300 hover:border-primary-400 hover:bg-slate-50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {progress ? (
          <div className="space-y-4">
            <div className="animate-pulse">
              <svg className="w-12 h-12 mx-auto text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <div>
              <p className="text-slate-700 font-medium">{progress.message}</p>
              {progress.phase !== 'done' && progress.total > 0 && (
                <div className="mt-2">
                  <div className="w-48 mx-auto bg-slate-200 rounded-full h-2">
                    <div
                      className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(progress.current / progress.total) * 100}%` }}
                    />
                  </div>
                  <p className="text-sm text-slate-500 mt-1">
                    {progress.current} / {progress.total} files
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            <svg className="w-12 h-12 mx-auto text-slate-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>

            <p className="text-slate-600 mb-4">
              {supportsDirectoryPicker
                ? 'Select a folder or drag & drop a ZIP file'
                : 'Upload a ZIP file of your repository'}
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              {supportsDirectoryPicker && (
                <button
                  onClick={handleSelectFolder}
                  disabled={isUploading}
                  className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  <span className="flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                    Select Folder
                  </span>
                </button>
              )}

              <button
                onClick={() => zipInputRef.current?.click()}
                disabled={isUploading}
                className={`px-6 py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50 ${
                  supportsDirectoryPicker
                    ? 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                    : 'bg-primary-600 hover:bg-primary-700 text-white'
                }`}
              >
                <span className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                  Upload ZIP
                </span>
              </button>
            </div>

            <input
              ref={zipInputRef}
              type="file"
              accept=".zip"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleZipUpload(file);
              }}
            />

            <p className="text-sm text-slate-500 mt-4">
              Skips: .git, node_modules, __pycache__, .env files
            </p>

            {!supportsDirectoryPicker && (
              <p className="text-xs text-amber-600 mt-2">
                Tip: Use Chrome or Edge for folder selection
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
