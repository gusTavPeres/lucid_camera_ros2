# Tutorial — Viewer: visualizar câmeras e LiDAR do Twizy

Guia genérico e completo para conectar qualquer máquina Linux ao PC do carro por cabo Ethernet e visualizar os tópicos ROS 2 (câmeras e LiDAR)
publicados pelos containers do `air_twizy_hardware`.

## Requisitos

- Ubuntu 22.04 e porta Ethernet.
- Docker instalado com o usuário no grupo `docker`.
- Cabo Ethernet.
- No carro, nada precisa ser instalado: o discovery server e os containers
  já sobem sozinhos no boot.

## Visão geral

```
máquina do viewer                 carro (PC)
~/twizy_viewer  ──cabo Ethernet──  porta enp6s0
10.250.0.2/30                      10.250.0.1/30 (fixo, já configurado)
      │                                 │
      └── Fast DDS SUPER_CLIENT ──────► discovery server 10.250.0.1:11811
                                        containers: air_twizy_camera,
                                        ouster_lidar, twizy
```

## Passo 1 — Construir a imagem Docker do viewer

Na máquina do viewer:

```bash
cd ~/twizy_viewer
./build.sh          # cria a imagem twizy_viewer:humble (~3 GB, uma vez só)
```

## Passo 2 — Conectar o cabo e identificar a interface

Conecte o cabo entre a máquina do viewer e a porta `enp6s0` do PC do carro

Descubra o nome da interface Ethernet da máquina:

```bash
ip -br link
```

Procure a interface que muda de `NO-CARRIER` para `UP` ao plugar o cabo
(ex.: `enp45s0`, `eth0`, `enx...` para adaptadores USB). Nos comandos
abaixo, substitua `IFACE` por esse nome.

## Passo 3 — Configurar o IP do cabo (uma vez, persistente)

```bash
sudo nmcli con add type ethernet ifname IFACE con-name twizy-cable \
    ipv4.method manual ipv4.addresses 10.250.0.2/30 \
    connection.autoconnect-priority 10
sudo nmcli con up twizy-cable
```

O lado do carro já está fixo em `10.250.0.1/30` — não altere nada lá.

## Passo 4 — Validar o link físico

```bash
ip -br addr show IFACE            # deve mostrar UP e 10.250.0.2/30
ping -c3 10.250.0.1               # deve responder < 1 ms
sudo ethtool IFACE | grep Speed   # deve mostrar 1000Mb/s
```

Se `Speed` mostrar `100Mb/s` ou `dmesg | grep IFACE` mostrar
`(downshifted)`, o cabo está ruim — troque antes de continuar.

## Passo 5 — Conferir o perfil Fast DDS

O arquivo `~/twizy_viewer/fastdds_super_client.xml` já vem pronto para a
topologia do cabo. Os dois campos que importam:

- `<address>10.250.0.1</address>` (dentro de `RemoteServer`): endereço do
  discovery server — o IP do carro no cabo. 
- `<interfaceWhiteList><address>10.250.0.2</address>`: o IP da **máquina do
  viewer** no cabo. Isso força o Fast DDS a usar somente a interface do cabo; sem a
  whitelist, ele anuncia todas as interfaces (WiFi, docker0, VPN) e os
  publishers do carro tentam entregar dados em endereços inalcançáveis —
  os tópicos até aparecem, mas nenhum dado chega.

Só edite esses campos se usar IPs diferentes dos deste tutorial.
Não use a variável `RMW_FASTRTPS_USE_QOS_FROM_XML` (causa erro
"Not enough memory in the buffer stream"); os scripts já usam
`FASTDDS_DEFAULT_PROFILES_FILE`, que é o caminho correto.

## Passo 6 — Usar

Todos os comandos abaixo rodam de dentro de `~/twizy_viewer`.

```bash
./check_topics.sh                            # lista tópicos e mede taxas
./view_cameras.sh                            # mosaico com as 6 câmeras
./view_one_camera.sh /camera/left/image_raw  # uma câmera (rqt_image_view)
./view_lidar.sh                              # RViz com a nuvem do LiDAR
```

Observações:

- A descoberta via cabo leva **10–15 s** num container recém-aberto. Se um
  script listar poucos tópicos logo de cara, aguarde e rode de novo.
- No mosaico, `q` ou `Esc` fecham a janela. Tiles em "aguardando" são
  câmeras sem publicação no momento.
- Para diagnóstico manual dentro do ambiente ROS:
  `./run_ros.sh "ros2 topic list --no-daemon --spin-time 12"`.


## Solução de problemas

**Nenhum tópico aparece**
1. `ping 10.250.0.1` funciona? Se não: cabo, IP (passo 3) ou carro desligado.
2. No carro: `docker ps` deve listar `discovery_server`, `air_twizy_camera`,
   `ouster_lidar` e `twizy`.
3. Aguarde 15 s e rode `./check_topics.sh` de novo.

**Tópicos aparecem, mas `hz`/viewer não recebem dados**
Quase sempre é estado degradado do discovery server (acumula clientes
mortos a cada sessão do viewer). No carro:

```bash
cd /home/air/tmp_simoes/air_twizy_hardware
docker restart discovery_server && sleep 5 && \
docker restart air_twizy_camera ouster_lidar twizy
```

**Importante:** nunca reiniciar apenas o `discovery_server` — clientes
Fast DDS do Humble não se re-registram em servidor reiniciado e todos os
tópicos somem até os containers clientes reiniciarem também.

**Um tile do mosaico congelou ou ficou em "aguardando"**
O nó daquela câmera respawnou no carro e o viewer perdeu a assinatura.
Feche a janela e rode `./view_cameras.sh` de novo.

**Link não sobe ou oscila (UP/DOWN em loop)**
Cabo ou conector ruim. Verifique com `sudo dmesg | grep IFACE` — mensagens
`Link is Up ... (downshifted)` seguidas de `Link is Down` confirmam.
Travar as duas pontas em 100 Mbps:

```bash
sudo nmcli con mod twizy-cable 802-3-ethernet.speed 100 \
    802-3-ethernet.duplex full 802-3-ethernet.auto-negotiate yes
sudo nmcli device reapply IFACE
```

Reverta com `802-3-ethernet.speed 0 802-3-ethernet.duplex "" ` após a troca.

**Rodar os viewers por SSH (janela abre na tela física da máquina)**

```bash
export DISPLAY=:0
export XAUTHORITY=$(ls /run/user/1000/.mutter-Xwaylandauth.* 2>/dev/null | head -1)
cd ~/twizy_viewer && ./view_cameras.sh
```

## Alternativa via WiFi (sem cabo)

Funciona para poucos tópicos leves (limite prático ~75 Mbps, instável).
Edite `fastdds_super_client.xml`: `RemoteServer address` = IP WiFi do carro
e `interfaceWhiteList` = IP WiFi da máquina do viewer. Não serve para LiDAR nem
para várias câmeras simultâneas.
