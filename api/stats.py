import os
import sys
import json
from http.server import BaseHTTPRequestHandler

# Añadir el root del proyecto al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.db import get_dashboard_stats


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        stats = get_dashboard_stats()

        # Headers CORS para acceso desde el frontend
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        self.wfile.write(json.dumps(stats).encode('utf-8'))