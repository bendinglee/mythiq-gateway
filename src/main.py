import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app, origins="*")

# Service Registry - All Mythiq backend services
SERVICES = {
    'game': 'https://mythiq-game-maker-production.up.railway.app',
    'agent': 'https://mythiq-agent-production.up.railway.app', 
    'media': 'https://mythiq-media-creator-production.up.railway.app',
    'audio': 'https://mythiq-audio-creator-production.up.railway.app',
    'video': 'https://mythiq-video-creator-production.up.railway.app',
    'learning': 'https://mythiq-self-learning-ai-production.up.railway.app'
}

@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'services': list(SERVICES.keys())
    })

@app.route('/api/v1/services/status', methods=['GET'])
def services_status():
    """Check status of all backend services"""
    status_results = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            response = requests.get(f"{service_url}/health", timeout=5)
            status_results[service_name] = {
                'status': 'healthy' if response.ok else 'unhealthy',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            status_results[service_name] = {
                'status': 'error',
                'error': str(e)
            }
    
    return jsonify(status_results)

@app.route('/api/v1/<service>/<path:endpoint>', methods=['POST', 'GET'])
def proxy_request(service, endpoint):
    """Unified API endpoint that routes to appropriate service"""
    
    if service not in SERVICES:
        logger.error(f"Service not found: {service}")
        return jsonify({'error': f'Service {service} not found'}), 404
    
    service_url = SERVICES[service]
    request_data = request.get_json() if request.method == 'POST' else {}
    
    logger.info(f"Routing request to {service}/{endpoint}")
    
    try:
        # Route to appropriate service
        if request.method == 'POST':
            response = requests.post(
                f"{service_url}/{endpoint}",
                json=request_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
        else:
            response = requests.get(
                f"{service_url}/{endpoint}",
                timeout=30
            )
        
        if response.ok:
            try:
                response_data = response.json()
                logger.info(f"Successful response from {service}/{endpoint}")
                return jsonify(response_data)
            except json.JSONDecodeError:
                # Handle non-JSON responses
                return response.text, response.status_code
        else:
            logger.error(f"Service error from {service}: {response.status_code}")
            return jsonify({
                'error': f'Service error: {response.status_code}',
                'service': service,
                'endpoint': endpoint
            }), response.status_code
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout calling {service}/{endpoint}")
        return jsonify({
            'error': 'Service timeout',
            'service': service,
            'endpoint': endpoint
        }), 504
    except Exception as e:
        logger.error(f"Error calling {service}/{endpoint}: {str(e)}")
        return jsonify({
            'error': str(e),
            'service': service,
            'endpoint': endpoint
        }), 500

# Specific endpoint handlers for common operations
@app.route('/api/v1/chat', methods=['POST'])
def chat():
    """Chat with AI Assistant"""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400
    
    return proxy_request('agent', 'chat')

@app.route('/api/v1/generate/game', methods=['POST'])
def generate_game():
    """Generate a game"""
    return proxy_request('game', 'generate')

@app.route('/api/v1/generate/image', methods=['POST'])
def generate_image():
    """Generate an image"""
    return proxy_request('media', 'generate-image')

@app.route('/api/v1/generate/audio', methods=['POST'])
def generate_audio():
    """Generate audio"""
    return proxy_request('audio', 'generate')

@app.route('/api/v1/generate/video', methods=['POST'])
def generate_video():
    """Generate video"""
    return proxy_request('video', 'generate')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """Serve static files"""
    static_folder_path = app.static_folder
    if static_folder_path is None:
        return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "API Gateway is running. Use /api/v1/ endpoints for service access.", 200

if __name__ == '__main__':
    logger.info("Starting Mythiq API Gateway...")
    logger.info(f"Registered services: {list(SERVICES.keys())}")
    app.run(host='0.0.0.0', port=5000, debug=True)
