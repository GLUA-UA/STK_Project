# SuperTuxKart Live Map Toolkit

Este projeto junta tres componentes em Python e uma alteracao no codigo do SuperTuxKart para acompanhar corridas e organizar torneios:

- `make3.py`: cliente simples para um servidor STK, com mapa em tempo real e leaderboard.
- `make3_quad.py`: dashboard para monitorizar ate 4 servidores em paralelo.
- `randomizador_grupos.py`: interface em `pygame` para criar grupos aleatorios de participantes.
- `stk-code/src/modes/world.cpp`: ponto onde o STK envia dados UDP para os clientes Python.

## Estrutura atual

Na raiz do projeto:

- [`make3.py`](/home/victor/Documents/GLUA/STK_Project/projeto/make3.py)
- [`make3_quad.py`](/home/victor/Documents/GLUA/STK_Project/projeto/make3_quad.py)
- [`randomizador_grupos.py`](/home/victor/Documents/GLUA/STK_Project/projeto/randomizador_grupos.py)
- [`stk-assets`](/home/victor/Documents/GLUA/STK_Project/projeto/stk-assets)
- [`stk-code`](/home/victor/Documents/GLUA/STK_Project/projeto/stk-code)
- [`pontuacoes`](/home/victor/Documents/GLUA/STK_Project/projeto/pontuacoes)

Ficheiros de configuracao de servidor STK usados neste projeto:

- [`stk-code/build-server/my.xml`](/home/victor/Documents/GLUA/STK_Project/projeto/stk-code/build-server/my.xml)
- [`stk-code/build-server/other.xml`](/home/victor/Documents/GLUA/STK_Project/projeto/stk-code/build-server/other.xml)

## Alteracao feita no STK

O STK foi alterado em [`stk-code/src/modes/world.cpp`](/home/victor/Documents/GLUA/STK_Project/projeto/stk-code/src/modes/world.cpp) para enviar dados de cada kart por UDP.

Formato atual do pacote:

```text
track|nome|kart|x|z|pos
```

Campos:

- `track`: identificador da pista atual
- `nome`: nome do jogador/controlador
- `kart`: identificador do kart
- `x`: coordenada X no mundo
- `z`: coordenada Z no mundo
- `pos`: posicao atual na corrida, usando a logica interna do STK

Exemplo:

```text
lighthouse|victor_m|tux|12.53|84.12|2
```

## Portas UDP usadas pela versao atual

A versao atual do `world.cpp` esta configurada com portas fixas:

- `9998/udp`: o cliente Python envia `MAP_CONNECT` para aqui
- `9999/udp`: o servidor STK envia os pacotes de volta para o cliente

Isto significa que, na versao atual do codigo, o fluxo esperado e o cliente Python e o servidor STK estarem alinhados com estas portas.

## Como os mapas sao obtidos

Os scripts Python nao descarregam mapas da rede.

O processo e este:

1. O STK envia o `track_id` no pacote UDP.
2. O script usa esse `track_id` para abrir localmente:

```text
stk-assets/tracks/<track_id>/quads.xml
```

3. O `quads.xml` e convertido para uma representacao 2D desenhada em `pygame`.

Se aparecer `Track nao encontrada` ou `Sem mapa recebido`, verifica:

- se ja chegaram pacotes UDP
- se o `track_id` existe em `stk-assets/tracks`
- se a pista usada no servidor e oficial ou existe localmente no teu PC

## Requisitos

### STK

- Linux
- codigo-fonte do STK em `stk-code`
- assets em `stk-assets`
- alteracao ativa em `stk-code/src/modes/world.cpp`

### Python

- Python 3
- `pygame`

Instalacao do `pygame`:

```bash
pip install pygame
```

## Compilar o STK

No teu caso, a build funcional esta em `stk-code/build-server`.

Comandos:

```bash
cd /home/victor/Documents/GLUA/STK_Project/projeto/stk-code/build-server
cmake .. -DCMAKE_BUILD_TYPE=Debug -DNO_SHADERC=on
cmake --build . -j"$(nproc)"
```

Executavel gerado:

```text
/home/victor/Documents/GLUA/STK_Project/projeto/stk-code/build-server/bin/supertuxkart
```

## Arrancar o servidor STK

Exemplo com o `my.xml`:

