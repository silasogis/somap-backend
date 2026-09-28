-- ==============================================================================
-- 02_viasul_tables_and_security.sql
-- Criação de Tabelas, Triggers, RLS, CLS e Permissões no viasul_spatial_db
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. FUNÇÕES AUXILIARES E TRIGGERS GLOBAIS
-- ------------------------------------------------------------------------------

-- Função de preenchimento automático de autoria e timestamps
CREATE OR REPLACE FUNCTION public.set_metadata_and_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.created_by := CURRENT_USER;
        NEW.created_at := CURRENT_TIMESTAMP;
    END IF;
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Função de cálculo geométrico automático (Comprimento e Área projetados em SIRGAS 2000 UTM 22S - EPSG:31982)
CREATE OR REPLACE FUNCTION public.calculate_geometry_metrics()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_TABLE_NAME IN ('defensas_metalicas', 'pavimento') THEN
        IF GeometryType(NEW.geom) IN ('LINESTRING', 'MULTILINESTRING') THEN
            NEW.extensao_km := ROUND((ST_Length(ST_Transform(NEW.geom, 31982)) / 1000.0)::numeric, 3);
        END IF;
    END IF;

    IF TG_TABLE_NAME IN ('pavimento', 'desapropriacoes', 'imoveis_lindeiros', 'faixa_dominio', 'app') THEN
        IF GeometryType(NEW.geom) IN ('POLYGON', 'MULTIPOLYGON') THEN
            NEW.area_m2 := ROUND(ST_Area(ST_Transform(NEW.geom, 31982))::numeric, 2);
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------------------------
-- 2. SCHEMA AUDIT (Logs e Rastreabilidade Total)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit.logged_actions (
    id SERIAL PRIMARY KEY,
    schema_name TEXT NOT NULL,
    table_name TEXT NOT NULL,
    user_name TEXT NOT NULL DEFAULT CURRENT_USER,
    action TEXT NOT NULL,
    original_data JSONB,
    new_data JSONB,
    query_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION audit.if_modified_func()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit.logged_actions (schema_name, table_name, action, original_data)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, 'DELETE', to_jsonb(OLD));
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit.logged_actions (schema_name, table_name, action, original_data, new_data)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, 'UPDATE', to_jsonb(OLD), to_jsonb(NEW));
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit.logged_actions (schema_name, table_name, action, new_data)
        VALUES (TG_TABLE_SCHEMA, TG_TABLE_NAME, 'INSERT', to_jsonb(NEW));
        RETURN NEW;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ------------------------------------------------------------------------------
-- 3. SCHEMA ADMIN (Isolamento Didático de Tabelas)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.admin_stuff (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    geom GEOMETRY(POINT, 4326)
);

CREATE TABLE IF NOT EXISTS admin.other_admin_stuff (
    id SERIAL PRIMARY KEY,
    codigo_segredo VARCHAR(100) NOT NULL,
    detalhes TEXT,
    geom GEOMETRY(POINT, 4326)
);

-- Permissão didática: Editores (Maria e João) só veem admin_stuff. other_admin_stuff fica só para Admin.
GRANT SELECT ON admin.admin_stuff TO viasul_editor;
-- (Note: other_admin_stuff NÃO recebe grant para viasul_editor nem viasul_readonly)

-- ------------------------------------------------------------------------------
-- 4. SCHEMA FUNDIARIO (Column-Level Security - CLS)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fundiario.imoveis_lindeiros (
    id SERIAL PRIMARY KEY,
    matricula VARCHAR(50) UNIQUE NOT NULL,
    proprietario VARCHAR(150) NOT NULL,
    cpf_cnpj VARCHAR(20),
    area_m2 NUMERIC(12, 2),
    valor_avaliado NUMERIC(14, 2),
    status_desapropriacao VARCHAR(30) DEFAULT 'Em Negociação',
    notas_vistoria TEXT, -- Coluna liberada para edição do fiscal/leitor Pedro
    created_by VARCHAR(50) DEFAULT CURRENT_USER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(MULTIPOLYGON, 4326),
    CONSTRAINT chk_geom_valida CHECK (ST_IsValid(geom))
);

