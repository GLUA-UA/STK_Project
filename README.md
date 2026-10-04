# SuperTuxKart Live Map Toolkit

Este projecto nasceu para ajudar a acompanhar corridas de SuperTuxKart em tempo
real. A ideia e simples: o servidor do STK envia a posicao dos karts por UDP, e
o menu em Python mostra esses karts num mapa 2D com a classificação ao lado.
Também permite organizar participantes em grupos.

Foi feito principalmente a pensar em Linux, torneios locais, LAN parties,
projectores e computadores diferentes ligados na mesma rede. Os scripts Python
tambem devem correr em macOS, desde que tenhas Python e `pygame-ce`.

## O Que Esta Aqui

Os ficheiros principais estao dentro da pasta `projeto/`:

- `app_menu/` contém o menu para um, dois ou quatro servidores.
- `stk-code/` tem o codigo do SuperTuxKart modificado.
- `stk-assets/` tem as pistas e assets usados para desenhar os mapas.
- `pontuacoes/` guarda as classificações quando sais do mapa.

O ficheiro importante do lado do SuperTuxKart e:

```text
projeto/stk-code/src/modes/world.cpp
```

E nele que o STK foi alterado para enviar os dados dos jogadores.

## Como Isto Funciona

Durante a corrida, o STK envia mensagens com estes seis campos:

```text
track|nome|kart|x|z|pos
```

O script usa o `track` para abrir o mapa local em:

```text
projeto/stk-assets/tracks/<track_id>/quads.xml
```

Depois desenha a pista, coloca os jogadores nas coordenadas `x` e `z`, e ordena
a leaderboard usando o campo `pos`.

## Alteração ao SuperTuxKart

A única alteração intencional ao código do SuperTuxKart está em
`projeto/stk-code/src/modes/world.cpp`. Esta alteração envia por UDP os dados
necessários para o viewer da aplicação:

- pista atual
- nome do jogador
- kart
- posição X/Z
- posição na corrida

O viewer envia um pedido ao servidor STK na porta UDP **9998**. Depois de
receber esse pedido, o STK envia os dados da corrida para a porta UDP **9999**
da máquina onde está a correr a aplicação Python.

A aplicação usa estes dados para identificar a pista, desenhar o minimapa com
o `quads.xml` local e mostrar os jogadores e a classificação em tempo real.

Não substituas `world.cpp` pela versão original do SuperTuxKart: isso remove
a telemetria UDP e o viewer deixa de receber os dados da corrida.

## Dependências

### SuperTuxKart (Ubuntu / Pop!_OS)

Instala estas ferramentas e bibliotecas antes de compilar:

```bash
sudo apt update

sudo apt install -y \
    build-essential \
    cmake \
    pkg-config \
    git \
    libsdl2-dev \
    libjpeg-dev \
    libpng-dev \
    zlib1g-dev \
    libbluetooth-dev \
    libopenal-dev \
    libfreetype6-dev \
    libvorbis-dev \
    libogg-dev \
    libharfbuzz-dev \
    libcurl4-openssl-dev \
    libssl-dev \
    libsqlite3-dev
```

### Aplicação Python

Instala o Python e o suporte para ambientes virtuais:

```bash
sudo apt install -y python3 python3-venv python3-pip
```

Na raiz do repositório, cria a venv do menu e instala os pacotes Python:

```bash
cd projeto/app_menu
python3 -m venv .venv
source .venv/bin/activate
pip install pygame-ce numpy
```

Usa `pygame-ce`, não o pacote Ubuntu `python3-pygame`. O menu usa
`pygame.Window` e precisa do `pygame-ce` 2.5.7 ou superior.
Não instales `pygame` e `pygame-ce` juntos na mesma venv. Os SVG são carregados
pelo `pygame-ce`; não é necessário CairoSVG.

## Preparar e abrir o menu

Requisitos: Python 3, `pygame-ce` 2.5.7 ou superior e as pistas em
`projeto/stk-assets/tracks/`. Para receber dados, precisas do servidor STK
modificado descrito abaixo. **Assistir** inicia apenas o servidor configurado
como local. O menu não compila STK nem inicia a corrida dentro do lobby.

Se todos os servidores forem remotos, não precisas de compilar ou instalar STK
na máquina do menu. Podes usar o menu no Mac e o servidor no Pop!_OS.
Mantém as pistas em `projeto/stk-assets/tracks/` na máquina do menu.

