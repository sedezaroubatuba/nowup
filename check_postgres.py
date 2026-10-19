"""Read-only PostgreSQL connection check. Never prints the connection URL."""
import os
import sys
from urllib.parse import urlsplit


def check_configuration(value):
    if not value:
        raise ValueError('Configure DATABASE_URL no ambiente, sem colar a senha no código.')
    parsed = urlsplit(value)
    if parsed.scheme not in ('postgres', 'postgresql') or not parsed.hostname or not parsed.path.strip('/'):
        raise ValueError('DATABASE_URL deve apontar para um banco PostgreSQL válido.')
    return value


def main():
    try:
        url = check_configuration(os.getenv('DATABASE_URL', ''))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print('Instale psycopg[binary]>=3.2,<4 para executar a verificação.', file=sys.stderr)
        return 2
    try:
        with psycopg.connect(url, connect_timeout=10) as conn:
            conn.execute('SET TRANSACTION READ ONLY')
            version = conn.execute('SHOW server_version').fetchone()[0]
            conn.execute('SELECT 1').fetchone()
            print('Conexão PostgreSQL confirmada. Versão: ' + version)
            print('Nenhuma tabela ou dado foi alterado.')
    except Exception:
        print('Falha na conexão. Confira endereço, credenciais, rede e TLS no Render. A URL foi omitida.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