CREATE INDEX IF NOT EXISTS ix_fundiario_imoveis_geom ON fundiario.imoveis_lindeiros USING GIST (geom);

-- Triggers em fundiario
CREATE OR REPLACE TRIGGER trg_fundiario_metrics
BEFORE INSERT OR UPDATE OF geom ON fundiario.imoveis_lindeiros
FOR EACH ROW EXECUTE FUNCTION public.calculate_geometry_metrics();

CREATE OR REPLACE TRIGGER trg_fundiario_meta
BEFORE INSERT OR UPDATE ON fundiario.imoveis_lindeiros
FOR EACH ROW EXECUTE FUNCTION public.set_metadata_and_timestamps();

CREATE OR REPLACE TRIGGER trg_fundiario_audit
AFTER INSERT OR UPDATE OR DELETE ON fundiario.imoveis_lindeiros
FOR EACH ROW EXECUTE FUNCTION audit.if_modified_func();

-- Permissões em fundiario:
-- Editores: Acesso completo
GRANT SELECT, INSERT, UPDATE, DELETE ON fundiario.imoveis_lindeiros TO viasul_editor;
GRANT USAGE, SELECT ON SEQUENCE fundiario.imoveis_lindeiros_id_seq TO viasul_editor;

-- Leitor (Pedro): SELECT em todas as colunas, mas UPDATE restrito EXCLUSIVAMENTE a notas_vistoria
GRANT SELECT ON fundiario.imoveis_lindeiros TO viasul_readonly;
GRANT UPDATE (notas_vistoria) ON fundiario.imoveis_lindeiros TO viasul_readonly;

-- ------------------------------------------------------------------------------
-- 5. SCHEMA TRANSPORTE (Row-Level Security - RLS)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transporte.ordens_servico (
    id SERIAL PRIMARY KEY,
    codigo_os VARCHAR(30) UNIQUE NOT NULL,
    rodovia VARCHAR(20) NOT NULL DEFAULT 'BR-116',
    km NUMERIC(6, 2) NOT NULL,
    tipo_servico VARCHAR(80) NOT NULL, -- 'Tapa-Buraco', 'Reparo Defensa', 'Limpeza Drenagem'
    prioridade VARCHAR(20) DEFAULT 'Normal',
    status VARCHAR(30) DEFAULT 'Pendente',
    created_by VARCHAR(50) DEFAULT CURRENT_USER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(POINT, 4326),
    CONSTRAINT chk_geom_os CHECK (ST_IsValid(geom))
);

CREATE INDEX IF NOT EXISTS ix_transporte_os_geom ON transporte.ordens_servico USING GIST (geom);

-- Triggers em transporte
CREATE OR REPLACE TRIGGER trg_transporte_meta
BEFORE INSERT OR UPDATE ON transporte.ordens_servico
FOR EACH ROW EXECUTE FUNCTION public.set_metadata_and_timestamps();

CREATE OR REPLACE TRIGGER trg_transporte_audit
AFTER INSERT OR UPDATE OR DELETE ON transporte.ordens_servico
FOR EACH ROW EXECUTE FUNCTION audit.if_modified_func();

-- Habilitar Row-Level Security (RLS)
ALTER TABLE transporte.ordens_servico ENABLE ROW LEVEL SECURITY;

-- Política 1: Editores só veem e editam as OS criadas pelo seu próprio usuário
DROP POLICY IF EXISTS os_editor_policy ON transporte.ordens_servico;
CREATE POLICY os_editor_policy ON transporte.ordens_servico
    FOR ALL
    TO viasul_editor
    USING (created_by = CURRENT_USER)
    WITH CHECK (created_by = CURRENT_USER);

-- Política 2: Admins têm acesso irrestrito a todas as OS
DROP POLICY IF EXISTS os_admin_policy ON transporte.ordens_servico;
CREATE POLICY os_admin_policy ON transporte.ordens_servico
    FOR ALL
    TO viasul_admin
    USING (true)
    WITH CHECK (true);

-- Política 3: Leitores podem visualizar todas as OS
DROP POLICY IF EXISTS os_readonly_policy ON transporte.ordens_servico;
CREATE POLICY os_readonly_policy ON transporte.ordens_servico
    FOR SELECT
    TO viasul_readonly
    USING (true);

