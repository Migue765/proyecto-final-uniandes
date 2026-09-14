#!/bin/sh
set -eu

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
target_file="$script_dir/../.env.local"

if [ -L "$target_file" ]; then
    printf '%s\n' '.env.local no puede ser un enlace simbólico.' >&2
    exit 3
fi

if [ -f "$target_file" ]; then
    chmod 600 "$target_file"
    missing_key=0
    for required_key in DATABASE_ADMIN_URL RUNTIME_DB_USER RUNTIME_DB_PASSWORD; do
        if ! grep -q "^${required_key}=" "$target_file"; then
            missing_key=1
        fi
    done
    if [ "$missing_key" -eq 1 ]; then
        printf '%s\n' \
            '.env.local usa el formato anterior y se conserva sin cambios.' \
            'Muévelo a un respaldo y vuelve a ejecutar este script para regenerarlo.' >&2
        exit 2
    fi
    printf '%s\n' \
        '.env.local ya existe, contiene las claves requeridas y quedó en modo 0600.'
    exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
    printf '%s\n' 'openssl es requerido para generar secretos locales.' >&2
    exit 1
fi

postgres_admin_password=$(openssl rand -hex 24)
runtime_db_password=$(openssl rand -hex 24)
redis_password=$(openssl rand -hex 24)
umask 077
{
    printf 'POSTGRES_USER=solventa_admin\n'
    printf 'POSTGRES_DB=solventa\n'
    printf 'POSTGRES_PASSWORD=%s\n' "$postgres_admin_password"
    printf 'DATABASE_ADMIN_URL=postgresql://solventa_admin:%s@postgres:5432/solventa\n' "$postgres_admin_password"
    printf 'RUNTIME_DB_USER=solventa_runtime\n'
    printf 'RUNTIME_DB_PASSWORD=%s\n' "$runtime_db_password"
    printf 'DATABASE_URL=postgresql://solventa_runtime:%s@postgres:5432/solventa\n' "$runtime_db_password"
    printf 'REDIS_PASSWORD=%s\n' "$redis_password"
    printf 'REDIS_URL=redis://:%s@redis:6379/0\n' "$redis_password"
} > "$target_file"
chmod 600 "$target_file"
printf '%s\n' '.env.local creado con permisos 0600.'
