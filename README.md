# Lucid Vision Camera - ROS2 Humble (Docker)

Driver das cameras Lucid Vision (Triton TRI032S) rodando dentro de um container Docker
com ROS2 Humble. Feito pro projeto do carro autonomo, pensado desde o inicio pra escalar
de 1 ate 8 cameras sem dor de cabeca.

O driver oficial da Lucid so vinha preparado pro ROS2 Eloquent e nao funcionava de cara.
Esse repositorio resolve isso e ja entrega tudo pronto pra rodar no Humble.

## O que voce precisa ter

- **Docker** e **Docker Compose** instalados no PC
- **Camera Lucid Vision Triton** conectada via cabo Ethernet (testado com TRI032S-C)
- **Lente C-mount** montada na camera. A camera vem sem lente, o sensor fica exposto.
  Se so tem o tubo protetor IP67 (IPTC-D590L555), ele nao eh lente, eh so protecao.
- **Ubuntu 22.04** ou mais novo
- **ArenaSDK** e **arena_api** — sao os drivers da Lucid, precisa baixar do site deles:
  https://thinklucid.com/downloads-hub/
  - O arquivo `ArenaSDK_Linux_x64.tar.gz` vai em `resources/ArenaSDK/linux64/`
  - O arquivo `arena_api-*.whl` vai em `resources/arena_api/`

## Estrutura das pastas

```
lucid_camera_ros2/
├── Dockerfile                  # Receita do container (ROS2 Humble + ArenaSDK)
├── docker-compose.yml          # Define os servicos (camera, gravador, etc)
├── resources/
│   ├── ArenaSDK/linux64/       # SDK da Lucid (baixar do site, nao vai pro git)
│   └── arena_api/              # API Python da Lucid (baixar do site)
├── ros2_ws/src/
│   └── arena_camera_node/      # Pacote ROS2 que fala com a camera
├── scripts/
│   ├── setup_network.sh        # Configura a rede do PC pras cameras GigE
│   ├── list_cameras.py         # Mostra todas as cameras conectadas
│   ├── start_camera.sh         # Atalho pra ligar uma camera
│   ├── focus_helper.py         # Ajuda a focar a lente (mostra score de nitidez)
│   └── live_viewer.py          # Mostra a imagem da camera ao vivo numa janela
├── launch/
│   └── multi_camera.launch.py  # Liga varias cameras de uma vez
├── config/
│   └── cameras_example.yaml    # Modelo de config pras 8 cameras
└── bags/                       # Onde ficam os bags gravados
```

## Instalacao passo a passo

### 1. Clonar e colocar os drivers

```bash
git clone <url-do-repo>
cd lucid_camera_ros2
```

Baixe o ArenaSDK do site da Lucid e coloque os arquivos nas pastas certas:
```
resources/ArenaSDK/linux64/ArenaSDK_Linux_x64.tar.gz
resources/arena_api/arena_api-X.X.X-py3-none-any.whl
```

### 2. Configurar a rede

As cameras Lucid usam GigE Vision (ethernet gigabit). O PC precisa de uns ajustes
pra aguentar o trafego de dados das cameras sem perder frames:

```bash
chmod +x scripts/setup_network.sh

# Troque "enp45s0" pela sua interface de rede se for diferente
sudo ./scripts/setup_network.sh enp45s0
```

Se nao sabe qual eh a interface, rode `ip link show` e procure a que nao eh `lo` nem `wlo`.

### 3. Configurar o IP

A camera e o PC precisam estar na mesma faixa de IP. Duas opcoes:

- **Link-local (mais facil):** o PC e a camera se encontram sozinhos na faixa 169.254.x.x
  ```bash
  sudo ip addr add 169.254.1.1/16 dev enp45s0
  ```
- **IP fixo:** configure um IP fixo no PC (ex: 192.168.1.1) e na camera (ex: 192.168.1.10)

### 4. Liberar janelas graficas pro container

Pra conseguir abrir janelas (tipo o visualizador de imagem) de dentro do container:
```bash
xhost +local:docker
```

### 5. Montar a imagem Docker

```bash
docker compose build
```

Isso demora na primeira vez porque baixa o ROS2 Humble e instala tudo.
Nas proximas vezes eh rapido porque usa cache.

## Como usar

### Ligar o container e entrar nele

```bash
docker compose up -d camera_dev
docker compose exec camera_dev bash
```

Agora voce esta dentro do container. Tudo que rodar daqui pra frente eh la dentro.

