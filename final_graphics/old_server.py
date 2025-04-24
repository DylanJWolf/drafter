import http.server
import socketserver
import os

PORT = 8000
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.webp')

class ImageHandler(http.server.SimpleHTTPRequestHandler):
    def list_directory(self, path):
        try:
            file_list = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None

        file_list = [f for f in file_list if f.lower().endswith(IMAGE_EXTENSIONS)]
        file_list.sort()

        encoded = ''.join(f'<img src="{f}" style="max-width: 100%; margin: 10px;"><br>\n' for f in file_list)
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Image Gallery</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: sans-serif;
                    text-align: center;
                    padding: 1em;
                    background-color: #111;
                    color: white;
                }}
                img {{
                    border: 2px solid white;
                    max-width: 90vw;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            <h1>📸 Draft Image Gallery</h1>
            {encoded}
        </body>
        </html>
        """
        encoded_bytes = html.encode('utf-8', 'surrogateescape')
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_bytes)))
        self.end_headers()
        self.wfile.write(encoded_bytes)
        return None

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), ImageHandler) as httpd:
        print(f"Serving image gallery at http://localhost:{PORT}")
        httpd.serve_forever()