-- Conceder privilégios de tabela
GRANT SELECT, INSERT, UPDATE, DELETE ON transporte.ordens_servico TO viasul_editor;
GRANT USAGE, SELECT ON SEQUENCE transporte.ordens_servico_id_seq TO viasul_editor;
GRANT SELECT ON transporte.ordens_servico TO viasul_readonly;

-- ------------------------------------------------------------------------------
-- 6. SCHEMA INFRAESTRUTURA (Triggers de Automação Geométrica)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS infraestrutura.pavimento (
    id SERIAL PRIMARY KEY,
    rodovia VARCHAR(20) NOT NULL DEFAULT 'BR-116',
    tipo_pavimento VARCHAR(50) NOT NULL, -- 'CBUQ', 'Concreto', 'Tratamento Superficial'
    condicao_iri NUMERIC(4, 2), -- Índice de Irregularidade Internacional
    area_m2 NUMERIC(12, 2),
    extensao_km NUMERIC(8, 3),
    created_by VARCHAR(50) DEFAULT CURRENT_USER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(MULTILINESTRING, 4326),
    CONSTRAINT chk_geom_pavimento CHECK (ST_IsValid(geom))
);

CREATE TABLE IF NOT EXISTS infraestrutura.defensas_metalicas (
    id SERIAL PRIMARY KEY,
    rodovia VARCHAR(20) NOT NULL DEFAULT 'BR-116',
    lado VARCHAR(30) NOT NULL, -- 'Direito', 'Esquerdo', 'Canteiro Central'
    tipo_defensa VARCHAR(50) NOT NULL, -- 'Semirrígida W-Beam', 'Barreira New Jersey'
    extensao_km NUMERIC(8, 3),
    created_by VARCHAR(50) DEFAULT CURRENT_USER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(MULTILINESTRING, 4326),
    CONSTRAINT chk_geom_defensas CHECK (ST_IsValid(geom))
);
ALTER TABLE infraestrutura.defensas_metalicas ALTER COLUMN lado TYPE VARCHAR(30);

CREATE TABLE IF NOT EXISTS infraestrutura.obras_arte_especiais (
    id SERIAL PRIMARY KEY,
    nome_oae VARCHAR(120) NOT NULL, -- 'Ponte Rio Iguaçu', 'Viaduto Contorno Sul'
    tipo VARCHAR(50) NOT NULL, -- 'Ponte', 'Viaduto', 'Passarela'
    extensao_metros NUMERIC(8, 2),
    created_by VARCHAR(50) DEFAULT CURRENT_USER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(POINT, 4326),
    CONSTRAINT chk_geom_oae CHECK (ST_IsValid(geom))
);

CREATE INDEX IF NOT EXISTS ix_infra_pavimento_geom ON infraestrutura.pavimento USING GIST (geom);
CREATE INDEX IF NOT EXISTS ix_infra_defensas_geom ON infraestrutura.defensas_metalicas USING GIST (geom);
CREATE INDEX IF NOT EXISTS ix_infra_oae_geom ON infraestrutura.obras_arte_especiais USING GIST (geom);

-- Triggers em infraestrutura
CREATE OR REPLACE TRIGGER trg_pavimento_metrics
BEFORE INSERT OR UPDATE OF geom ON infraestrutura.pavimento
FOR EACH ROW EXECUTE FUNCTION public.calculate_geometry_metrics();

CREATE OR REPLACE TRIGGER trg_pavimento_meta
BEFORE INSERT OR UPDATE ON infraestrutura.pavimento
FOR EACH ROW EXECUTE FUNCTION public.set_metadata_and_timestamps();

CREATE OR REPLACE TRIGGER trg_pavimento_audit
AFTER INSERT OR UPDATE OR DELETE ON infraestrutura.pavimento
FOR EACH ROW EXECUTE FUNCTION audit.if_modified_func();

CREATE OR REPLACE TRIGGER trg_defensas_metrics
BEFORE INSERT OR UPDATE OF geom ON infraestrutura.defensas_metalicas
FOR EACH ROW EXECUTE FUNCTION public.calculate_geometry_metrics();

