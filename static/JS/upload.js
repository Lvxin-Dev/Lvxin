document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const dragDropArea = document.getElementById('dragDropArea');
    const selectedFileDisplay = document.getElementById('selectedFile');
    const progressContainer = document.getElementById('progressContainer');
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('statusText');
    const uploadControls = document.getElementById('uploadControls');
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const analyzeBtn = document.querySelector('.analyze-btn');

    let currentFile = null;
    let uploadId = null;
    let isPaused = false;
    let isCancelled = false;
    let uploadedSize = 0; // Use a single variable to track byte progress
    const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB

    // Event Listeners
    if (dragDropArea) {
        dragDropArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0]));

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dragDropArea.addEventListener(eventName, preventDefaults, false);
        });

        dragDropArea.addEventListener('dragenter', () => dragDropArea.classList.add('dragover'));
        dragDropArea.addEventListener('dragleave', () => dragDropArea.classList.remove('dragover'));
        dragDropArea.addEventListener('drop', (e) => {
            dragDropArea.classList.remove('dragover');
            handleFileSelect(e.dataTransfer.files[0]);
        });
    }

    uploadForm.addEventListener('submit', handleUpload);
    pauseBtn.addEventListener('click', pauseUpload);
    resumeBtn.addEventListener('click', resumeUpload);
    cancelBtn.addEventListener('click', cancelUpload);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    async function handleFileSelect(file) {
        if (!file) return;

        currentFile = file;
        selectedFileDisplay.textContent = `Selected file: ${file.name}`;
        analyzeBtn.disabled = false;

        // Check for a resumable upload
        try {
            const response = await fetch(`/uploads/status?file_name=${encodeURIComponent(file.name)}`);
            if (!response.ok) {
                throw new Error('Could not check upload status.');
            }
            const data = await response.json();
            if (data.resumable) {
                if (confirm('An incomplete upload was found for this file. Do you want to resume?')) {
                    uploadId = data.upload_id;
                    uploadedSize = data.uploaded_size;
                    updateProgress(uploadedSize, file.size);

                    statusText.textContent = `Resuming upload for ${file.name}.`;
                    uploadChunks();
                } else {
                    resetUploadState();
                }
            }
        } catch (error) {
            console.error('Error checking for resumable upload:', error);
            statusText.textContent = 'Could not check for resumable upload.';
        }
    }

    async function handleUpload(e) {
        e.preventDefault();
        if (!currentFile) {
            alert('Please select a file to upload.');
            return;
        }

        if (!uploadId) {
            await initiateUpload();
        }
        uploadChunks();
    }

    async function initiateUpload() {
        try {
            const response = await fetch('/uploads/initiate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_name: currentFile.name,
                    file_size: currentFile.size,
                    mime_type: currentFile.type,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to initiate upload.');
            }

            const data = await response.json();
            uploadId = data.upload_id;
            uploadedSize = 0; // A new upload starts at 0

            statusText.textContent = 'Upload initiated. Starting...';
            progressContainer.style.display = 'block';
            uploadControls.style.display = 'flex';
            
        } catch (error) {
            console.error('Initiate Upload Error:', error);
            statusText.textContent = `Error: ${error.message}`;
            resetUploadState();
        }
    }

    async function uploadChunks() {
        isPaused = false;
        pauseBtn.style.display = 'inline-block';
        resumeBtn.style.display = 'none';

        while (uploadedSize < currentFile.size && !isPaused) {
            const startByte = uploadedSize; // Use the server-provided size directly
            const end = Math.min(startByte + CHUNK_SIZE, currentFile.size);
            const chunk = currentFile.slice(startByte, end);

            try {
                const response = await fetch(`/uploads/${uploadId}`, {
                    method: 'PATCH',
                    body: chunk, // Send the raw chunk
                    headers: {
                        'Content-Range': `bytes ${startByte}-${end - 1}/${currentFile.size}`,
                    },
                });

                if (!response.ok) {
                    throw new Error(`Chunk upload failed with status: ${response.status}`);
                }

                const data = await response.json();
                // The server is the source of truth for the new uploaded size
                uploadedSize = data.uploaded_size;
                updateProgress(uploadedSize, data.total_size);

            } catch (error) {
                if (isCancelled) {
                    statusText.textContent = 'Upload cancelled.';
                } else {
                    console.error('Chunk Upload Error:', error);
                    statusText.textContent = 'Upload failed. You can try to resume.';
                    isPaused = true;
                    pauseBtn.style.display = 'none';
                    resumeBtn.style.display = 'inline-block';
                    return;
                }
            }
        }

        if (!isPaused) {
            finishUpload();
        }
    }

    async function finishUpload() {
        try {
            const response = await fetch(`/uploads/${uploadId}/finish`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error('Failed to finalize upload.');
            }

            const data = await response.json();
            statusText.textContent = 'Upload complete! Analyzing...';
            uploadControls.style.display = 'none';
            window.location.href = `/analysis?filename=${encodeURIComponent(data.filename)}`;

        } catch (error) {
            console.error('Finish Upload Error:', error);
            statusText.textContent = 'Error: Could not finalize upload.';
        }
    }

    function pauseUpload() {
        isPaused = true;
        statusText.textContent = 'Upload paused.';
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'inline-block';
    }

    function resumeUpload() {
        isPaused = false;
        statusText.textContent = 'Resuming upload...';
        uploadChunks();
    }

    function cancelUpload() {
        if (uploadId) {
            // Optional: Send a request to the server to cancel the upload immediately
            // fetch(`/uploads/${uploadId}/cancel`, { method: 'POST' });
        }
        resetUploadState();
        statusText.textContent = 'Upload cancelled.';
    }

    function updateProgress(uploaded, total) {
        const percent = total > 0 ? Math.round((uploaded / total) * 100) : 0;
        progressBar.style.width = `${percent}%`;
        progressBar.textContent = `${percent}%`;
    }

    function resetUploadState() {
        isPaused = false;
        isCancelled = false;
        currentFile = null;
        uploadId = null;
        uploadedSize = 0;

        selectedFileDisplay.textContent = '';
        progressContainer.style.display = 'none';
        uploadControls.style.display = 'none';
        updateProgress(0, 0);
    }
});
