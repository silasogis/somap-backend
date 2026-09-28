-- ==============================================================================
-- 01_viasul_init.sql
-- Inicialização de Roles, Logins e Schemas para viasul_spatial_db
-- ==============================================================================

-- 1. Habilitar PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Revogar privilégios públicos padrão (Princípio do Menor Privilégio)
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CONNECT ON DATABASE viasul_spatial_db FROM PUBLIC;

-- 3. Criar Roles de Grupo (NOLOGIN)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viasul_admin') THEN
        CREATE ROLE viasul_admin WITH SUPERUSER;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viasul_editor') THEN
        CREATE ROLE viasul_editor WITH NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'viasul_readonly') THEN
        CREATE ROLE viasul_readonly WITH NOLOGIN;
    END IF;
END
$$;

-- 4. Criar Usuários de Login individuais e vincular aos grupos
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin_user') THEN
        CREATE ROLE admin_user WITH SUPERUSER LOGIN PASSWORD 'viasul_admin@2026' INHERIT IN ROLE viasul_admin;
    ELSE
        ALTER ROLE admin_user WITH SUPERUSER PASSWORD 'viasul_admin@2026';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'maria') THEN
        CREATE ROLE maria WITH LOGIN PASSWORD 'maria@2026' INHERIT IN ROLE viasul_editor;
    ELSE
        ALTER ROLE maria WITH PASSWORD 'maria@2026';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'joao') THEN
        CREATE ROLE joao WITH LOGIN PASSWORD 'joao@2026' INHERIT IN ROLE viasul_editor;
    ELSE
        ALTER ROLE joao WITH PASSWORD 'joao@2026';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pedro') THEN
        CREATE ROLE pedro WITH LOGIN PASSWORD 'pedro@2026' INHERIT IN ROLE viasul_readonly;
    ELSE
        ALTER ROLE pedro WITH PASSWORD 'pedro@2026';
    END IF;
END
$$;

-- 5. Conceder privilégio de conexão ao banco
GRANT CONNECT, TEMP ON DATABASE viasul_spatial_db TO viasul_admin, viasul_editor, viasul_readonly;

-- 6. Criar os Schemas
CREATE SCHEMA IF NOT EXISTS admin;
CREATE SCHEMA IF NOT EXISTS ambiental;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS compartilhado;
CREATE SCHEMA IF NOT EXISTS limites;
CREATE SCHEMA IF NOT EXISTS fundiario;
CREATE SCHEMA IF NOT EXISTS infraestrutura;
CREATE SCHEMA IF NOT EXISTS hidrografia;
CREATE SCHEMA IF NOT EXISTS mapas;
CREATE SCHEMA IF NOT EXISTS public;
CREATE SCHEMA IF NOT EXISTS turismo;
CREATE SCHEMA IF NOT EXISTS transporte;
CREATE SCHEMA IF NOT EXISTS analise_br376;

-- 7. Configurar Permissões de USAGE nos Schemas

-- Schema 'admin': apenas admin e editores (Pedro / Leitor NÃO ACESSA)
REVOKE ALL ON SCHEMA admin FROM PUBLIC, viasul_readonly;
GRANT USAGE ON SCHEMA admin TO viasul_admin, viasul_editor;

-- Schema 'audit': apenas admin
REVOKE ALL ON SCHEMA audit FROM PUBLIC, viasul_editor, viasul_readonly;
GRANT USAGE ON SCHEMA audit TO viasul_admin;

-- Schema 'compartilhado': editores têm USAGE e CREATE para criar novas tabelas; leitores têm USAGE
REVOKE ALL ON SCHEMA compartilhado FROM PUBLIC;
GRANT USAGE, CREATE ON SCHEMA compartilhado TO viasul_admin, viasul_editor;
GRANT USAGE ON SCHEMA compartilhado TO viasul_readonly;

-- Schemas operacionais: USAGE para todos os grupos
GRANT USAGE ON SCHEMA public, ambiental, limites, fundiario, infraestrutura, hidrografia, mapas, turismo, transporte, analise_br376 TO viasul_admin, viasul_editor, viasul_readonly;

-- Permissão de leitura em tabelas/funções espaciais nativas do PostGIS no schema public
GRANT SELECT ON ALL TABLES IN SCHEMA public TO viasul_editor, viasul_readonly;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO viasul_editor, viasul_readonly;