CREATE OR REPLACE TRIGGER trg_defensas_meta
BEFORE INSERT OR UPDATE ON infraestrutura.defensas_metalicas
FOR EACH ROW EXECUTE FUNCTION public.set_metadata_and_timestamps();

CREATE OR REPLACE TRIGGER trg_defensas_audit
AFTER INSERT OR UPDATE OR DELETE ON infraestrutura.defensas_metalicas
FOR EACH ROW EXECUTE FUNCTION audit.if_modified_func();

-- Permissões em infraestrutura
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA infraestrutura TO viasul_editor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA infraestrutura TO viasul_editor;
GRANT SELECT ON ALL TABLES IN SCHEMA infraestrutura TO viasul_readonly;

-- ------------------------------------------------------------------------------
-- 7. SCHEMA LIMITES (Faixa de Domínio e Praças de Pedágio)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS limites.faixa_dominio (
    id SERIAL PRIMARY KEY,
    trecho VARCHAR(100) NOT NULL,
    largura_metros NUMERIC(6, 2) NOT NULL,
    area_m2 NUMERIC(14, 2),
    geom GEOMETRY(MULTIPOLYGON, 4326),
    CONSTRAINT chk_geom_faixa CHECK (ST_IsValid(geom))
);

CREATE TABLE IF NOT EXISTS limites.pracas_pedagio (
    id SERIAL PRIMARY KEY,
    nome_praca VARCHAR(100) NOT NULL,
    km NUMERIC(6, 2) NOT NULL,
    tarifa_base NUMERIC(6, 2) NOT NULL,
    geom GEOMETRY(POINT, 4326)
);

CREATE INDEX IF NOT EXISTS ix_limites_faixa_geom ON limites.faixa_dominio USING GIST (geom);
CREATE INDEX IF NOT EXISTS ix_limites_pedagio_geom ON limites.pracas_pedagio USING GIST (geom);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA limites TO viasul_editor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA limites TO viasul_editor;
GRANT SELECT ON ALL TABLES IN SCHEMA limites TO viasul_readonly;

-- ------------------------------------------------------------------------------
-- 8. SCHEMAS AMBIENTAL, HIDROGRAFIA E TURISMO
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ambiental.app (
    id SERIAL PRIMARY KEY,
    tipo_app VARCHAR(80) NOT NULL, -- 'Margem de Rio', 'Nascente', 'Topo de Morro'
    area_m2 NUMERIC(14, 2),
    geom GEOMETRY(MULTIPOLYGON, 4326)
);

CREATE TABLE IF NOT EXISTS hidrografia.bueiros_drenagem (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- 'BDTC - Bueiro Duplo Tubular de Concreto', 'BSCC'
    km NUMERIC(6, 2) NOT NULL,
    status_limpeza VARCHAR(30) DEFAULT 'Normal',
    geom GEOMETRY(POINT, 4326)
);

