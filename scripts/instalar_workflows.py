"""Importa e publica os dois workflows após a criação da conta proprietária do n8n."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    print('+', ' '.join(args), flush=True)
    subprocess.run(list(args), cwd=ROOT, check=True)


def main():
    if not (ROOT / '.env').exists():
        print('Primeiro execute: python scripts/gerar_env.py')
        return 1
    try:
        run('docker', 'compose', 'exec', '-T', 'n8n', 'n8n',
            'import:workflow', '--separate', '--input=/files/workflows')
        for id in ('ubsMariliaColeta26', 'ubsMariliaChat26'):
            run('docker', 'compose', 'exec', '-T', 'n8n', 'n8n', 'publish:workflow', '--id=' + id)
        print('Workflows importados e publicados. Executando coleta inicial...')
        run('docker', 'compose', 'exec', '-T', 'api', 'python', '-m', 'app.bootstrap')
    except (subprocess.CalledProcessError, FileNotFoundError):
        print('Falha de instalacao. Consulte README.md: importacao manual e diagnostico.', file=sys.stderr)
        return 1
    print('Pronto: http://localhost:8080 (chat) e http://localhost:5678 (n8n).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
