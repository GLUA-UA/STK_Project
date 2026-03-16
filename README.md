# SuperTuxKart Live Map

Este projeto adiciona suporte a um **mapa em tempo real para
SuperTuxKart**, mostrando a posição dos jogadores num mapa 2D durante
uma corrida.

O servidor STK foi modificado para enviar posições dos karts via
**UDP**, e um script em **Python + Pygame** recebe esses dados e mostra
o mapa.

------------------------------------------------------------------------

# Arquitetura

SuperTuxKart Server\
│\
│ UDP (porta 9999)\
▼\
Python Script (main2.py)\
│\
▼\
Mapa em tempo real (Pygame)

Formato das mensagens:

    track_id|player_name|kart_type|x|z

Exemplo:

    lighthouse|victor_m|tux|12.53|84.12

------------------------------------------------------------------------

# Requisitos

## Servidor

-   Linux
-   SuperTuxKart compilado a partir do código fonte
-   alteração no ficheiro:

```{=html}
<!-- -->
```
    src/modes/world.cpp

## Cliente (mapa)

-   Python 3
-   pygame

Instalar pygame:

    pip install pygame

------------------------------------------------------------------------

# Compilar o SuperTuxKart modificado

Dentro da pasta do STK:

    mkdir build
    cd build
    cmake ..
    make -j$(nproc)

O executável ficará em:

    bin/supertuxkart

------------------------------------------------------------------------

# Iniciar o servidor

Executar:

    ./bin/supertuxkart --server-config=server_config.xml

ou iniciar uma corrida normalmente no jogo.

------------------------------------------------------------------------

# Executar o mapa

Na pasta do projeto:

    python3 main2.py

Isto abre uma janela pygame com o mapa.

------------------------------------------------------------------------

# Configuração do IP

No ficheiro:

    main2.py

existe esta variável:

    IP_DO_SERVIDOR = "127.0.0.1"

Este valor depende de onde o servidor está a correr.

------------------------------------------------------------------------

## Caso 1 --- servidor e mapa no mesmo PC

Usar:

    IP_DO_SERVIDOR = "127.0.0.1"

ou

    IP_DO_SERVIDOR = "localhost"

------------------------------------------------------------------------

## Caso 2 --- servidor em outro PC

Descobrir o IP do servidor:

    ip a

ou

    hostname -I

Exemplo:

    192.168.1.85

Depois alterar no `main2.py`:

    IP_DO_SERVIDOR = "192.168.1.85"

------------------------------------------------------------------------

# Portas usadas

  Porta   Função
  ------- ------------------------------
  9998    pedido de ligação do mapa
  9999    envio das posições dos karts

------------------------------------------------------------------------

# Como funciona a ligação

1.  O script Python envia

```{=html}
<!-- -->
```
    MAP_CONNECT

para o servidor na porta **9998**.

2.  O servidor regista o cliente.

3.  O servidor começa a enviar posições dos karts via **UDP (9999)**.

------------------------------------------------------------------------

# Problemas comuns

## O mapa não mostra jogadores

Verificar se o servidor registou o cliente.

No terminal do STK deve aparecer:

    [MAPA] Novo cliente registrado: ...

------------------------------------------------------------------------

## Firewall

Garantir que as portas estão abertas:

    sudo firewall-cmd --add-port=9998/udp
    sudo firewall-cmd --add-port=9999/udp

------------------------------------------------------------------------

## Pygame não encontrado

Instalar pygame:

    pip install pygame

------------------------------------------------------------------------

# Melhorias possíveis

-   rotação do kart
-   velocidade
-   posição na corrida
-   radar estilo spectator
-   suporte a múltiplos clientes

------------------------------------------------------------------------

# Licença

Este projeto utiliza o código do **SuperTuxKart**, licenciado sob
**GPLv3**.