### Ver se a camera foi detectada

```bash
python3 /arena_camera_ros2/scripts/list_cameras.py
```

Vai mostrar modelo, serial e IP de cada camera conectada. Se nao aparecer nada,
confira o cabo e o IP.

### Ligar a camera e publicar imagens

Jeito rapido (com script):
```bash
/arena_camera_ros2/scripts/start_camera.sh <SERIAL> /camera/image_raw
```

Jeito manual (mais controle):
```bash
source /opt/ros/humble/setup.bash
source /arena_camera_ros2/ros2_ws/install/setup.bash
ros2 run arena_camera_node start --ros-args \
    -p serial:=<SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=rgb8
```

### Ver a imagem ao vivo

Abra outro terminal no container:
```bash
docker compose exec camera_dev bash
python3 /arena_camera_ros2/scripts/live_viewer.py
```

Ou, se tiver ROS2 no PC host:
```bash
ros2 run rqt_image_view rqt_image_view /camera/image_raw
```

### Gravar um bag (salvar os dados da camera)

```bash
docker compose exec camera_dev bash
cd /arena_camera_ros2/bags
source /opt/ros/humble/setup.bash
ros2 bag record /camera/image_raw -s mcap
```

Os bags ficam salvos na pasta `bags/` que eh compartilhada com o PC host.
Ctrl+C pra parar de gravar.

### Checar se ta tudo rodando

```bash
# Ver quais topicos existem
ros2 topic list

# Ver a que taxa a camera ta publicando (fps)
ros2 topic hz /camera/image_raw

# Ver info do topico
ros2 topic info /camera/image_raw --verbose
```

## Usando varias cameras (modo producao)

O sistema foi feito pra escalar. Pra rodar as 8 cameras do carro:

### 1. Criar o arquivo de configuracao

```bash
cp config/cameras_example.yaml config/cameras.yaml
```

### 2. Editar com os seriais das suas cameras

Abra `config/cameras.yaml` e substitua os seriais. Use `list_cameras.py` pra descobrir
o serial de cada camera. Cada camera tem um topico diferente (ex: `/camera/front/image_raw`).

### 3. Ligar todas de uma vez

```bash
ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py \
    config_file:=/arena_camera_ros2/config/cameras.yaml
```

### Dicas pra 8 cameras no carro

- Use um **switch gigabit** com suporte a Jumbo Frames entre as cameras e o PC
- Configure **IPs fixos** nas cameras (ex: 192.168.1.10 ate 192.168.1.17)
- Rode `setup_network.sh` em cada interface de rede usada
- Se tiver problemas de banda, reduza a resolucao ou o fps no YAML

## Parametros que a camera aceita

| Parametro       | O que faz                                | Padrao                    |
|-----------------|------------------------------------------|---------------------------|
| serial          | Escolhe qual camera usar (pelo serial)   | primeira que encontrar    |
| topic           | Nome do topico onde publica as imagens   | /arena_camera_node/images |
| width           | Largura da imagem em pixels              | maximo da camera          |
| height          | Altura da imagem em pixels               | maximo da camera          |
| pixelformat     | Formato de cor (rgb8, bgr8, mono8, bayer_rggb8, etc)  | rgb8                      |
| gain            | Ganho do sensor (brilho)                 | 0.0                       |
| exposure_time   | Tempo de exposicao em microsegundos      | 10000                     |
| trigger_mode    | Se true, so tira foto quando pedir       | false                     |
| qos_reliability | Confiabilidade da comunicacao ROS        | reliable                  |

## Modo RAW (BayerRG8)

Para capturar imagens direto do sensor sem processamento de cor (modo RAW), use o formato `bayer_rggb8`:

### Iniciar camera em modo RAW
```bash
# Jeito rapido (com script)
/arena_camera_ros2/scripts/start_camera_raw.sh 243901923 /camera/image_raw

# Jeito manual
ros2 run arena_camera_node start --ros-args \
    -p serial:=243901923 \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8
```

### Visualizar imagem RAW

**Opção 1: Viewer direto da API Arena (mais rápido)**
```bash
python3 /arena_camera_ros2/scripts/live_viewer_raw.py
# Pressione 'r' para alternar entre RAW e RGB
# Pressione 's' para salvar frame (salva RAW e RGB)
```