```bash
cd /home/victor/Documents/GLUA/STK_Project/projeto/stk-code/build-server
./bin/supertuxkart --server-config=my.xml --lan-server=pilinha --network-console
```

Segundo exemplo com `other.xml`:

```bash
cd /home/victor/Documents/GLUA/STK_Project/projeto/stk-code/build-server
./bin/supertuxkart --server-config=other.xml --lan-server=pilinha2 --network-console
```

## Usar o cliente simples: `make3.py`

Este e o cliente principal para um servidor.

Executar:

```bash
cd /home/victor/Documents/GLUA/STK_Project/projeto
python3 make3.py
```

O script:

- envia `MAP_CONNECT` para `127.0.0.1:9998`
- faz `bind` local em `9999`
- recebe os pacotes UDP
- mostra mapa e leaderboard
- guarda a classificacao atual ao fechar em `pontuacoes/`

### O que o `make3.py` faz

- aceita pacotes com `pos`
- usa `pos` na leaderboard quando existe
- mantem compatibilidade com pacotes antigos sem `pos`
- cria ficheiros de pontuacao ao fechar

## Usar o dashboard multi-servidor: `make3_quad.py`

Este script foi preparado para monitorizar ate 4 servidores em paralelo.

Executar:

```bash
cd /home/victor/Documents/GLUA/STK_Project/projeto
python3 make3_quad.py
```

Configuracao no topo do ficheiro:

```python
SERVER_CONFIGS = [
    {"label": "Server 1", "server_ip": "192.168.1.100", "server_port": 9998, "client_port": 10001},
    {"label": "Server 2", "server_ip": "192.168.1.101", "server_port": 9998, "client_port": 10002},
    {"label": "Server 3", "server_ip": "192.168.1.102", "server_port": 9998, "client_port": 10003},
    {"label": "Server 4", "server_ip": "192.168.1.103", "server_port": 9998, "client_port": 10004},
]
```

Ajusta:

- `label`: nome apresentado no painel
- `server_ip`: IP do PC que corre o servidor STK
- `server_port`: porta UDP do `world.cpp` desse servidor
- `client_port`: porta local usada por este dashboard

O `make3_quad.py` mostra, por servidor:

- nome do servidor
- pista atual
- mapa 2D da pista
- jogadores desenhados no mapa
- leaderboard no mesmo estilo visual do `make3.py`

Tambem guarda um resumo ao fechar em `pontuacoes/`.

## Usar o randomizador de grupos

Executar:

```bash
cd /home/victor/Documents/GLUA/STK_Project/projeto
python3 randomizador_grupos.py
```

Funcionalidades atuais:

- pede primeiro o numero de participantes
- cria apenas os campos necessarios
- randomiza os nomes em grupos
- interface toda em `pygame`

## Como descobrir o IP do teu servidor

Na mesma rede local:

```bash
hostname -I
```

ou

```bash
ip -4 addr show | grep inet
```

Se outro PC for usar o teu servidor no `make3_quad.py`, esse PC deve colocar o teu IP em `server_ip`.

## Problemas comuns

### `SDL2 not found`

Em Fedora, instala:

```bash
sudo dnf install SDL2-devel
```

### `Track nao encontrada`

O script recebeu um `track_id`, mas nao encontrou o `quads.xml` correspondente em `stk-assets/tracks/`.

### `Sem mapa recebido`

Nenhum pacote UDP chegou ainda desse servidor, ou o `track_id` ainda nao foi resolvido para um mapa local.

### `Sem jogadores recebidos`

O servidor ainda nao enviou karts desse painel, ou o cliente nao esta a receber pacotes desse servidor.

### Firewall

Se estiveres a usar rede local entre maquinas diferentes, confirma que as portas UDP estao acessiveis.

Exemplo em Fedora:

```bash
sudo firewall-cmd --add-port=9998/udp
sudo firewall-cmd --add-port=9999/udp
```

## Notas finais

- `make3.py` e o cliente simples principal.
- `make3_quad.py` e o dashboard multi-servidor.
- `randomizador_grupos.py` e independente do STK: serve apenas para organizar grupos de torneio.
- os ficheiros em `pontuacoes/` sao historicos gerados ao fechar os scripts de visualizacao.

## Licenca

O projeto usa codigo do SuperTuxKart, que esta sob GPLv3.
