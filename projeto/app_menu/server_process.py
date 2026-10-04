"""Arranque e paragem dos servidores locais criados pelo menu."""

import os
from pathlib import Path
import socket
import subprocess
import xml.etree.ElementTree as ET

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
RUNTIME_DIR = APP_DIR / "runtime"


def find_executable():
    build = PROJECT_DIR / "stk-code" / "build-server"
    for path in build.rglob("supertuxkart"):
        if path.is_file() and os.access(path, os.X_OK):
            return path
    raise OSError("Compila primeiro o STK: executável ausente em stk-code/build-server.")


def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
        except OSError as error:
            raise OSError(f"Porta UDP {port} ocupada: {error}") from error


class Servers:
    def __init__(self):
        self.running = []

    def start(self, servers):
        local_index = None
        addresses = set()
        for index, server in enumerate(servers):
            server["local"] = False
            try:
                address = socket.gethostbyname(server["ip"])
            except OSError:
                # O viewer mostra erros de DNS sem impedir os outros servidores.
                continue
            if address in addresses:
                raise ValueError("Usa um endereço diferente para cada servidor.")
            addresses.add(address)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                try:
                    sock.bind((address, 0))
                    server["local"] = True
                except OSError:
                    pass
            if server["local"]:
                if local_index is not None:
                    raise ValueError("Só pode existir um servidor local. Usa outros computadores para os restantes.")
                local_index = index
            else:
                print("[STK] Servidor remoto:", server["label"], server["ip"], "(iniciar nesse computador)")
        if local_index is None:
            return

        server = servers[local_index]
        executable = find_executable()
        for port in (2759, 2757, 9998):
            check_port(port)
        template = PROJECT_DIR / "necessary_files" / "for_server" / "my.xml"
        RUNTIME_DIR.mkdir(exist_ok=True)
        try:
            tree = ET.parse(template)
            for tag, value in (("server-name", server["label"]),
                               ("server-port", "2759"),
                               ("wan-server", "false"), ("enable-console", "true")):
                tree.getroot().find(tag).set("value", value)
            config = RUNTIME_DIR / "local_server.xml"
            tree.write(config, encoding="utf-8", xml_declaration=True)
            savedir = RUNTIME_DIR / "local_server_user"
            savedir.mkdir(exist_ok=True)
            environment = os.environ.copy()
            environment["SUPERTUXKART_DATADIR"] = str(PROJECT_DIR / "stk-code")
            environment["SUPERTUXKART_ASSETS_DIR"] = str(PROJECT_DIR / "stk-assets")
            environment["SUPERTUXKART_SAVEDIR"] = str(savedir) + os.sep
            log_path = RUNTIME_DIR / "local_server.log"
            command = [str(executable), f"--server-config={config}",
                       f"--lan-server={server['label']}", "--port=2759", "--network-console"]
            with log_path.open("w") as log:
                process = subprocess.Popen(command, cwd=RUNTIME_DIR, env=environment,
                                           stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
            self.running.append({"process": process, "label": server["label"],
                                 "index": local_index, "log": log_path, "reported": False})
            server["game_port"] = 2759
            print("[STK] Servidor local:", command, "log:", log_path)
        except (OSError, ET.ParseError, AttributeError) as error:
            self.stop()
            raise OSError(f"Erro ao iniciar servidor local: {error}") from error

    def check(self, states):
        for entry in self.running:
            index = entry["index"]
            code = entry["process"].poll()
            if code is not None and not entry["reported"]:
                entry["reported"] = True
                with entry["log"].open("rb") as log:
                    log.seek(0, 2)
                    log.seek(max(0, log.tell() - 2000))
                    detail = log.read().decode(errors="replace")
                message = f"{entry['label']}: STK terminou (código {code}). Ver {entry['log']}"
                print("[ERRO STK]", message, detail)
                if index < len(states):
                    states[index]["error"] = message
                return message
        return ""

    def stop_server(self, index):
        entry = self.running[index]
        process = entry["process"]
        if process.poll() is None:
            print("[STK] Parar", entry["label"], "PID", process.pid)
            process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdin:
            process.stdin.close()
        entry["reported"] = True

    def stop(self):
        for index in range(len(self.running)):
            self.stop_server(index)
        self.running = []
