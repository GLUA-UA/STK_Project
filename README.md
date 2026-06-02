# SuperTuxKart Live Map Toolkit

Este projecto adiciona uma camada de mapa em tempo real e leaderboard a um
servidor modificado do SuperTuxKart.

Os scripts em Python recebem dados UDP enviados pelo SuperTuxKart, desenham os
karts num mapa 2D da pista actual e guardam a classificacao quando a janela e
fechada.

O foco principal deste projecto e Linux. Tambem deve funcionar em macOS para os
scripts Python, desde que o SuperTuxKart modificado consiga ser compilado nesse
sistema.

## Estrutura do Projecto

| Caminho | Funcao |
| --- | --- |
| `projeto/live_map.py` | Cliente principal para ver um servidor. |
| `projeto/live_map_duo.py` | Dashboard para dois servidores. |
| `projeto/live_map_quad.py` | Dashboard para ate quatro servidores. |
| `projeto/stk-code/` | Codigo-fonte do SuperTuxKart com a alteracao UDP. |
| `projeto/stk-assets/` | Assets do SuperTuxKart usados para desenhar as pistas. |
| `projeto/stk-code/src/modes/world.cpp` | Ficheiro do STK alterado para enviar telemetria por UDP. |
| `projeto/necessary_files/for_server/` | Copias de referencia de ficheiros uteis para o servidor. |
| `projeto/necessary_files/randomizador_grupos.py` | Ferramenta opcional para criar grupos aleatorios. |
| `projeto/pontuacoes/` | Classificacoes guardadas pelos scripts. |

## Como Funciona

O SuperTuxKart modificado envia uma mensagem UDP por cada kart durante a corrida.
O script Python recebe essas mensagens e procura a pista localmente em:

```text
projeto/stk-assets/tracks/<track_id>/quads.xml
```

Depois transforma esse ficheiro num mapa 2D e desenha os jogadores por cima.

Formato actual da mensagem UDP:

```text
track|nome|kart|x|z|pos
```

Exemplo:

```text
lighthouse|player1|tux|12.53|84.12|2
```

Campos:

| Campo | Significado |
| --- | --- |
| `track` | Identificador da pista no SuperTuxKart. |
| `nome` | Nome do jogador/controlador. |
| `kart` | Identificador do kart. |
| `x` | Coordenada X no mundo do STK. |
| `z` | Coordenada Z no mundo do STK. |
| `pos` | Posicao actual na corrida. |

## Requisitos

Para os scripts Python:

- Python 3
- `pygame`
- Pasta `projeto/stk-assets/`
- Acesso de rede ao computador que corre o servidor STK

Para o servidor:

- Codigo modificado em `projeto/stk-code/`
- CMake
- Compilador C++
- Dependencias normais do SuperTuxKart para Linux ou macOS

As dependencias exactas do SuperTuxKart dependem do sistema. Para mais detalhe,
consulta:

```text
projeto/stk-code/INSTALL.md
projeto/stk-code/README.md
```

## Instalar Dependencias Python

Na raiz do repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pygame
```

Se nao quiseres usar ambiente virtual, podes instalar o `pygame` directamente no
teu Python normal.

## Compilar o SuperTuxKart Modificado

Fluxo geral:

```bash
cd projeto/stk-code
cmake -S . -B build-server -DCMAKE_BUILD_TYPE=Debug -DNO_SHADERC=on
cmake --build build-server
```

Em Linux, podes acelerar a compilacao com:

```bash
cmake --build build-server -j"$(nproc)"
```

Em macOS:

```bash
cmake --build build-server -j"$(sysctl -n hw.ncpu)"
```

O executavel fica normalmente em:

```text
projeto/stk-code/build-server/bin/
```

## Arrancar o Servidor STK

Exemplo:

```bash
cd projeto/stk-code/build-server
./bin/supertuxkart --server-config=my.xml --lan-server=torneio1 --network-console
```

Existe uma configuracao de referencia em:

```text
projeto/necessary_files/for_server/my.xml
```

Se `my.xml` nao existir na pasta `build-server`, copia esse ficheiro ou cria uma
configuracao equivalente.

## Portas UDP

O `world.cpp` modificado usa portas fixas:

| Porta | Direccao | Funcao |
| --- | --- | --- |
| `9998/udp` | Python para STK | O cliente envia `MAP_CONNECT`. |
| `9999/udp` | STK para Python | O servidor envia posicoes dos karts. |

Se o servidor e o cliente estiverem em computadores diferentes, confirma que a
firewall permite estas portas UDP.

## Usar o Cliente de Um Servidor

```bash
cd projeto
python3 live_map.py
```

Por defeito, o script usa:

| Opcao | Valor |
| --- | --- |
| IP do servidor | `127.0.0.1` |
| Porta do servidor | `9998` |
| Porta local do cliente | `9999` |

Se o servidor STK estiver noutro computador, altera `SERVER_IP` no topo de
`projeto/live_map.py`.

## Usar os Dashboards Multi-Servidor

Para dois servidores:

```bash
cd projeto
python3 live_map_duo.py
```

Para ate quatro servidores:

```bash
cd projeto
python3 live_map_quad.py
```

Antes de executar, edita `SERVER_CONFIGS` no topo do script.

Exemplo para `live_map_duo.py`:

```python
UDP_PORT = 9999

