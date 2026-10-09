"""Arranque e paragem dos servidores locais criados pelo menu."""

import os
from pathlib import Path
import socket
import shlex
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


class LocalServer:
    def __init__(self):
        self.started = False

    def start(self, servers):
        local_server = None
        addresses = []
        for server in servers:
            ip = server["ip"]
            server["local"] = ip == "127.0.0.1" or ip == "localhost"
            if ip in addresses:
                raise ValueError("Usa um endereço diferente para cada servidor.")
            addresses.append(ip)
            if server["local"]:
                if local_server is not None:
                    raise ValueError("Só pode existir um servidor local. Usa outros computadores para os restantes.")
                local_server = server
            else:
                print("[STK] Servidor remoto:", server["label"], server["ip"], "(iniciar nesse computador)")
        if local_server is None:
            return

        server = local_server
        executable = find_executable()
        for port in (2759, 2757, 9998):
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                try:
                    sock.bind(("0.0.0.0", port))
                except OSError as error:
                    raise OSError(f"Porta UDP {port} ocupada: {error}") from error
        template = PROJECT_DIR / "necessary_files" / "my.xml"
        RUNTIME_DIR.mkdir(exist_ok=True)
        try:
            tree = ET.parse(template)
            root = tree.getroot()
            root.find("server-name").set("value", server["label"])
            root.find("server-port").set("value", "2759")
            root.find("server-difficulty").set("value", str(server["difficulty"]))
            root.find("wan-server").set("value", "false")
            root.find("enable-console").set("value", "true")
            config = RUNTIME_DIR / "local_server.xml"
            tree.write(config, encoding="utf-8", xml_declaration=True)
            data_dir = PROJECT_DIR / "stk-code"
            assets_dir = PROJECT_DIR / "stk-assets"
            command = "cd " + shlex.quote(str(RUNTIME_DIR)) + " && "
            command += "SUPERTUXKART_DATADIR=" + shlex.quote(str(data_dir)) + " "
            command += "SUPERTUXKART_ASSETS_DIR=" + shlex.quote(str(assets_dir)) + " "
            command += shlex.quote(str(executable))
            command += " --server-config=" + shlex.quote(str(config))
            command += " --lan-server=" + shlex.quote(server["label"])
            command += " --port=2759 --network-console"
            command += " &"
            print("[STK] Servidor local:", command)
            result = os.system(command)
            if result != 0:
                raise OSError("Não foi possível executar o comando STK.")
            self.started = True
            server["game_port"] = 2759
        except (OSError, ET.ParseError, AttributeError) as error:
            self.stop()
            raise OSError(f"Erro ao iniciar servidor local: {error}") from error

    def stop(self):
        if not self.started:
            return
        print("[STK] Parar servidores locais com pkill supertuxkart.")
        os.system("pkill supertuxkart")
        self.started = False
