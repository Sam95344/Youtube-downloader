import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from yt_dlp import YoutubeDL
import tempfile

# लॉगिंग सेट करें ताकि आप Vercel पर लॉग्स देख सकें
logging.basicConfig(level=logging.INFO)

# Flask ऐप को इनिशियलाइज़ करें। Vercel रूट डायरेक्टरी से static/templates फोल्डर को ढूंढेगा।
app = Flask(__name__, static_folder='../static', template_folder='../templates')

# Vercel पर केवल /tmp डायरेक्टरी लिखने योग्य है
DOWNLOAD_FOLDER = tempfile.gettempdir()
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

@app.route('/')
def index():
    """मुख्य पेज (index.html) को रेंडर करता है।"""
    return render_template('index.html')

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    """दी गई YouTube URL से वीडियो की जानकारी प्राप्त करता है।"""
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    app.logger.info(f"Fetching info for URL: {url}")
    try:
        ydl_opts = {'quiet': True, 'no_warnings': True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            
            # केवल MP4 वीडियो फॉर्मेट्स (वीडियो और ऑडियो दोनों के साथ) को चुनें
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    formats.append({
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution'),
                        'format_note': f.get('format_note', '')
                    })
            
            # चेतावनी: MP3 रूपांतरण Vercel पर काम नहीं करेगा क्योंकि ffmpeg उपलब्ध नहीं है।
            # इसलिए, हमने MP3 विकल्प को हटा दिया है।
            
            return jsonify({
                'title': info.get('title', 'No title found'),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats
            })
    except Exception as e:
        app.logger.error(f"Error fetching video info: {e}")
        return jsonify({'error': 'Invalid URL or failed to fetch video data.'}), 500

@app.route('/download', methods=['POST'])
def download_video():
    """उपयोगकर्ता द्वारा चुने गए फॉर्मेट में वीडियो डाउनलोड करता है।"""
    url = request.json.get('url')
    format_id = request.json.get('format_id')

    if not url or not format_id:
        return jsonify({'error': 'URL and format ID are required'}), 400

    app.logger.info(f"Download request for URL: {url} with format: {format_id}")
    try:
        # वीडियो डाउनलोड के लिए yt-dlp विकल्प
        ydl_opts = {
            'format': f'{format_id}+bestaudio/best', # वीडियो और सबसे अच्छी ऑडियो को मर्ज करें
            'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
            'quiet': True, 'no_warnings': True
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # yt-dlp द्वारा तैयार किए गए वास्तविक फ़ाइल नाम का उपयोग करें
            filename = ydl.prepare_filename(info).replace(app.config['DOWNLOAD_FOLDER'] + os.sep, '')

            app.logger.info(f"File downloaded to /tmp: {filename}")
            return jsonify({'download_path': filename})

    except Exception as e:
        app.logger.error(f"Download failed: {e}")
        # Vercel पर ffmpeg न होने के कारण यह त्रुटि आम है
        if "ffmpeg" in str(e).lower():
            return jsonify({'error': 'Download failed. This format may require merging with ffmpeg, which is not available on Vercel.'}), 500
        return jsonify({'error': 'Download failed. The video may be region-locked or private.'}), 500

@app.route('/downloads/<path:filename>')
def downloaded_file(filename):
    """डाउनलोड की गई फ़ाइल को /tmp फ़ोल्डर से उपयोगकर्ता को भेजता है।"""
    app.logger.info(f"Serving file: {filename} from {app.config['DOWNLOAD_FOLDER']}")
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)