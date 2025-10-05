#!/usr/bin/env python3
# src/ide/tac_server.py
"""
Servidor mínimo con modo --watch + SSE para notificaciones en tiempo real.
- Endpoints:
    /           -> UI (index.html from static/)
    /tac        -> input.cps.pretty_tac (texto)
    /raw        -> input.cps.raw_tac
    /logs       -> input.cps.server.log
    /events     -> Server-Sent Events (notifica "update" cuando TAC/logs cambian)
"""
import argparse
import os
import time
import subprocess
import threading
import urllib.parse
import queue
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    def __init__(self, server_address, RequestHandlerClass, pretty_path, raw_path, log_path):
        super().__init__(server_address, RequestHandlerClass)
        self.pretty_path = pretty_path
        self.raw_path = raw_path
        self.log_path = log_path
        self.sse_clients = []          # list of queues (one per client)
        self.sse_lock = threading.Lock()

    def broadcast_sse(self, event: str = "update", data: str = ""):
        """
        Envia un evento SSE a todos los clientes conectados.
        data será enviado como texto; escapamos saltos de linea por seguridad.
        """
        payload = data.replace("\n", "\\n")
        with self.sse_lock:
            # iterar sobre copia para que clientes que fallan no bloqueen
            for q in list(self.sse_clients):
                try:
                    q.put_nowait((event, payload))
                except queue.Full:
                    pass


class TACRequestHandler(SimpleHTTPRequestHandler):
    server_version = "TacServer/1.0"

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        if parsed.path in ("/", "/index.html"):
            return os.path.join(STATIC_DIR, "index.html")
        if parsed.path == "/tac":
            return self.server.pretty_path
        if parsed.path == "/raw":
            return self.server.raw_path
        if parsed.path == "/logs":
            return self.server.log_path
        # fall back to static dir for other files (css/js)
        rel = parsed.path.lstrip("/")
        return os.path.join(STATIC_DIR, rel)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/events":
            return self.handle_sse()
        return super().do_GET()

    def handle_sse(self):
        # registers a new SSE client and streams events until disconnect
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = queue.Queue(maxsize=10)
        with self.server.sse_lock:
            self.server.sse_clients.append(q)
        try:
            # send an initial ping
            init_msg = "connected"
            self.wfile.write(f"event: init\ndata: {init_msg}\n\n".encode("utf-8"))
            self.wfile.flush()
            while True:
                try:
                    event, payload = q.get(timeout=0.5)
                    # write SSE message
                    msg = f"event: {event}\ndata: {payload}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # send a keep-alive comment occasionally to avoid proxies timing out
                    # but don't send too often
                    self.wfile.write(b": keep-alive\n\n")
                    try:
                        self.wfile.flush()
                    except BrokenPipeError:
                        break
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            # cleanup client
            with self.server.sse_lock:
                try:
                    self.server.sse_clients.remove(q)
                except ValueError:
                    pass

    def log_message(self, format, *args):
        # Compact logging to stdout
        print("[http] " + format % args)


def run_server(port: int, input_path: str, watch: bool, autorun_cmd: str):
    base = input_path
    pretty = base + ".pretty_tac"
    raw = base + ".raw_tac"
    logf = base + ".server.log"

    # ensure static dir exists
    os.makedirs(STATIC_DIR, exist_ok=True)

    # limpiar logs y pretty al iniciar (evita residuos de ejecuciones previas)
    open(logf, "w", encoding="utf-8").close()
    # si quieres también limpiar pretty: uncomment:
    open(pretty, "w", encoding="utf-8").close()

    server = ThreadedHTTPServer(("", port), TACRequestHandler, pretty, raw, logf)
    print(f"[INFO] Servidor TAC corriendo en http://0.0.0.0:{port} (archivo: {input_path})")

    if watch:
        print("[INFO] Modo watch activo: detectando cambios y (re)generando TAC automáticamente.")
        watcher = FileWatcher(input_path, autorun_cmd, logf, server)
        watcher_thread = threading.Thread(target=watcher.run, daemon=True)
        watcher_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Servidor detenido por keyboard interrupt.")


class FileWatcher:
    """
    Observa el archivo fuente por cambios en mtime.
    Al detectar cambio, ejecuta autorun_cmd, vuelca salida a log_path
    y notifica al servidor para que haga broadcast SSE.
    """
    def __init__(self, input_path, autorun_cmd, log_path, server: ThreadedHTTPServer, poll_interval=0.8):
        self.input_path = input_path
        self.autorun_cmd = autorun_cmd
        self.log_path = log_path
        self.server = server
        self.poll_interval = poll_interval
        self.last_mtime = 0

    def _run_autorun(self):
        # append a header in the log to separate runs
        hdr = f"\n\n=== run at {time.ctime()} ===\n"
        with open(self.log_path, "a", encoding="utf-8") as L:
            L.write(hdr)
        try:
            # run command; capture stdout and stderr
            proc = subprocess.run(self.autorun_cmd, shell=True, cwd=os.getcwd(),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=300)
            out = proc.stdout or ""
            with open(self.log_path, "a", encoding="utf-8") as L:
                L.write(out + "\n")
            # notify clients that TAC/logs are updated
            # we try to read the pretty file to include small summary in payload
            summary = ""
            pretty_path = self.input_path + ".pretty_tac"
            if os.path.exists(pretty_path):
                try:
                    with open(pretty_path, "r", encoding="utf-8") as f:
                        # read first 6 lines as small preview
                        lines = [next(f).rstrip("\n") for _ in range(6)]
                        summary = "\\n".join(lines)
                except Exception:
                    summary = "(preview not available)"
            self.server.broadcast_sse(event="update", data=summary)
        except subprocess.TimeoutExpired as e:
            msg = f"[watch] autorun timed out: {e}"
            with open(self.log_path, "a", encoding="utf-8") as L:
                L.write(msg + "\n")
            self.server.broadcast_sse(event="error", data="timeout")
        except Exception as e:
            with open(self.log_path, "a", encoding="utf-8") as L:
                L.write(f"[watch] error running autorun: {e}\n")
            self.server.broadcast_sse(event="error", data=str(e))

    def run(self):
        # initial mtime if file exists
        if os.path.exists(self.input_path):
            self.last_mtime = os.path.getmtime(self.input_path)
        else:
            self.last_mtime = 0

        while True:
            try:
                if os.path.exists(self.input_path):
                    m = os.path.getmtime(self.input_path)
                    if m != self.last_mtime:
                        print(f"[watch] detectado cambio en {self.input_path} (mtime {m})")
                        self.last_mtime = m
                        # run autorun command
                        print(f"[watch] ejecutando: {self.autorun_cmd}")
                        self._run_autorun()
                time.sleep(self.poll_interval)
            except Exception as e:
                print("[watch] excepción:", e)
                time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Archivo fuente .cps (ej: input.cps)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Puerto HTTP")
    parser.add_argument("--watch", action="store_true", help="Regenerar TAC al detectar cambios en el archivo")
    parser.add_argument("--autorun-cmd", default="./scripts/run_tac_gen.sh", help="Comando que genera TAC (ej: scripts/run_tac_gen.sh)")
    args = parser.parse_args()
    run_server(args.port, args.input, args.watch, args.autorun_cmd)


if __name__ == "__main__":
    main()
