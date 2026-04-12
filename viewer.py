import os
import json
import http.server
import socketserver
import datetime
import mimetypes
from urllib.parse import unquote, parse_qs
from PIL import Image
from pillow_heif import register_heif_opener

# --- CONFIGURATION & DOTENV HELPER ---
try:
    from dotenv import load_dotenv, set_key
    load_dotenv()
except ImportError:
    def set_key(path, key, value):
        lines = []
        if os.path.exists(path):
            with open(path, "r") as f: lines = f.readlines()
        with open(path, "w") as f:
            written = False
            for line in lines:
                if line.startswith(f"{key}="):
                    f.write(f"{key}={value}\n"); written = True
                else: f.write(line)
            if not written: f.write(f"{key}={value}\n")

ENV_FILE = ".env"
PORT = int(os.getenv("PORT", 0))
ROOT_PATH = "/media/archives/insta/archives"

register_heif_opener()

# --- CORE LOGIC ---

def pre_convert(stories_path):
    print(f"--- Pre-converting files in {stories_path} ---")
    pre_convert_heic(stories_path)

def pre_convert_heic(stories_path):
    if not os.path.exists(stories_path): return
    converted = 0
    for root, _, files in os.walk(stories_path):
        for file in files:
            if file.lower().endswith('.heic'):
                heic_path = os.path.join(root, file)
                jpg_path = os.path.splitext(heic_path)[0] + ".jpg"
                if not os.path.exists(jpg_path):
                    try:
                        Image.open(heic_path).convert('RGB').save(jpg_path, format='JPEG', quality=90)
                        converted += 1
                    except Exception as e: print(f"Failed {file}: {e}")
    if converted > 0: print(f"--- Converted HEIC to JPG: {converted} files ---")

def get_manifest(stories_dir):
    manifest = {}
    if not os.path.exists(stories_dir): return manifest
    # Ascending sort: Oldest folder names (202101) first
    for folder in sorted(os.listdir(stories_dir)):
        full_path = os.path.join(stories_dir, folder)
        if os.path.isdir(full_path):
            file_data = []
            for f in sorted(os.listdir(full_path)):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov')):
                    f_path = os.path.join(full_path, f)
                    mtime = os.path.getmtime(f_path)
                    date_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
                    file_data.append({"name": f, "date": date_str})
            if file_data: manifest[folder] = file_data
    return manifest

def get_folders(base_path):
    try:
        search_path = os.path.abspath(os.path.expanduser(base_path))
        return sorted([
            f for f in os.listdir(search_path) 
            if os.path.isdir(os.path.join(search_path, f)) and not f.startswith('.')
        ])
    except Exception: return []

# --- WEB SERVER ---

class ArchiveHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        requested_path = unquote(self.path).rstrip('/')
        
        if requested_path.startswith("/api/ls"):
            params = parse_qs(self.path.split('?')[-1]) if '?' in self.path else {}
            current = params.get('path', [os.path.expanduser('~')])[0]
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_folders(current)).encode())
            return

        if not os.getenv("ARCHIVE_PATH"):
            return self.serve_setup_page()

        if requested_path == ROOT_PATH or requested_path == "" or requested_path == "/":
            return self.serve_main_ui()

        stories_prefix = f"{ROOT_PATH}/stories"
        if requested_path.startswith(stories_prefix):
            return self.serve_media(requested_path, stories_prefix)

        self.send_error(404)

    def do_POST(self):
        if self.path == "/save-config":
            content_length = int(self.headers['Content-Length'])
            post_data = parse_qs(self.rfile.read(content_length).decode('utf-8'))
            raw_path = post_data.get('path', [''])[0].strip()
            new_path = os.path.abspath(os.path.expanduser(raw_path))
            
            if os.path.isdir(new_path):
                set_key(ENV_FILE, "ARCHIVE_PATH", new_path)
                os.environ["ARCHIVE_PATH"] = new_path
                pre_convert(os.path.join(new_path, "stories"))
                self.send_response(303)
                self.send_header('Location', ROOT_PATH)
                self.end_headers()
            else:
                self.send_error(400, f"Invalid Directory: {new_path}")

    def serve_setup_page(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        home = os.path.abspath(os.path.expanduser('~')).replace('\\', '/')
        html = f"""
        <html><head><title>Setup</title><style>
            body {{ background: #050a0f; color: #e1e8ed; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: #0d161f; padding: 30px; border-radius: 20px; border: 1px solid #4a90e2; width: 500px; }}
            .explorer {{ background: #000; border: 1px solid #1b2836; border-radius: 8px; height: 300px; overflow-y: auto; margin: 15px 0; }}
            .folder-item {{ padding: 10px; cursor: pointer; border-bottom: 1px solid #111; display: flex; align-items: center; }}
            .folder-item:hover {{ background: #111d29; color: #4a90e2; }}
            .folder-item::before {{ content: "📁"; margin-right: 10px; }}
            .path-bar {{ font-family: monospace; font-size: 11px; background: #111; padding: 12px; border-radius: 5px; color: #4a90e2; margin-bottom: 10px; }}
            button {{ background: #4a90e2; color: white; border: none; padding: 14px; border-radius: 8px; cursor: pointer; width: 100%; font-weight: bold; }}
            .back-btn {{ color: #8899a6; cursor: pointer; font-size: 12px; margin-bottom: 8px; display: inline-block; }}
        </style></head><body>
            <div class="card">
                <h2>Archive Setup</h2>
                <div id="pathDisplay" class="path-bar">/</div>
                <div id="back" class="back-btn">⬅ Go Up</div>
                <div id="explorer" class="explorer"></div>
                <form action="/save-config" method="POST">
                    <input type="hidden" id="finalPath" name="path" value="">
                    <button type="submit">Select This Folder</button>
                </form>
            </div>
            <script>
                let currentPath = "{home}";
                const explorer = document.getElementById('explorer');
                const pathDisplay = document.getElementById('pathDisplay');
                const finalPathInput = document.getElementById('finalPath');

                async function loadFolder(path) {{
                    currentPath = path;
                    pathDisplay.innerText = path;
                    finalPathInput.value = path;
                    const res = await fetch(`/api/ls?path=${{encodeURIComponent(path)}}`);
                    const folders = await res.json();
                    explorer.innerHTML = '';
                    folders.forEach(f => {{
                        const div = document.createElement('div');
                        div.className = 'folder-item';
                        div.innerText = f;
                        div.onclick = () => loadFolder(path.endsWith('/') ? path + f : path + '/' + f);
                        explorer.appendChild(div);
                    }});
                }}
                document.getElementById('back').onclick = () => {{
                    const parts = currentPath.split('/').filter(Boolean);
                    if(parts.length > 0) {{
                        parts.pop();
                        loadFolder('/' + parts.join('/'));
                    }}
                }};
                loadFolder(currentPath);
            </script>
        </body></html>
        """
        self.wfile.write(html.encode('utf-8'))

    def serve_main_ui(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            stories_dir = os.path.join(os.environ["ARCHIVE_PATH"], "stories")
            manifest_json = json.dumps(get_manifest(stories_dir))
            
            html = f"""
            <!DOCTYPE html><html><head><title>Insta Archive</title>
            <style>
                :root {{ --accent: #4a90e2; --bg: #050a0f; --panel: #0d161f; --text: #e1e8ed; --text-muted: #8899a6; }}
                body {{ background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; margin: 0; overflow: hidden; }}
                #timeline {{ display: flex; overflow-x: auto; height: 100vh; scroll-snap-type: x mandatory; gap: 15px; padding: 0 40px; }}
                #timeline::-webkit-scrollbar {{ height: 8px; }}
                #timeline::-webkit-scrollbar-thumb {{ background: #1b2836; border-radius: 10px; }}
                .year-col {{ flex: 0 0 380px; height: 100vh; background: var(--panel); overflow-y: auto; scroll-snap-align: start; border: 2px solid transparent; transition: 0.3s; position: relative; }}
                .year-col:hover {{ border-color: var(--accent); background: #111d29; }}
                .header {{ position: sticky; top: 0; background: rgba(13, 22, 31, 0.9); backdrop-filter: blur(15px); padding: 25px; text-align: center; font-size: 32px; font-weight: 900; z-index: 20; color: var(--accent); border-bottom: 1px solid #1b2836; }}
                .month-divider {{ padding: 12px 20px; background: linear-gradient(90deg, rgba(74, 144, 226, 0.1) 0%, transparent 100%); font-size: 13px; text-transform: uppercase; letter-spacing: 3px; color: var(--text-muted); margin-top: 30px; border-left: 4px solid var(--accent); }}
                .item {{ margin: 20px 15px; border-radius: 15px; overflow: hidden; background: #000; position: relative; cursor: pointer; box-shadow: 0 8px 24px rgba(0,0,0,0.5); }}
                img, video {{ width: 100%; display: block; border-radius: 15px; }}
                .media-icon {{ position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.5); border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-size: 12px; z-index: 5; }}
                .date-overlay {{ position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.8)); color: #fff; font-size: 11px; padding: 15px 10px 10px 10px; text-align: center; opacity: 0; transition: 0.3s; pointer-events: none; }}
                .item:hover .date-overlay {{ opacity: 1; }}
                #lightbox {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.95); z-index: 1000; display: none; align-items: center; justify-content: center; }}
                #lightbox.active {{ display: flex; }}
                .lightbox-content {{ max-width: 95vw; max-height: 95vh; object-fit: contain; border-radius: 8px; }}
            </style>
            </head><body>
                <div id="timeline"></div>
                <div id="lightbox" onclick="this.classList.remove('active'); this.innerHTML=''"></div>
                <script>
                    const data = {manifest_json};
                    const container = document.getElementById('timeline');
                    const rootPath = "{ROOT_PATH}";

                    function openLightbox(path, type) {{
                        const lb = document.getElementById('lightbox');
                        lb.innerHTML = type === 'video' 
                            ? `<video class="lightbox-content" controls autoplay src="${{path}}"></video>`
                            : `<img class="lightbox-content" src="${{path}}">`;
                        lb.classList.add('active');
                    }}

                    const years = {{}};
                    Object.keys(data).forEach(f => {{ 
                        const y = f.substring(0,4); 
                        if(!years[y]) years[y]=[]; 
                        years[y].push(f); 
                    }});

                    // --- CHANGE HERE: Sort Years Descending (Newest on Left) ---
                    Object.keys(years).sort().reverse().forEach(year => {{
                        const col = document.createElement('div');
                        col.className = 'year-col';
                        col.innerHTML = `<div class="header">${{year}}</div>`;
                        
                        // Keep Months Ascending (Jan -> Dec)
                        years[year].sort().forEach(folder => {{
                            const monthName = new Date(year, parseInt(folder.substring(4,6))-1).toLocaleString('default', {{ month: 'long' }});
                            const monthDiv = document.createElement('div');
                            monthDiv.className = 'month-divider';
                            monthDiv.innerText = monthName;
                            col.appendChild(monthDiv);
                            
                            data[folder].forEach(fileObj => {{
                                const div = document.createElement('div');
                                div.className = 'item';
                                const mediaPath = `${{rootPath}}/stories/${{folder}}/${{fileObj.name}}`;
                                const isVideo = ['mp4', 'mov'].includes(fileObj.name.split('.').pop().toLowerCase());
                                div.innerHTML = `<div class="media-icon">${{isVideo ? '▶' : '📷'}}</div>`;
                                if (isVideo) {{
                                    const vid = document.createElement('video');
                                    vid.muted = true; vid.loop = true; vid.src = mediaPath + "#t=0.1";
                                    div.onmouseenter = () => vid.play();
                                    div.onmouseleave = () => {{ vid.pause(); vid.currentTime = 0.1; }};
                                    div.onclick = () => openLightbox(mediaPath, 'video');
                                    div.appendChild(vid);
                                }} else {{
                                    const img = document.createElement('img');
                                    img.src = mediaPath; img.loading = "lazy";
                                    div.onclick = () => openLightbox(mediaPath, 'image');
                                    div.appendChild(img);
                                }}
                                const dateTag = document.createElement('div');
                                dateTag.className = 'date-overlay';
                                dateTag.innerText = fileObj.date;
                                div.appendChild(dateTag);
                                col.appendChild(div);
                            }});
                        }});
                        container.appendChild(col);
                    }});
                </script>
            </body></html>
            """
            self.wfile.write(html.encode('utf-8'))

    def serve_media(self, requested_path, prefix):
        rel_path = requested_path[len(prefix):].lstrip('/')
        actual_file = os.path.join(os.environ["ARCHIVE_PATH"], "stories", rel_path)
        if os.path.exists(actual_file) and os.path.isfile(actual_file):
            self.send_response(200)
            ctype, _ = mimetypes.guess_type(actual_file)
            self.send_header('Content-type', ctype or 'application/octet-stream')
            self.end_headers()
            with open(actual_file, 'rb') as f: self.wfile.write(f.read())
        else: self.send_error(404)

def run_server():
    mimetypes.init()
    if os.getenv("ARCHIVE_PATH"):
        pre_convert(os.path.join(os.environ["ARCHIVE_PATH"], "stories"))
    
    # This is the key line to fix the "Address already in use" error
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), ArchiveHandler) as httpd:
        assigned_port = httpd.socket.getsockname()[1]
        print(f"🚀 Server Active at http://localhost:{assigned_port}{ROOT_PATH}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.server_close() # Explicitly close the socket

if __name__ == "__main__":
    run_server()