Se já tens uma `.venv` a funcionar, podes continuar a usá-la.

Dentro de `projeto/app_menu/`, com a venv ativada:

```bash
python app_menu.py
```

Ou, sem ativar a venv:

```bash
.venv/bin/python app_menu.py
```

1. Escolhe 1, 2 ou 4 servidores e indica os nomes e IPs.
2. Em **Configurar grupos**, indica os participantes, os nomes e o número de
   grupos. Usa **Randomizar** para distribuir os nomes preenchidos.
3. Volta ao menu e usa **Assistir** para acompanhar os servidores. O servidor local
   é iniciado pelo menu; os remotos devem estar a correr nos seus computadores.
   **Assistir** mostra todos os servidores ao mesmo tempo: um mapa grande,
   dois lado a lado ou quatro numa grelha 2×2, cada um com a sua classificação.
4. **Voltar**, Escape ou fechar a janela usa `pkill supertuxkart` se o menu
   iniciou um servidor local e guarda a classificação atual em
   `projeto/pontuacoes/`. Escape no menu fecha a aplicação.

Cada IP identifica o computador de um servidor. O menu pode correr noutro
computador. Para um servidor local, escreve `127.0.0.1` ou `localhost`.
Para um servidor remoto, escreve o IP real do outro computador. O menu não
procura os IPs de rede desta máquina: qualquer outro endereço é tratado como
remoto. Só o servidor local é iniciado automaticamente, com o nome indicado.
Nos remotos, usa um IP numérico IPv4, não um nome de máquina.
Os remotos são iniciados manualmente nos respetivos computadores; os nomes no
menu identificam os seus mapas e pontuações, sem alterar o nome do STK remoto.

Um torneio de 2 ou 4 servidores não inicia 2 ou 4 processos nesta máquina.
Usa um computador por servidor, com no máximo um servidor local. Qualquer
entrada pode ser local, não apenas a primeira. Também podes usar só servidores
remotos. Usa IPs diferentes para cada servidor.

Os grupos ficam apenas em memória e não são enviados ao STK. Usa a roda do rato
para percorrer participantes, grupos ou classificações que não caibam no ecrã.

Em **Configurar grupos**, podes preparar entre 2 e 32 campos de participantes
e escolher entre 1 e 16 grupos. Só os nomes preenchidos entram na distribuição;
são necessários pelo menos dois. Os resultados aparecem no ecrã e no terminal.
Esta é a ferramenta atual de organização de grupos do projeto.

Mantém o terminal aberto para acompanhar os servidores selecionados, os pedidos
UDP, a primeira receção de dados, as pistas, os novos jogadores e os erros.
O menu não imprime cada pacote nem inicia corridas: estas são iniciadas no STK.

Só o servidor local gera uma configuração em
`projeto/app_menu/runtime/local_server.xml`, numa pasta ignorada pelo Git.
O XML é recriado ao iniciar o servidor local, com o nome e dificuldade atuais.
Não é lido para recuperar escolhas anteriores: as opções do menu ficam apenas
em memória. A referência `my.xml` não é alterada.

O menu procura o executável compilado em `projeto/stk-code/build-server/` e
inicia-o em segundo plano com `os.system`. Usa `--server-config` com o XML
gerado, `--lan-server` com o nome escolhido, `--port=2759` e `--network-console`.
Os caminhos e nomes são protegidos com `shlex.quote` para aceitar espaços.
As variáveis nativas `SUPERTUXKART_DATADIR` e `SUPERTUXKART_ASSETS_DIR` indicam
os dados e assets deste repositório. O STK usa a sua pasta de utilizador normal.
O menu não cria logs do servidor nem redireciona stdout/stderr: a saída aparece
no terminal. O STK pode criar os seus próprios logs na pasta de utilizador.
O jogo usa a porta 2759 e a descoberta LAN usa 2757. Cada computador STK
recebe pedidos de telemetria em 9998; o menu recebe as respostas em 9999.
Ao sair de uma sessão com servidor local, o menu executa `pkill supertuxkart`.
Este comando pode parar todos os processos SuperTuxKart que o utilizador tem
permissão para terminar nesta máquina, incluindo os iniciados fora do menu.
O projeto assume apenas uma instância local do STK. Sessões só com servidores
remotos não executam `pkill`, e os servidores dos outros computadores não são
parados. O menu não acompanha o processo nem confirma que ficou pronto.
Como o comando corre em segundo plano, falhas posteriores aparecem no terminal.