**Opção 2: Viewer ROS2 (subscreve no tópico)**
```bash
python3 /arena_camera_ros2/scripts/live_viewer_ros_raw.py
# Pressione 'r' para alternar entre RAW e RGB
# Pressione 's' para salvar frame
```

**Opção 3: rqt_image_view**
```bash
ros2 run rqt_image_view rqt_image_view /camera/image_raw
# O rqt automaticamente faz o demosaicing do Bayer para visualização
```

### Formatos Bayer suportados

A câmera Triton TRI032S usa um sensor com filtro Bayer **RGGB**. Formatos disponíveis:
- `bayer_rggb8` - 8 bits, padrão Red-Green-Green-Blue (BayerRG8)
- `bayer_rggb16` - 16 bits, padrão RGGB
- `bayer_bggr8`, `bayer_gbrg8`, `bayer_grbg8` - outros padrões Bayer

**Importante**: A câmera TRI032S usa BayerRG8 nativamente. Use `bayer_rggb8` para obter dados RAW sem conversão.

### Conversão Bayer para RGB

Para processar imagens Bayer, use OpenCV:
```python
import cv2
raw_img = cv2.imread('frame_raw.png', cv2.IMREAD_GRAYSCALE)
rgb_img = cv2.cvtColor(raw_img, cv2.COLOR_BayerRG2RGB)
```

Ou use o pacote ROS2 `image_proc` para fazer demosaicing em tempo real:
```bash
ros2 run image_proc debayer --ros-args \
    -r image_raw:=/camera/image_raw \
    -r image_color:=/camera/image_color
```

## Problemas comuns

### Camera nao aparece

1. Confira se o cabo ethernet ta conectado e a camera ta ligada
2. Rode `sudo ./scripts/setup_network.sh <interface>` no PC host
3. Confira se o IP do PC e da camera estao na mesma faixa
4. Tente pingar a camera: `ping 169.254.x.x`

### Imagem toda cinza / borrada / sem forma nenhuma

A camera Triton **nao vem com lente**. Sem lente, o sensor recebe luz difusa e a
imagem fica uniformemente cinza. O tubo IP67 (IPTC-D590L555) eh so protecao, nao
eh lente.

Monte uma **lente C-mount** e depois ajuste o foco:
```bash
python3 /arena_camera_ros2/scripts/focus_helper.py
# Gire o anel de foco ate o SHARPNESS na tela ser o mais alto possivel
```

### Janela grafica nao abre

Rode no PC host (fora do container):
```bash
xhost +local:docker
```

### Imagem com lag ou travando

- Aumente os buffers de rede (`setup_network.sh` ja faz isso)
- Ative Jumbo Frames (MTU 9000) no switch e na interface
- Reduza a resolucao ou o fps
- Se for muitas cameras, distribua entre interfaces de rede diferentes

### Erro de compilacao: `True not declared`

O codigo original tinha `True` (que eh Python) em vez de `true` (que eh C++).
Ja ta corrigido nesse repositorio.

### Erro de OpenCV na compilacao

O ArenaSDK vem com o OpenCV dele (4.0.1) e o linker precisa achar essas libs.
O `Findarena_sdk.cmake` desse repositorio ja ta configurado pra isso.
Se der problema, confira se o `LD_LIBRARY_PATH` inclui `/ArenaSDK_Linux_x64/OpenCV/lib`.

## Comandos uteis (cola rapida)

```bash
# Subir o container
docker compose up -d camera_dev

# Entrar no container
docker compose exec camera_dev bash

# Ver logs do container
docker compose logs -f

# Parar tudo
docker compose down

# Rebuildar do zero (se mudou o Dockerfile)
docker compose build --no-cache
```

## O que foi mudado em relacao ao driver oficial

Esse projeto parte do [arena_camera_ros2](https://github.com/lucidvisionlabs/arena_camera_ros2)
da Lucid Vision Labs. O original era pro ROS2 Eloquent e nao compilava no Humble.
Mudancas feitas:

1. **Dockerfile refeito** pro ROS2 Humble (o original era Eloquent)
2. **Instalacao do ArenaSDK** feita direto via `Arena_SDK.conf` (sem script interativo)
3. **OpenCV do SDK linkado** no `Findarena_sdk.cmake` (resolvia erro de undefined reference)
4. **Bug `True`/`true`** corrigido no `ArenaCameraNode.cpp`
5. **Coisas novas**: scripts auxiliares, launch file multi-camera, config YAML, focus helper

## Licenca

MIT - Baseado no driver oficial da Lucid Vision Labs.
