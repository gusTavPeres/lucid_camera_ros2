# Receptor de stream em outra máquina

Ferramentas para receber o stream das câmeras em qualquer máquina Linux com
ROS2 Humble, via LAN ou VPN. O transmissor é o PC com as câmeras rodando o
`docker compose` deste repositório (Discovery Server na porta 11811).

Para o viewer do carro Twizy (cabo Ethernet dedicado), use
`docs/tutorial-viewer.md` — o fluxo abaixo é para o streaming genérico
multi-máquina deste repositório.

## Pré-requisitos

- ROS2 Humble com `rmw_fastrtps_cpp`, `cv_bridge` e `image_transport`.
  - Ubuntu/Debian: instale os pacotes `ros-humble-*` correspondentes.
  - Fedora Kinoite/Silverblue: rode `bash setup_toolbox.sh` (cria um
    Toolbox Ubuntu 22.04 com tudo instalado) e entre com
    `toolbox enter ros2-humble`.
- Rota de rede até o transmissor (`ping <IP_DO_TRANSMISSOR>`).
- Profile FastDDS do assinante gerado para a interface de recepção:

```bash
./config/setup_fastdds.sh subscriber <interface>   # ex.: wt0, eth0, wlan0
```

- Firewall liberado para o tráfego DDS, se necessário:

```bash
sudo bash notebook_setup/setup_firewall_receiver.sh <SUBNET>   # ex.: 192.168.0.0/24
```

## Uso

Configure o ambiente (uma vez por terminal):

```bash
source notebook_setup/env.sh <IP_DO_TRANSMISSOR>:11811
```

Depois, qualquer ferramenta ROS2 funciona nesse terminal:

```bash
ros2 topic list --no-daemon
python3 notebook_setup/stream_viewer.py --topic /camera_1/image_new --compressed
ros2 run rqt_image_view rqt_image_view
```

Ou use o atalho que abre o viewer (e opcionalmente grava):

```bash
export ROS_DISCOVERY_SERVER=<IP_DO_TRANSMISSOR>:11811
bash notebook_setup/start_receiver.sh /camera_1/image_new
bash notebook_setup/start_receiver.sh /camera_1/image_new --record --duration 60
```

## Solução de problemas

- **Nenhum tópico aparece:** confira `ROS_DOMAIN_ID` (deve ser o mesmo do
  transmissor, padrão 0), o `ROS_DISCOVERY_SERVER` e se o profile
  `config/fastdds_subscriber.xml` foi gerado para a interface certa.
- **Sempre use `--no-daemon`** nos comandos `ros2` — o daemon interfere com
  o Discovery Server (o `env.sh` já para o daemon automaticamente).
- **Stream com lag:** prefira os tópicos `*/compressed` (JPEG), que usam
  uma fração da banda do stream RAW.
- **Janela não abre (Toolbox/container):** rode `xhost +local:` no host.
