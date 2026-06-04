# SuperTuxKart Live Map Toolkit

Este projecto nasceu para ajudar a acompanhar corridas de SuperTuxKart em tempo
real. A ideia e simples: o servidor do STK envia a posicao dos karts por UDP, e
os scripts em Python mostram esses karts num mapa 2D com uma leaderboard ao
lado.

Foi feito principalmente a pensar em Linux, torneios locais, LAN parties,
projectores e computadores diferentes ligados na mesma rede. Os scripts Python
tambem devem correr em macOS, desde que tenhas Python e `pygame`.

## O Que Esta Aqui

Os ficheiros principais estao dentro da pasta `projeto/`:

- `live_map.py` mostra um servidor.
- `live_map_duo.py` mostra dois servidores.
- `live_map_quad.py` mostra quatro servidores.
- `stk-code/` tem o codigo do SuperTuxKart modificado.
- `stk-assets/` tem as pistas e assets usados para desenhar os mapas.
- `pontuacoes/` guarda as classificacoes quando fechas os viewers.

O ficheiro importante do lado do SuperTuxKart e:

```text
projeto/stk-code/src/modes/world.cpp
```

E nele que o STK foi alterado para enviar os dados dos jogadores.

## Como Isto Funciona

Durante a corrida, o STK envia mensagens neste formato:

```text
track|nome|kart|x|z|pos
```

O script usa o `track` para abrir o mapa local em:

```text
projeto/stk-assets/tracks/<track_id>/quads.xml
```

Depois desenha a pista, coloca os jogadores nas coordenadas `x` e `z`, e ordena
a leaderboard usando o campo `pos`.

## Preparar o Python

Na raiz do repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install pygame
```

Se preferires, tambem podes instalar o `pygame` directamente no teu Python
normal.

## Compilar o STK Modificado

O projecto precisa do SuperTuxKart compilado com a alteracao no `world.cpp`.
Um fluxo normal e:

```bash
cd projeto/stk-code
cmake -S . -B build-server -DCMAKE_BUILD_TYPE=Debug -DNO_SHADERC=on
cmake --build build-server -j"$(nproc)"
```

Em macOS, troca o ultimo comando por:

```bash
cmake --build build-server -j"$(sysctl -n hw.ncpu)"
```

Se precisares de detalhes sobre dependencias do STK, ve:

```text
projeto/stk-code/INSTALL.md
```

## Arrancar o Servidor

Exemplo:

```bash
cd projeto/stk-code/build-server
./bin/supertuxkart --server-config=my.xml --lan-server=torneio1 --network-console
```

Ha uma configuracao de referencia em:

```text
projeto/necessary_files/for_server/my.xml
```

Se `my.xml` nao existir na tua pasta `build-server`, copia esse ficheiro para la
ou cria uma configuracao equivalente.

## Usar os Viewers

Para ver um servidor:

```bash
cd projeto
python3 live_map.py
```

Para ver dois servidores:

```bash
python3 live_map_duo.py
```

Para ver quatro servidores:

```bash
python3 live_map_quad.py
```

Se o servidor estiver noutro computador, muda o IP no topo do script. Nos
scripts multi-servidor, muda a lista `SERVER_CONFIGS`.

As portas usadas sao:

- `9998/udp` para o Python pedir dados ao STK.
- `9999/udp` para o STK enviar os dados de volta ao Python.

Se estiveres a usar computadores diferentes, confirma que a firewall deixa essas
portas passar.

Para descobrir o IP do servidor em Linux:

```bash
hostname -I
```

Em macOS:

```bash
ipconfig getifaddr en0
```

## Pontuacoes

Quando fechas um viewer, ele guarda a classificacao actual em:

```text
projeto/pontuacoes/
```

Isto e util para guardar um registo rapido do fim da corrida ou do estado da
leaderboard.

## Randomizador de Grupos

Tambem existe uma ferramenta simples para criar grupos aleatorios:

```bash
cd projeto/necessary_files
python3 randomizador_grupos.py
```

Ela e independente do STK. Serve so para ajudar a organizar participantes.

## Se Algo Nao Funcionar

Se a janela abrir mas nao aparecer mapa, normalmente ainda nao chegaram pacotes
do servidor, o IP esta errado, a firewall bloqueou as portas, ou a pista nao
existe em `stk-assets/tracks/`.

Se aparecer `Track nao encontrada`, o script recebeu uma pista que nao existe
localmente nos assets.

Se aparecer `Address already in use`, ja tens outro viewer ou outro processo a
usar a porta `9999`.

Se nao aparecerem jogadores, confirma que estas mesmo a correr o STK compilado
com o `world.cpp` modificado. Um servidor normal do SuperTuxKart nao envia estes
dados UDP.

## Notas

`projeto/necessary_files/make4_testing.py` nao e necessario para correr o
projecto. Era uma copia/teste antiga. O viewer de quatro servidores actual e:

```text
projeto/live_map_quad.py
```

`projeto/necessary_files/pontuacoes/` tambem nao e usado pelos scripts actuais.

## Licenca

Este projecto inclui e modifica codigo do SuperTuxKart. O SuperTuxKart esta sob
a licenca GNU GPLv3.

```text
projeto/stk-code/COPYING
```

## Agradecimento

Espero que este projecto ajude a criar bons momentos e que traga alguma
felicidade a este mundo em que vivemos.

Obrigado ao GLUA e a equipa por detras do STK :)

Obrigado a ti por jogares!
