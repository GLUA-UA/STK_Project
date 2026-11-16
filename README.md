# SuperTuxKart Live Map Toolkit

Aplicação Python central do GLUA para acompanhar 1, 2 ou 4 servidores STK
modificados, com minimapa, jogadores e classificação em tempo real.

## App setup

Na raiz do repositório:

```bash
cd projeto/app_menu
python3 -m venv .venv
source .venv/bin/activate
pip install pygame-ce numpy
python app_menu.py
```

Usa `pygame-ce`, não `python3-pygame`. Se todos os servidores forem remotos,
não precisas de compilar STK na máquina da app.

## Server addresses

- **Local:** `127.0.0.1` ou `localhost`. A app inicia o servidor ao carregar em
  **Assistir**, desde que já esteja compilado.
- **Remoto:** IPv4 numérico do outro computador, por exemplo `192.168.1.20`.
  O servidor deve estar a correr antes de carregar em **Assistir**.

Podes ter no máximo um servidor local. Os restantes correm noutros computadores.
Ao sair de uma sessão local, `pkill supertuxkart` pode parar outros STK nessa máquina.

## Server-only clone

Para uma máquina que só vai correr o servidor:

```bash
git clone --filter=blob:none --sparse https://github.com/GLUA-UA/STK_Project.git STK_Server
cd STK_Server
git sparse-checkout set \
    projeto/stk-code \
    projeto/stk-assets \
    projeto/necessary_files
```

`projeto/stk-code/src/modes/world.cpp` já contém a telemetria do projeto:
não precisas de copiar nada; `necessary_files/world.cpp` é apenas uma referência.

## Build server on Linux

Em Ubuntu / Pop!_OS:

```bash
sudo apt update
sudo apt install -y \
    build-essential cmake pkg-config git \
    libsdl2-dev libjpeg-dev libpng-dev zlib1g-dev libbluetooth-dev \
    libopenal-dev libfreetype6-dev libvorbis-dev libogg-dev libharfbuzz-dev \
    libcurl4-openssl-dev libssl-dev libsqlite3-dev
```

Na raiz do repositório:

```bash
cd projeto/stk-code
cmake -S . -B build-server \
    -DCMAKE_BUILD_TYPE=Debug \
    -DNO_SHADERC=on
cmake --build build-server -j"$(nproc)"
```

Executável: `projeto/stk-code/build-server/bin/supertuxkart`.
Avisos de falta de `astc-encoder` ou `libopenglrecorder` não bloqueiam este build.

## Build server on macOS

Com Homebrew instalado, instala as ferramentas e dependências:

```bash
xcode-select --install
brew install cmake pkg-config git sdl2 jpeg-turbo libpng zlib \
    openal-soft freetype libvorbis libogg harfbuzz curl openssl@3 sqlite libsamplerate
```

Na raiz do repositório:

```bash
cd projeto/stk-code
cmake -S . -B build-server \
    -DCMAKE_BUILD_TYPE=Debug \
    -DNO_SHADERC=on \
    -DCMAKE_PREFIX_PATH="$(brew --prefix);$(brew --prefix openssl@3)" \
    -DOPENSSL_ROOT_DIR="$(brew --prefix openssl@3)" \
    -DCMAKE_CXX_FLAGS="-I$(brew --prefix openssl@3)/include"
cmake --build build-server -j"$(sysctl -n hw.ncpu)"
```

Executável: `projeto/stk-code/build-server/bin/supertuxkart.app/Contents/MacOS/supertuxkart`.

## Server difficulty

- 0 = Novice
- 1 = Intermediate
- 2 = Expert
- 3 = SuperTux

**Local:** seleciona a dificuldade na app.

**Remoto:** depois de compilar, cria a configuração na primeira utilização.
Na raiz do repositório:

```bash
cp projeto/necessary_files/my.xml projeto/stk-code/build-server/my.xml
```

Edita `projeto/stk-code/build-server/my.xml` antes de iniciar ou reiniciar o
servidor. Por exemplo, para Expert:

```xml
<server-difficulty value="2" />
```

## Start a remote server

Executa no computador do servidor, a partir da raiz do repositório.
Muda `GLUA Race 1` para o nome desejado.

**Linux:**

```bash
cd projeto/stk-code
SUPERTUXKART_DATADIR="$PWD" \
SUPERTUXKART_ASSETS_DIR="$PWD/../stk-assets" \
./build-server/bin/supertuxkart \
    --server-config="$PWD/build-server/my.xml" \
    --lan-server="GLUA Race 1" \
    --port=2759 \
    --network-console
```

**macOS:**

```bash
cd projeto/stk-code
SUPERTUXKART_DATADIR="$PWD" \
SUPERTUXKART_ASSETS_DIR="$PWD/../stk-assets" \
./build-server/bin/supertuxkart.app/Contents/MacOS/supertuxkart \
    --server-config="$PWD/build-server/my.xml" \
    --lan-server="GLUA Race 1" \
    --port=2759 \
    --network-console
```

Mantém o terminal aberto. Na app central, indica o IPv4 desse computador e
carrega em **Assistir**. Inicia a corrida no STK para receber dados.

## How it works

- App para servidor: UDP 9998.
- Servidor para app: UDP 9999.

O `world.cpp` modificado envia:

```text
track|name|kart|x|z|race_position
```

A app usa os `stk-assets` locais para desenhar o minimapa.

## Common problems

- **Sem dados:** confirma o IP, se a corrida começou e se o servidor foi
  compilado com o `world.cpp` deste projeto.
- **Mapa indisponível:** confirma que tens a pista em `projeto/stk-assets/tracks/`.
- **Porta ocupada:** verifica as portas UDP 9998, 9999 e 2759.
- **Problema de build no macOS:** confirma que as dependências correspondem à
  arquitetura do Mac, sem misturar Intel e Apple Silicon.
