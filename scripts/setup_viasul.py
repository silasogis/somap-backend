"""
Script de Inicialização e Carga de Dados do viasul_spatial_db
Executar via terminal:
  docker compose exec api python -m scripts.setup_viasul
"""
import asyncio
import os
import asyncpg
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("POSTGRES_HOST", "db")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_USER = os.getenv("POSTGRES_USER", "somap")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "somap_secret")
DEFAULT_DB = os.getenv("POSTGRES_DB", "somap")
TARGET_DB = "viasul_spatial_db"

SCRIPTS_DIR = Path(__file__).parent / "viasul"

async def create_database_if_not_exists():
    print(f"[*] Conectando ao PostgreSQL ({PG_HOST}:{PG_PORT}/{DEFAULT_DB}) como '{PG_USER}'...")
    conn = await asyncpg.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=DEFAULT_DB
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", TARGET_DB
        )
        if not exists:
            print(f"[+] Criando banco de dados '{TARGET_DB}'...")
            await conn.execute(f'CREATE DATABASE "{TARGET_DB}" OWNER "{PG_USER}";')
            print(f"[✓] Banco '{TARGET_DB}' criado com sucesso.")
        else:
            print(f"[i] Banco '{TARGET_DB}' já existe.")
    finally:
        await conn.close()

async def run_sql_file(conn, file_path: Path):
    print(f"[*] Executando script SQL: {file_path.name}...")
    sql_content = file_path.read_text(encoding="utf-8")
    await conn.execute(sql_content)
    print(f"[✓] {file_path.name} executado com sucesso.")

