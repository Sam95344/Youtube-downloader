document.addEventListener('DOMContentLoaded', () => {
    const fetchButton = document.getElementById('fetch-button');
    const downloadButton = document.getElementById('download-button');
    const urlInput = document.getElementById('youtube-url');
    const videoInfoDiv = document.getElementById('video-info');
    const thumbnailImg = document.getElementById('thumbnail');
    const titleH2 = document.getElementById('video-title');
    const qualityOptions = document.getElementById('quality-options');
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loader-text');
    const errorMessageDiv = document.getElementById('error-message');
    const downloadLinkContainer = document.getElementById('download-link-container');
    const downloadLink = document.getElementById('download-link');

    fetchButton.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            showError('Please enter a YouTube URL.');
            return;
        }
        hideAllSections();
        showLoader('Fetching video info...');
        try {
            const response = await fetch('/get_video_info', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            displayVideoInfo(data);
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoader();
        }
    });

    downloadButton.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        const formatId = qualityOptions.value;
        hideAllSections();
        showLoader('Downloading, this may take a moment...');
        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, format_id: formatId }),
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            showDownloadLink(data.download_path);
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoader();
        }
    });

    function displayVideoInfo(data) {
        if (!data.formats || data.formats.length === 0) {
            showError("No downloadable formats found for this video.");
            return;
        }
        thumbnailImg.src = data.thumbnail;
        titleH2.textContent = data.title;
        qualityOptions.innerHTML = '';
        data.formats.forEach(format => {
            const option = document.createElement('option');
            option.value = format.format_id;
            let formatText = `${format.resolution} (${format.ext.toUpperCase()})`;
            if (format.format_note) formatText += ` - ${format.format_note}`;
            option.textContent = formatText;
            qualityOptions.appendChild(option);
        });
        videoInfoDiv.classList.remove('hidden');
    }

    function showDownloadLink(filePath) {
        downloadLink.href = `/downloads/${encodeURIComponent(filePath)}`;
        downloadLinkContainer.classList.remove('hidden');
    }

    function showError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.classList.remove('hidden');
    }

    function hideAllSections() {
        videoInfoDiv.classList.add('hidden');
        errorMessageDiv.classList.add('hidden');
        downloadLinkContainer.classList.add('hidden');
    }

    function showLoader(text) {
        loaderText.textContent = text;
        loader.classList.remove('hidden');
    }

    function hideLoader() {
        loader.classList.add('hidden');
    }
});
