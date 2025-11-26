import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from yt_dlp import YoutubeDL

# लॉगिंग सेट करें ताकि आप सर्वर पर क्या हो रहा है देख सकें
logging.basicConfig(level=logging.INFO)

# Flask ऐप को इनिशियलाइज़ करें
app = Flask(__name__, static_folder='static', template_folder='templates')

# डाउनलोड की गई फ़ाइलों को स्टोर करने के लिए एक फ़ोल्डर बनाएँ
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

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
            
            # MP3 के लिए एक ऑडियो-ओनली विकल्प जोड़ें
            if any(f.get('acodec') != 'none' for f in info.get('formats', [])):
                 formats.append({
                        'format_id': 'mp3',
                        'ext': 'mp3',
                        'resolution': 'Audio Only',
                        'format_note': 'Best Audio'
                    })
            
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
    """उपयोगकर्ता द्वारा चुने गए फॉर्मेट में वीडियो या ऑडियो डाउनलोड करता है।"""
    url = request.json.get('url')
    format_id = request.json.get('format_id')

    if not url or not format_id:
        return jsonify({'error': 'URL and format ID are required'}), 400

    app.logger.info(f"Download request for URL: {url} with format: {format_id}")
    try:
        # MP3 डाउनलोड के लिए yt-dlp विकल्प
        if format_id == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
                'quiet': True, 'no_warnings': True
            }
        # वीडियो डाउनलोड के लिए yt-dlp विकल्प
        else:
            ydl_opts = {
                'format': f'{format_id}+bestaudio/best', # वीडियो और सबसे अच्छी ऑडियो को मर्ज करें
                'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
                'quiet': True, 'no_warnings': True
            }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if format_id == 'mp3':
                filename = os.path.splitext(filename)[0] + '.mp3'

            app.logger.info(f"File downloaded: {filename}")
            return jsonify({'download_path': os.path.basename(filename)})

    except Exception as e:
        app.logger.error(f"Download failed: {e}")
        return jsonify({'error': 'Download failed. The video may be region-locked or private.'}), 500

@app.route('/downloads/<path:filename>')
def downloaded_file(filename):
    """डाउनलोड की गई फ़ाइल को उपयोगकर्ता को भेजने के लिए सर्व करता है।"""
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
