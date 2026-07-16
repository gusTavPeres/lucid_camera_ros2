# Registro de alterações — carro Twizy e viewer (2026-07-03)

Registro completo do que foi alterado no PC do carro (`air@…`,
`/home/air/tmp_simoes/air_twizy_hardware`) e criado para o viewer, com o
motivo de cada mudança.

## Carro — rede (NetworkManager, persistente)

### Porta `enp6s0` virou o link do notebook

| propriedade | antes | depois |
|---|---|---|
| `ipv4.method` | link-local | manual `10.250.0.1/30` |
| `802-3-ethernet.mtu` | 9000 | 1500 |

Comando equivalente:

```bash
sudo nmcli con mod Camera_enp6s0 ipv4.method manual \
    ipv4.addresses 10.250.0.1/30 802-3-ethernet.mtu 1500
```

### Rota /32 de cada câmera no perfil da interface

Antes, as rotas host das câmeras eram criadas só pelo script de tuning no
boot, que corre contra a ativação das interfaces pelo NetworkManager —
resultado: câmeras inalcançáveis de forma intermitente após reboot. Além
disso, três perfis guardavam rotas de um mapeamento antigo errado
(`164.199→enp9s0`, `10.197→enp10s0`, `153.193→enp12s0`).

Agora cada perfil NM `Camera_enp*` tem a rota da sua câmera em
`ipv4.routes` (aplicada pelo NM em toda ativação, sem corrida):

| câmera    | serial    | IP              | interface | perfil NM       |
|-----------|-----------|-----------------|-----------|-----------------|
| left      | 243901924 | 169.254.7.198   | enp2s0    | Camera_enp2s0   |
| top_front | 243901980 | 169.254.81.234  | enp7s0    | Camera_enp7s0   |
| top_left  | 243901923 | 169.254.10.197  | enp8s0    | Camera_enp8s0   |
| top_right | 243901918 | 169.254.153.193 | enp9s0    | Camera_enp9s0   |
| back      | 243901915 | 169.254.1.191   | enp10s0   | Camera_enp10s0  |
| right     | 243901926 | 169.254.1.190   | enp12s0   | Camera_enp12s0  |

- A câmera que ocupava `enp3s0` (serial 243901925) foi removida fisicamente
  em 2026-07-03; o perfil `Camera_enp3s0` mantém a rota `169.254.164.199/32`
  para o caso de retorno.
- `right`: nome assumido pela câmera do `enp12s0` (243901926, antes chamada
  `camera_6`), para manter o conjunto de posições completo.
- `top_front`: câmera substituída por reserva — serial novo **243901980**
  (a original era 243901916).

Comandos que recriam essa configuração do zero (rodar no carro com sudo):

```bash
nmcli con mod Camera_enp2s0  ipv4.routes 169.254.7.198/32
nmcli con mod Camera_enp3s0  ipv4.routes 169.254.164.199/32
nmcli con mod Camera_enp7s0  ipv4.routes 169.254.81.234/32
nmcli con mod Camera_enp8s0  ipv4.routes 169.254.10.197/32
nmcli con mod Camera_enp9s0  ipv4.routes 169.254.153.193/32
nmcli con mod Camera_enp10s0 ipv4.routes 169.254.1.191/32
nmcli con mod Camera_enp12s0 ipv4.routes 169.254.1.190/32
for d in enp2s0 enp3s0 enp6s0 enp7s0 enp8s0 enp9s0 enp10s0 enp12s0; do
    nmcli device reapply "$d" || true
done
```

## Carro — systemd

`/etc/systemd/system/air-twizy-gige-tuning.service`: `enp6s0` removido de
`CAMERA_IFACES`. A porta deixou de ser de câmera; o MTU 9000 que o tuning
força quebraria o link com o notebook. Depois de editar:
`sudo systemctl daemon-reload`.

## Carro — repositório `air_twizy_hardware`

### `.env`

- `CAMERA_NAMES=left,top_front,top_left,top_right,back,right`
- `CAMERA_SERIALS=243901924,243901980,243901923,243901918,243901915,243901926`
- `CAMERA_COUNT=6`
- `CAMERA_FRAME_RATE=10.0`

Alterações no `.env` exigem `docker compose up -d camera`
(recreate; `docker restart` não relê o env).

**Pendente no carro:** o rename `camera_6` → `right` (último item de
`CAMERA_NAMES`) ainda não foi aplicado no `.env` do carro — na próxima
conexão, editar e rodar `docker compose up -d camera`.

### `workspace/camera-lucid/launch/multi_camera.launch.py`

Nós de câmera com `respawn=True, respawn_delay=5.0`. Os processos morrem
com `GenICam TimeoutException` quando a câmera demora a responder (boot,
troca de câmera, hiccup de PoE) e antes ficavam mortos até reiniciar o
container — era a causa de "faltar câmera" após reboot.

## Notebook usado no desenvolvimento (específico da máquina)

Setup do notebook não é necessário para o carro funcionar — está aqui só
como registro. Para configurar qualquer outro notebook, siga
`docs/tutorial-viewer.md`.

- Conexão NM `twizy-cable`: `enp45s0`, `10.250.0.2/30`, autoconnect
  (persistida em `/etc/netplan/90-NM-<uuid>.yaml`).
- `~/twizy_viewer/`: mesmo conteúdo da pasta `twizy_viewer/` deste
  repositório (a versão do repositório é a de referência).

## Viewer (`twizy_viewer/` neste repositório)

- `fastdds_super_client.xml`: SUPER_CLIENT → `10.250.0.1:11811`, transporte
  UDPv4 com `interfaceWhiteList 10.250.0.2` e `useBuiltinTransports=false`.
- `multi_camera_viewer.py`: mosaico com as 6 câmeras operacionais,
  FPS por câmera, QoS best_effort.
- Demais scripts (`build.sh`, `run_ros.sh`, `check_topics.sh`,
  `view_*.sh`): uso documentado no tutorial.

## Compatibilidade com o restante do compose

O serviço de câmeras faz parte de um `docker-compose.yml` maior no carro
(discovery server, LiDAR, interface do veículo). Nenhuma alteração toca os
outros serviços: as variáveis de `.env` modificadas são lidas apenas pelo
serviço `camera`, o respawn é interno ao container de câmeras e as mudanças
de rede são no host (porta `enp6s0` e rotas /32), fora das interfaces do
LiDAR (`enp11s0`) e da rede dos demais containers (host network).

## Validação executada (pós-reboot do carro)

1. 4 containers sobem sozinhos (`discovery_server`, `air_twizy_camera`,
   `ouster_lidar`, `twizy`).
2. 6 câmeras publicam a 10 Hz.
3. LiDAR publica (`/ouster/points` 10 Hz, `/ouster/imu` 100 Hz).
4. Notebook recebe as 6 câmeras a 10 fps pelo cabo gigabit (~46 MB/s).
5. Viewer multi-câmera exibe o mosaico na tela do notebook.

## Armadilha principal (operação)

Nunca reiniciar somente o `discovery_server`: clientes Fast DDS do Humble
não se re-registram em servidor reiniciado e todos os tópicos somem.
Sequência correta no carro:

```bash
docker restart discovery_server && sleep 5 && \
docker restart air_twizy_camera ouster_lidar twizy
```