SERVER_CONFIGS = [
    {"label": "Servidor 1", "server_ip": "127.0.0.1", "server_port": 9998},
    {"label": "Servidor 2", "server_ip": "192.168.1.20", "server_port": 9998},
]
```

Exemplo para `live_map_quad.py`:

```python
SERVER_CONFIGS = [
    {"label": "Servidor 1", "server_ip": "127.0.0.1", "server_port": 9998, "client_port": 9999},
    {"label": "Servidor 2", "server_ip": "192.168.1.20", "server_port": 9998, "client_port": 9999},
]
```

O importante e:

| Campo | Significado |
| --- | --- |
| `label` | Nome que aparece no dashboard. |
| `server_ip` | IP do computador que corre esse servidor STK. |
| `server_port` | Porta UDP onde o STK recebe `MAP_CONNECT`. |
| `client_port` | Porta UDP local usada pelo dashboard `live_map_quad.py`. |

Os dashboards usam uma porta local partilhada, normalmente `9999`.

## Janelas Redimensionaveis

As janelas dos scripts principais podem ser redimensionadas:

- `live_map.py`
- `live_map_duo.py`
- `live_map_quad.py`
- `necessary_files/randomizador_grupos.py`

O conteudo escala com o tamanho da janela. Isto ajuda quando o projecto e usado
em portateis, monitores externos, projectores ou ecras com resolucoes diferentes.

## Descobrir o IP do Servidor

Linux:

```bash
hostname -I
```

macOS:

```bash
ipconfig getifaddr en0
```

Usa o IP da rede onde tambem esta o computador que vai correr o script Python.

## Firewall

Em Linux, se necessario:

```bash
sudo firewall-cmd --add-port=9998/udp
sudo firewall-cmd --add-port=9999/udp
```

Em macOS, aceita o pedido de permissao de rede se o sistema mostrar uma janela.

## Guardar Pontuacoes

Quando fechas `live_map.py`, `live_map_duo.py` ou `live_map_quad.py`, o script guarda a
classificacao actual em:

```text
projeto/pontuacoes/
```

## Randomizador de Grupos

Esta ferramenta e opcional e nao precisa do servidor STK.

```bash
cd projeto/necessary_files
python3 randomizador_grupos.py
```

Serve para introduzir participantes e criar grupos aleatorios.

## Ficheiros Que Nao Sao Necessarios

`projeto/necessary_files/make4_testing.py` nao e necessario para correr o
projecto. Era uma copia/teste do dashboard de quatro servidores. O ficheiro activo
deve ser:

```text
projeto/live_map_quad.py
```

`projeto/necessary_files/pontuacoes/` tambem nao e necessario. Essa pasta so tem
ficheiros locais do macOS e nao e usada pelos scripts activos.

## Problemas Comuns

### A janela abre mas nao aparece mapa

Verifica:

- se a corrida ja comecou no servidor;
- se o IP do servidor esta correcto;
- se as portas UDP `9998` e `9999` estao livres;
- se a pista existe em `projeto/stk-assets/tracks/`.

### `Track nao encontrada`

O script recebeu uma pista que nao existe localmente em:

```text
projeto/stk-assets/tracks/<track_id>/quads.xml
```

Usa uma pista existente nos assets ou adiciona os assets em falta.

### `Address already in use`

Outro processo ja esta a usar a porta UDP, normalmente `9999`.

Fecha outro viewer aberto ou altera a porta no script e no codigo UDP do STK.

### Nao aparecem jogadores

Provavelmente o servidor que esta a correr nao foi compilado com o `world.cpp`
modificado. Um servidor normal do SuperTuxKart nao envia estes pacotes UDP.

## Fluxo Recomendado

1. Instalar Python 3 e `pygame`.
2. Compilar o SuperTuxKart modificado em `projeto/stk-code/`.
3. Copiar ou preparar `my.xml` na pasta `build-server`.
4. Arrancar o servidor STK.
5. Comecar uma corrida.
6. Executar `live_map.py`, `live_map_duo.py` ou `live_map_quad.py`.
7. Fechar a janela no fim para guardar a classificacao.

## Licenca

Este projecto inclui e modifica codigo do SuperTuxKart. O SuperTuxKart esta sob
a licenca GNU GPLv3.

Consulta:

```text
projeto/stk-code/COPYING
```

## Agradecimento

Espero que este projecto ajude a criar bons momentos e que traga alguma felicidade a este mundo em que vivemos.

Obrigado ao GLUA e à equipa por detrás do STK :)

Obrigado a ti por jogares!