async def seed_data(conn):
    print("[*] Inserindo dados geoespaciais de demonstração (Rodovia BR-116 - Contorno Leste / Sul)...")

    # 1. Admin tables
    await conn.execute("""
        INSERT INTO admin.admin_stuff (nome, descricao, geom) VALUES
        ('Ponto de Controle Operacional 01', 'Instalação de segurança nível 1', ST_SetSRID(ST_MakePoint(-49.273, -25.438), 4326)),
        ('Ponto de Controle Operacional 02', 'Instalação de segurança nível 2', ST_SetSRID(ST_MakePoint(-49.255, -25.452), 4326))
        ON CONFLICT DO NOTHING;

        INSERT INTO admin.other_admin_stuff (codigo_segredo, detalhes, geom) VALUES
        ('SEC-ALPHA-99', 'Chaves e credenciais dos armários de fibra óptica', ST_SetSRID(ST_MakePoint(-49.280, -25.430), 4326))
        ON CONFLICT DO NOTHING;
    """)

    # 2. Limites
    await conn.execute("""
        INSERT INTO limites.pracas_pedagio (nome_praca, km, tarifa_base, geom) VALUES
        ('Praça Fazenda Rio Grande', 128.5, 10.20, ST_SetSRID(ST_MakePoint(-49.308, -25.658), 4326)),
        ('Praça São José dos Pinhais', 62.0, 11.50, ST_SetSRID(ST_MakePoint(-49.124, -25.568), 4326))
        ON CONFLICT DO NOTHING;

        INSERT INTO limites.faixa_dominio (trecho, largura_metros, geom) VALUES
        ('BR-116 - Km 100 ao 120 (Curitiba/Fazenda Rio Grande)', 60.0, 
         ST_SetSRID(ST_GeomFromText('MULTIPOLYGON(((-49.270 -25.490, -49.265 -25.490, -49.290 -25.600, -49.295 -25.600, -49.270 -25.490)))'), 4326))
        ON CONFLICT DO NOTHING;
    """)

    # 3. Fundiario
    await conn.execute("""
        INSERT INTO fundiario.imoveis_lindeiros (matricula, proprietario, cpf_cnpj, valor_avaliado, status_desapropriacao, notas_vistoria, geom) VALUES
        ('MAT-88421', 'Agropecuária Vale Verde Ltda', '12.345.678/0001-90', 450000.00, 'Em Negociação', 'Vistoria inicial realizada pelo fiscal Pedro em 10/09/2026. A cerca lateral requer recuo de 4m.',
         ST_SetSRID(ST_GeomFromText('MULTIPOLYGON(((-49.285 -25.540, -49.280 -25.540, -49.280 -25.545, -49.285 -25.545, -49.285 -25.540)))'), 4326)),
        ('MAT-99104', 'Espólio de Roberto Silveira', '234.567.890-12', 280000.00, 'Acordo Firmado', 'Documentação cartorial validada.',
         ST_SetSRID(ST_GeomFromText('MULTIPOLYGON(((-49.290 -25.550, -49.286 -25.550, -49.286 -25.554, -49.290 -25.554, -49.290 -25.550)))'), 4326))
        ON CONFLICT DO NOTHING;
    """)

    # 4. Infraestrutura
    await conn.execute("""
        INSERT INTO infraestrutura.obras_arte_especiais (nome_oae, tipo, extensao_metros, geom) VALUES
        ('Ponte Rio Iguaçu - BR-116', 'Ponte', 180.0, ST_SetSRID(ST_MakePoint(-49.282, -25.578), 4326)),
        ('Viaduto Acesso Contorno Leste', 'Viaduto', 95.0, ST_SetSRID(ST_MakePoint(-49.230, -25.490), 4326))
        ON CONFLICT DO NOTHING;

        INSERT INTO infraestrutura.defensas_metalicas (rodovia, lado, tipo_defensa, geom) VALUES
        ('BR-116', 'Canteiro Central', 'Barreira New Jersey', 
         ST_SetSRID(ST_GeomFromText('MULTILINESTRING((-49.270 -25.495, -49.275 -25.520, -49.280 -25.550))'), 4326)),
        ('BR-116', 'Direito', 'Semirrígida W-Beam', 
         ST_SetSRID(ST_GeomFromText('MULTILINESTRING((-49.271 -25.495, -49.276 -25.520, -49.281 -25.550))'), 4326))
        ON CONFLICT DO NOTHING;

        INSERT INTO infraestrutura.pavimento (rodovia, tipo_pavimento, condicao_iri, geom) VALUES
        ('BR-116', 'CBUQ', 1.85, 
         ST_SetSRID(ST_GeomFromText('MULTILINESTRING((-49.270 -25.490, -49.280 -25.550, -49.300 -25.620))'), 4326))
        ON CONFLICT DO NOTHING;
    """)

    # 5. Hidrografia, Turismo, Ambiental
    await conn.execute("""
        INSERT INTO hidrografia.bueiros_drenagem (tipo, km, status_limpeza, geom) VALUES
        ('BDTC 1.00m', 104.2, 'Normal', ST_SetSRID(ST_MakePoint(-49.272, -25.502), 4326)),
        ('BSCC 2.00x2.00m', 111.8, 'Desobstrução Solicitada', ST_SetSRID(ST_MakePoint(-49.283, -25.565), 4326))
        ON CONFLICT DO NOTHING;

        INSERT INTO turismo.postos_servico (nome_estabelecimento, tipo_servico, km, geom) VALUES
        ('Posto Graal Contorno', 'Posto de Combustível / Restaurante 24h', 108.0, ST_SetSRID(ST_MakePoint(-49.276, -25.530), 4326)),
        ('Base SOS Usuário 03 - Viasul', 'SOS / Ambulância / Guicho', 118.5, ST_SetSRID(ST_MakePoint(-49.298, -25.610), 4326))
        ON CONFLICT DO NOTHING;

        INSERT INTO ambiental.app (tipo_app, geom) VALUES
        ('Margem do Rio Iguaçu', 
         ST_SetSRID(ST_GeomFromText('MULTIPOLYGON(((-49.290 -25.575, -49.270 -25.575, -49.270 -25.582, -49.290 -25.582, -49.290 -25.575)))'), 4326))
        ON CONFLICT DO NOTHING;
    """)

    # 6. Exemplo de Ordens de Serviço cadastradas por Maria e João (para teste de RLS)
    await conn.execute("""
        INSERT INTO transporte.ordens_servico (codigo_os, rodovia, km, tipo_servico, prioridade, status, created_by, geom) VALUES
        ('OS-2026-001', 'BR-116', 105.4, 'Tapa-Buraco Pista Norte', 'Alta', 'Em Execução', 'maria', ST_SetSRID(ST_MakePoint(-49.273, -25.510), 4326)),
        ('OS-2026-002', 'BR-116', 114.2, 'Reparo de Defensa Metálica', 'Média', 'Pendente', 'joao', ST_SetSRID(ST_MakePoint(-49.288, -25.580), 4326))
        ON CONFLICT DO NOTHING;
    """)

    print("[✓] Dados de demonstração inseridos com sucesso.")

async def main():
    print("=" * 70)
    print(" PROVISIONAMENTO DO BANCO MULTIUSUÁRIO: viasul_spatial_db ")
    print("=" * 70)
    await create_database_if_not_exists()

    conn = await asyncpg.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASSWORD,
        database=TARGET_DB
    )
    try:
        await run_sql_file(conn, SCRIPTS_DIR / "01_viasul_init.sql")
        await run_sql_file(conn, SCRIPTS_DIR / "02_viasul_tables_and_security.sql")
        await seed_data(conn)
        print("\n[🎉] Provisionamento concluído com sucesso!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