Sem dados de um remoto, confirma que está em corrida, que o IP está correto e
que a firewall permite UDP.

O código do menu está dividido em quatro ficheiros:

- `app_menu.py`: eventos, navegação e organização dos participantes.
- `menu_ui.py`: botões, campos, SVG e desenho dos ecrãs.
- `stk_viewer.py`: UDP, leitura de pistas e gravação de pontuações.
- `server_process.py`: configurações, arranque e paragem dos processos STK.

Para mudar os nomes dos botões, começa em `MenuApp.__init__` no `app_menu.py`.
Os ecrãs estão nas funções `draw_home`, `draw_groups` e `draw_viewer` do
`menu_ui.py`. O formato dos pacotes está em `parse_packet` no `stk_viewer.py`.

## Compilar o STK Modificado

O projecto precisa do SuperTuxKart compilado com a alteracao no `world.cpp`.
Na raiz do repositório, executa:

```bash
cd projeto/stk-code

cmake -S . -B build-server \
    -DCMAKE_BUILD_TYPE=Debug \
    -DNO_SHADERC=on

cmake --build build-server -j"$(nproc)"
```

Os avisos sobre `astc-encoder` e `libopenglrecorder` são opcionais e não
impedem a compilação. A falta de `libopenglrecorder` desativa o gravador do jogo.

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

## Dificuldade do servidor

Os níveis desta versão do STK são Novice (0), Intermediate (1), Expert (2)
e SuperTux (3). O campo de configuração é `server-difficulty`.

### Servidor local

No menu, clica no botão **Local: Novice** para percorrer os quatro níveis.
Escolhe antes de **Assistir**. O menu escreve o nível escolhido em
`app_menu/runtime/local_server.xml`, apenas para o servidor local.
O nível inicial é Novice, como na configuração de referência.

### Servidor remoto

O botão do menu não altera servidores remotos. Em cada computador remoto:

1. Instala as dependências e compila STK com os comandos acima.
2. Na raiz do repositório, copia a configuração:

   ```bash
   cp projeto/necessary_files/for_server/my.xml projeto/stk-code/build-server/my.xml
   ```

3. Edita essa cópia e escolhe o nível. Por exemplo, Expert:

   ```xml
   <server-difficulty value="2" />
   ```

   Mantém `<server-configurable value="false" />` para que o dono não altere
   a dificuldade no lobby.
4. Inicia o servidor nesse computador, usando o nome pretendido:

   ```bash
   cd projeto/stk-code/build-server
   ./bin/supertuxkart --server-config=my.xml --lan-server="GLUA Race 1" --network-console
   ```

5. Introduz o IP desse computador no menu Python e usa **Assistir**.

## Rede

No menu, escolhe o número de servidores e escreve os respetivos IPs.
Usa um computador por servidor: a telemetria do STK usa portas
fixas, pelo que vários servidores na mesma máquina entram em conflito.
Abre apenas um menu por computador para receber os dados.

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

Quando sais do mapa no menu, é guardada a classificação atual em:

```text
projeto/pontuacoes/
```

O menu cria ficheiros `app_viewer_<data>_<hora>.txt`, com o nome e IP de cada
servidor, a pista e os jogadores ordenados pela posição. Se dois ficheiros
forem guardados no mesmo segundo, acrescenta um número ao nome.

Isto e util para guardar um registo rapido do fim da corrida ou do estado da
leaderboard.

## Se Algo Nao Funcionar

Se a janela abrir mas nao aparecer mapa, normalmente ainda nao chegaram pacotes
do servidor, o IP esta errado, a firewall bloqueou as portas, ou a pista nao
existe em `stk-assets/tracks/`.

Se aparecer `Mapa indisponível`, confirma que existe o `quads.xml` da pista
recebida em `projeto/stk-assets/tracks/` e que o XML é válido.

Se aparecer `Address already in use`, já tens outro menu ou outro processo a
usar a porta `9999`.

Se nao aparecerem jogadores, confirma que estas mesmo a correr o STK compilado
com o `world.cpp` modificado. Um servidor normal do SuperTuxKart nao envia estes
dados UDP.

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
