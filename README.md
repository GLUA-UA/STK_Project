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

## Preparar e abrir o menu

Requisitos: Python 3, `pygame-ce` 2.5.7 ou superior e as pistas em
`projeto/stk-assets/tracks/`. Para receber dados, precisas do servidor STK
modificado descrito abaixo. O menu não inicia o servidor STK.

Se já tens uma `.venv` a funcionar, usa-a. Para criar uma pela primeira vez,
na raiz do repositório:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install "pygame-ce>=2.5.7"
```

O `pygame-ce` fornece o módulo `pygame`, incluindo o carregamento de SVG e o
suporte Retina usado pelo menu. Não instales `pygame` e `pygame-ce` juntos
na mesma venv. Os SVG originais ficam em `app_menu/images/`; não é necessário
CairoSVG.

Para abrir o menu, na raiz do repositório:

```bash
.venv/bin/python projeto/app_menu/app_menu.py
```

1. Escolhe 1, 2 ou 4 servidores e indica os nomes e IPs ou endereços.
2. Em **Configurar grupos**, indica os participantes, os nomes e o número de
   grupos. Usa **Randomizar** para distribuir os nomes preenchidos.
3. Volta ao menu e usa **Iniciar mapa** com o servidor STK já a correr.
4. **Voltar**, Escape ou fechar a janela guarda a classificação atual em
   `projeto/pontuacoes/`. Escape no menu fecha a aplicação.

Os nomes dos servidores no menu identificam os mapas e os ficheiros de
pontuações; não alteram o nome configurado no servidor STK. Os grupos ficam
apenas em memória e não são enviados ao STK. Usa a roda do rato para percorrer
participantes, grupos ou classificações que não caibam no ecrã.

Em **Configurar grupos**, podes preparar entre 2 e 32 campos de participantes
e escolher entre 1 e 16 grupos. Só os nomes preenchidos entram na distribuição;
são necessários pelo menos dois. Os resultados aparecem no ecrã e no terminal.
Esta é a ferramenta atual de organização de grupos do projeto.

Mantém o terminal aberto para acompanhar os servidores selecionados, os pedidos
UDP, a primeira receção de dados, as pistas, os novos jogadores e os erros.
O menu não imprime cada pacote nem inicia corridas: estas são iniciadas no STK.

O código do menu está dividido em três ficheiros:

- `app_menu.py`: eventos, navegação e organização dos participantes.
- `menu_ui.py`: botões, campos, SVG e desenho dos ecrãs.
- `stk_viewer.py`: UDP, leitura de pistas e gravação de pontuações.

Para mudar os nomes dos botões, começa em `MenuApp.__init__` no `app_menu.py`.
Os ecrãs estão nas funções `draw_menu`, `draw_groups` e `draw_viewer` do
`menu_ui.py`. O formato dos pacotes está em `parse_packet` no `stk_viewer.py`.

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

## Rede

No menu, escolhe o número de servidores e escreve os respetivos IPs ou
endereços. Usa um computador por servidor: a telemetria do STK usa portas
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