CREATE TABLE IF NOT EXISTS turismo.postos_servico (
    id SERIAL PRIMARY KEY,
    nome_estabelecimento VARCHAR(120) NOT NULL,
    tipo_servico VARCHAR(80) NOT NULL, -- 'Posto de Combustível / Restaurante', 'SOS Usuário'
    km NUMERIC(6, 2) NOT NULL,
    geom GEOMETRY(POINT, 4326)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ambiental, hidrografia, turismo TO viasul_editor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ambiental, hidrografia, turismo TO viasul_editor;
GRANT SELECT ON ALL TABLES IN SCHEMA ambiental, hidrografia, turismo TO viasul_readonly;

-- ------------------------------------------------------------------------------
-- 8b. SCHEMA ANALISE_BR376
-- ------------------------------------------------------------------------------
GRANT USAGE ON SCHEMA analise_br376 TO viasul_admin, viasul_editor, viasul_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analise_br376 TO viasul_editor;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analise_br376 TO viasul_editor;
GRANT SELECT ON ALL TABLES IN SCHEMA analise_br376 TO viasul_readonly;
GRANT ALL ON SCHEMA analise_br376 TO viasul_admin;
GRANT ALL ON ALL TABLES IN SCHEMA analise_br376 TO viasul_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA analise_br376 TO viasul_admin;

-- Default Privileges para analise_br376
ALTER DEFAULT PRIVILEGES FOR ROLE somap IN SCHEMA analise_br376
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viasul_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE somap IN SCHEMA analise_br376
    GRANT SELECT ON TABLES TO viasul_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE somap IN SCHEMA analise_br376
    GRANT USAGE, SELECT ON SEQUENCES TO viasul_editor;

ALTER DEFAULT PRIVILEGES FOR ROLE admin_user IN SCHEMA analise_br376
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viasul_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE admin_user IN SCHEMA analise_br376
    GRANT SELECT ON TABLES TO viasul_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE admin_user IN SCHEMA analise_br376
    GRANT USAGE, SELECT ON SEQUENCES TO viasul_editor;

ALTER DEFAULT PRIVILEGES FOR ROLE maria IN SCHEMA analise_br376
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viasul_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE maria IN SCHEMA analise_br376
    GRANT SELECT ON TABLES TO viasul_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE maria IN SCHEMA analise_br376
    GRANT USAGE, SELECT ON SEQUENCES TO viasul_editor;

ALTER DEFAULT PRIVILEGES FOR ROLE joao IN SCHEMA analise_br376
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viasul_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE joao IN SCHEMA analise_br376
    GRANT SELECT ON TABLES TO viasul_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE joao IN SCHEMA analise_br376
    GRANT USAGE, SELECT ON SEQUENCES TO viasul_editor;

-- ------------------------------------------------------------------------------
-- 9. SCHEMA COMPARTILHADO (Default Privileges)
-- ------------------------------------------------------------------------------
-- Toda tabela criada por Maria nasce acessível por João e outros editores, e legível por Pedro
ALTER DEFAULT PRIVILEGES FOR ROLE maria IN SCHEMA compartilhado
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viasul_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE maria IN SCHEMA compartilhado
    GRANT SELECT ON TABLES TO viasul_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE maria IN SCHEMA compartilhado
    GRANT USAGE, SELECT ON SEQUENCES TO viasul_editor;

ALTER DEFAULT PRIVILEGES FOR ROLE joao IN SCHEMA compartilhado
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO viasul_editor;
ALTER DEFAULT PRIVILEGES FOR ROLE joao IN SCHEMA compartilhado
    GRANT SELECT ON TABLES TO viasul_readonly;
ALTER DEFAULT PRIVILEGES FOR ROLE joao IN SCHEMA compartilhado
    GRANT USAGE, SELECT ON SEQUENCES TO viasul_editor;

-- ------------------------------------------------------------------------------
-- 10. SCHEMA PUBLIC - REPOSITÓRIO CENTRAL DE ESTILOS DO QGIS (layer_styles)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.layer_styles (
    id SERIAL PRIMARY KEY,
    f_table_catalog VARCHAR(256),
    f_table_schema VARCHAR(256),
    f_table_name VARCHAR(256),
    f_geometry_column VARCHAR(256),
    styleName VARCHAR(30),
    styleQML TEXT,
    styleSLD TEXT,
    useAsDefault BOOLEAN,
    description TEXT,
    owner VARCHAR(30) DEFAULT CURRENT_USER,
    ui TEXT,
    update_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Somente o Admin tem permissão de escrita no layer_styles oficial
REVOKE ALL ON public.layer_styles FROM PUBLIC, viasul_editor, viasul_readonly;
GRANT SELECT ON public.layer_styles TO viasul_editor, viasul_readonly;
GRANT ALL ON public.layer_styles TO viasul_admin;
GRANT USAGE, SELECT ON SEQUENCE public.layer_styles_id_seq TO viasul_admin;

-- ------------------------------------------------------------------------------
-- 11. SCHEMA MAPAS - REPOSITÓRIO DE PROJETOS DO QGIS (.qgz no banco)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS mapas.qgis_projects (
    name TEXT PRIMARY KEY,
    metadata JSONB,
    content BYTEA,
    created_by VARCHAR(50) DEFAULT CURRENT_USER,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Somente o Admin altera os projetos mestres
REVOKE ALL ON mapas.qgis_projects FROM PUBLIC, viasul_editor, viasul_readonly;
GRANT SELECT ON mapas.qgis_projects TO viasul_editor, viasul_readonly;
GRANT ALL ON mapas.qgis_projects TO viasul_admin;
