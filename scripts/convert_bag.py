#!/usr/bin/env python3
"""
Converte um ROS2 bag para MP4 em um único comando (sem precisar de dois terminais).

Uso:
    python3 convert_bag.py ./minha_bag
    python3 convert_bag.py ./minha_bag --output video.mp4
    python3 convert_bag.py ./minha_bag --topic /camera/image_raw --fps 35

O script inicia automaticamente o subscriber e o 'ros2 bag play'.
"""

import argparse
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Converte ROS2 bag para MP4 (comando único)'
    )
    parser.add_argument('bag', help='Pasta da bag (ex: ./minha_bag)')
    parser.add_argument(
        '--output', default=None,
        help='Arquivo de saída (padrão: <nome_da_bag>.mp4)'
    )
    parser.add_argument(
        '--topic', default='/camera/image_raw',
        help='Tópico de imagem (padrão: /camera/image_raw)'
    )
    parser.add_argument(
        '--fps', type=float, default=None,
        help='FPS do vídeo (padrão: detectado da bag)'
    )
    args = parser.parse_args()

    bag_path = Path(args.bag).resolve()
    if not bag_path.exists():
        print(f'❌ Bag não encontrada: {bag_path}')
        sys.exit(1)

    if args.output is None:
        args.output = str(bag_path.parent / f'{bag_path.name}.mp4')

    print(f'📦 Bag:    {bag_path}')
    print(f'🎬 Saída:  {args.output}')
    print(f'📡 Tópico: {args.topic}')
    print()

    # Arquivo de override de QoS (necessário para bags com BEST_EFFORT)
    qos_content = f"""{args.topic}:
  reliability: best_effort
  durability: volatile
  history: keep_last
  depth: 10
"""
    qos_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    qos_file.write(qos_content)
    qos_file.close()

    script_dir = Path(__file__).parent
    bag_to_video = script_dir / 'bag_to_video.py'

    # Comando do subscriber
    subscriber_cmd = [
        sys.executable, str(bag_to_video),
        '--topic', args.topic,
        '--output', args.output,
    ]
    if args.fps:
        subscriber_cmd += ['--fps', str(args.fps)]

    # Comando do bag play
    bag_cmd = [
        'ros2', 'bag', 'play', str(bag_path),
        '--qos-profile-overrides-path', qos_file.name
    ]

    subscriber = None
    try:
        print('▶️  Iniciando subscriber...')
        subscriber = subprocess.Popen(subscriber_cmd)

        # Aguardar subscriber inicializar
        time.sleep(3)

        print('▶️  Reproduzindo bag...')
        subprocess.run(bag_cmd)

        print('\n⏳ Finalizando subscriber...')
        time.sleep(2)

    except KeyboardInterrupt:
        print('\n🛑 Interrompido pelo usuário')
    finally:
        if subscriber and subscriber.poll() is None:
            subscriber.send_signal(signal.SIGINT)
            try:
                subscriber.wait(timeout=10)
            except subprocess.TimeoutExpired:
                subscriber.kill()
        os.unlink(qos_file.name)

    if os.path.exists(args.output) and os.path.getsize(args.output) > 0:
        size_mb = os.path.getsize(args.output) / (1024 * 1024)
        print(f'\n✅ Conversão concluída!')
        print(f'   📁 {args.output} ({size_mb:.1f} MB)')
    else:
        print(f'\n⚠️  Arquivo de saída não encontrado ou vazio: {args.output}')
        print('   Verifique se o tópico está correto e se a bag tem frames.')


if __name__ == '__main__':
    main()
