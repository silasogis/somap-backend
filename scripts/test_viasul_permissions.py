"""
Script de Validação e Testes Automatizados de Permissões
Testa todas as regras de negócio multiusuário no banco viasul_spatial_db
Executar via terminal:
  docker compose exec api python -m scripts.test_viasul_permissions
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

PG_HOST = os.getenv("POSTGRES_HOST", "db")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
TARGET_DB = "viasul_spatial_db"

USERS = {
    "admin": ("admin_user", "viasul_admin@2026"),
    "maria": ("maria", "maria@2026"),
    "joao":  ("joao", "joao@2026"),
    "pedro": ("pedro", "pedro@2026"),
}

async def get_conn(user_key: str):
    user, password = USERS[user_key]
    return await asyncpg.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=user,
        password=password,
        database=TARGET_DB
    )

async def test_1_admin_schema_isolation():
    print("\n--- [TESTE 1] Isolamento Didático no Schema 'admin' ---")
    conn_admin = await get_conn("admin")
    conn_maria = await get_conn("maria")
    conn_pedro = await get_conn("pedro")

    try:
        # 1.1 Admin vê ambas
        c1 = await conn_admin.fetchval("SELECT COUNT(*) FROM admin.admin_stuff;")
        c2 = await conn_admin.fetchval("SELECT COUNT(*) FROM admin.other_admin_stuff;")
        print(f"  [✓] Admin acessa admin_stuff ({c1} linhas) e other_admin_stuff ({c2} linhas).")

        # 1.2 Maria (Editora) vê admin_stuff
        c_maria = await conn_maria.fetchval("SELECT COUNT(*) FROM admin.admin_stuff;")
        print(f"  [✓] Maria (Editora) acessa admin_stuff ({c_maria} linhas).")

        # 1.3 Maria NÃO vê other_admin_stuff (deve falhar)
        try:
            await conn_maria.fetchval("SELECT COUNT(*) FROM admin.other_admin_stuff;")
            assert False, "Maria NÃO deveria ter acesso a other_admin_stuff!"
        except asyncpg.InsufficientPrivilegeError:
            print("  [✓] Maria foi bloqueada com sucesso em other_admin_stuff (InsufficientPrivilege).")

        # 1.4 Pedro (Leitor) NÃO tem USAGE no schema admin (deve falhar)
        try:
            await conn_pedro.fetchval("SELECT COUNT(*) FROM admin.admin_stuff;")
            assert False, "Pedro NÃO deveria ter acesso ao schema admin!"
        except asyncpg.InsufficientPrivilegeError:
            print("  [✓] Pedro foi bloqueado com sucesso em admin.admin_stuff (Sem USAGE no schema).")

    finally:
        await conn_admin.close()
        await conn_maria.close()
        await conn_pedro.close()

async def test_2_column_level_security():
    print("\n--- [TESTE 2] Column-Level Security (CLS) em 'fundiario.imoveis_lindeiros' ---")
    conn_pedro = await get_conn("pedro")
    conn_maria = await get_conn("maria")

    try:
        # 2.1 Pedro consegue ler todas as colunas
        row = await conn_pedro.fetchrow("SELECT matricula, proprietario, valor_avaliado, notas_vistoria FROM fundiario.imoveis_lindeiros LIMIT 1;")
        print(f"  [✓] Pedro (Leitor) lê todas as colunas do imóvel {row['matricula']}.")

        # 2.2 Pedro atualiza a coluna notas_vistoria com sucesso
        nova_nota = "Vistoria complementar efetuada por Pedro: marcos divisórios conferidos."
        await conn_pedro.execute(
            "UPDATE fundiario.imoveis_lindeiros SET notas_vistoria = $1 WHERE matricula = 'MAT-88421';",
            nova_nota
        )
        nota_atualizada = await conn_pedro.fetchval("SELECT notas_vistoria FROM fundiario.imoveis_lindeiros WHERE matricula = 'MAT-88421';")
        assert nota_atualizada == nova_nota
        print("  [✓] Pedro atualizou 'notas_vistoria' com sucesso.")

        # 2.3 Pedro tenta alterar 'proprietario' ou 'valor_avaliado' (deve falhar)
        try:
            await conn_pedro.execute("UPDATE fundiario.imoveis_lindeiros SET proprietario = 'Novo Dono Invalido' WHERE matricula = 'MAT-88421';")
            assert False, "Pedro NÃO deveria poder atualizar a coluna proprietario!"
        except asyncpg.InsufficientPrivilegeError:
            print("  [✓] Pedro foi bloqueado ao tentar alterar coluna não autorizada ('proprietario').")

    finally:
        await conn_pedro.close()
        await conn_maria.close()

async def test_3_row_level_security():
    print("\n--- [TESTE 3] Row-Level Security (RLS) em 'transporte.ordens_servico' ---")
    conn_maria = await get_conn("maria")
    conn_joao = await get_conn("joao")
    conn_admin = await get_conn("admin")

    try:
        # Inserir OS via Maria
        await conn_maria.execute("""
            INSERT INTO transporte.ordens_servico (codigo_os, rodovia, km, tipo_servico, prioridade, geom)
            VALUES ('OS-MARIA-999', 'BR-116', 105.4, 'Tapa-Buraco Pista Norte', 'Alta', ST_SetSRID(ST_MakePoint(-49.273, -25.510), 4326))
            ON CONFLICT (codigo_os) DO NOTHING;
        """)

        # Inserir OS via João
        await conn_joao.execute("""
            INSERT INTO transporte.ordens_servico (codigo_os, rodovia, km, tipo_servico, prioridade, geom)
            VALUES ('OS-JOAO-888', 'BR-116', 114.2, 'Reparo de Defensa Metálica', 'Média', ST_SetSRID(ST_MakePoint(-49.288, -25.580), 4326))
            ON CONFLICT (codigo_os) DO NOTHING;
        """)

        # 3.1 Maria lista OS: deve ver apenas as criadas por 'maria'
        os_maria = await conn_maria.fetch("SELECT codigo_os, created_by FROM transporte.ordens_servico;")
        for r in os_maria:
            assert r["created_by"] == "maria", f"Maria viu OS de outro usuário: {r['codigo_os']} ({r['created_by']})"
        print(f"  [✓] Maria visualiza apenas suas próprias OS ({len(os_maria)} registros).")

        # 3.2 João lista OS: deve ver apenas as criadas por 'joao'
        os_joao = await conn_joao.fetch("SELECT codigo_os, created_by FROM transporte.ordens_servico;")
        for r in os_joao:
            assert r["created_by"] == "joao", f"João viu OS de outro usuário: {r['codigo_os']} ({r['created_by']})"
        print(f"  [✓] João visualiza apenas suas próprias OS ({len(os_joao)} registros).")

        # 3.3 Maria tenta atualizar a OS do João (deve afetar 0 linhas por causa do RLS)
        res = await conn_maria.execute("UPDATE transporte.ordens_servico SET status = 'Cancelada' WHERE codigo_os = 'OS-JOAO-888';")
        assert res == "UPDATE 0", f"Maria conseguiu alterar OS de João: {res}"
        print("  [✓] Maria foi impedida pelo RLS de alterar ou enxergar a OS de João (UPDATE 0).")

        # 3.4 Admin lista OS: deve ver todas (Maria + João)
        os_admin = await conn_admin.fetch("SELECT codigo_os, created_by FROM transporte.ordens_servico;")
        criadores = {r["created_by"] for r in os_admin}
        assert "maria" in criadores and "joao" in criadores
        print(f"  [✓] Admin visualiza todas as OS sem restrição de RLS ({len(os_admin)} registros).")

    finally:
        await conn_maria.close()
        await conn_joao.close()
        await conn_admin.close()

async def test_4_geometric_triggers():
    print("\n--- [TESTE 4] Triggers de Automação Geométrica e Metadados ---")
    conn_maria = await get_conn("maria")

    try:
        # Inserir uma defesa metálica sem passar extensao_km nem created_by
        await conn_maria.execute("""
            INSERT INTO infraestrutura.defensas_metalicas (rodovia, lado, tipo_defensa, geom)
            VALUES ('BR-116', 'Direito', 'Semirrígida W-Beam', 
                    ST_SetSRID(ST_GeomFromText('MULTILINESTRING((-49.270 -25.500, -49.270 -25.510))'), 4326));
        """)

        row = await conn_maria.fetchrow("""
            SELECT id, extensao_km, created_by, created_at 
            FROM infraestrutura.defensas_metalicas 
            WHERE created_by = 'maria' 
            ORDER BY id DESC LIMIT 1;
        """)

        assert row["created_by"] == "maria"
        assert float(row["extensao_km"]) > 0.9  # ~1.1 km projetado
        print(f"  [✓] Trigger calculou extensão automaticamente: {row['extensao_km']} km (Criado por: {row['created_by']}).")

    finally:
        await conn_maria.close()

async def test_5_audit_logs():
    print("\n--- [TESTE 5] Auditoria e Rastreabilidade (Schema 'audit') ---")
    conn_admin = await get_conn("admin")
    conn_pedro = await get_conn("pedro")

    try:
        # Admin consulta histórico de logs gravados pelos testes anteriores
        logs = await conn_admin.fetch("SELECT schema_name, table_name, user_name, action FROM audit.logged_actions ORDER BY id DESC LIMIT 5;")
        assert len(logs) > 0
        print(f"  [✓] Auditoria registrou com sucesso {len(logs)} eventos recentes. Último evento: {logs[0]['action']} em {logs[0]['table_name']} por '{logs[0]['user_name']}'.")

        # Pedro tenta ler a tabela de auditoria (deve falhar)
        try:
            await conn_pedro.fetchval("SELECT COUNT(*) FROM audit.logged_actions;")
            assert False, "Pedro NÃO deveria ter acesso ao schema audit!"
        except asyncpg.InsufficientPrivilegeError:
            print("  [✓] Pedro foi bloqueado ao tentar consultar o schema audit (Acesso restrito ao Admin).")

    finally:
        await conn_admin.close()
        await conn_pedro.close()

async def test_6_shared_schema_default_privileges():
    print("\n--- [TESTE 6] Permissões Padrão no Schema 'compartilhado' ---")
    conn_maria = await get_conn("maria")
    conn_joao = await get_conn("joao")
    conn_pedro = await get_conn("pedro")

    try:
        # Maria cria tabela nova no schema compartilhado
        await conn_maria.execute("""
            CREATE TABLE IF NOT EXISTS compartilhado.inspecoes_campo (
                id SERIAL PRIMARY KEY,
                titulo VARCHAR(100),
                observacao TEXT,
                geom GEOMETRY(POINT, 4326)
            );
        """)
        print("  [✓] Maria criou a tabela 'compartilhado.inspecoes_campo'.")

        # João insere na tabela criada por Maria (graças ao ALTER DEFAULT PRIVILEGES)
        await conn_joao.execute("""
            INSERT INTO compartilhado.inspecoes_campo (titulo, observacao, geom)
            VALUES ('Inspeção Drenagem Km 110', 'Bueiro limpo', ST_SetSRID(ST_MakePoint(-49.27, -25.50), 4326));
        """)
        print("  [✓] João inseriu dados na tabela criada por Maria sem necessidade de GRANT manual.")

        # Pedro lê a tabela
        count = await conn_pedro.fetchval("SELECT COUNT(*) FROM compartilhado.inspecoes_campo;")
        print(f"  [✓] Pedro leu {count} registro(s) da tabela compartilhada.")

        # Pedro tenta inserir (deve falhar, pois só tem SELECT)
        try:
            await conn_pedro.execute("INSERT INTO compartilhado.inspecoes_campo (titulo) VALUES ('Invalido');")
            assert False, "Pedro NÃO deveria poder inserir em compartilhado!"
        except asyncpg.InsufficientPrivilegeError:
            print("  [✓] Pedro foi bloqueado ao tentar inserir em 'compartilhado' (Somente Leitura).")

    finally:
        await conn_maria.close()
        await conn_joao.close()
        await conn_pedro.close()

async def test_7_qgis_styles_lock():
    print("\n--- [TESTE 7] Bloqueio de Estilos do QGIS ('public.layer_styles') ---")
    conn_admin = await get_conn("admin")
    conn_maria = await get_conn("maria")

    try:
        # Admin insere estilo padrão
        await conn_admin.execute("""
            INSERT INTO public.layer_styles (f_table_schema, f_table_name, styleName, styleQML, useAsDefault)
            VALUES ('infraestrutura', 'defensas_metalicas', 'Padrao_Viasul', '<qgis style="w-beam"/>', true);
        """)
        print("  [✓] Admin cadastrou estilo oficial na tabela 'layer_styles'.")

        # Maria tenta salvar/modificar o estilo padrão oficial (deve falhar)
        try:
            await conn_maria.execute("""
                INSERT INTO public.layer_styles (f_table_schema, f_table_name, styleName, styleQML)
                VALUES ('infraestrutura', 'defensas_metalicas', 'Tentativa_Editor', '<qgis/>');
            """)
            assert False, "Maria NÃO deveria poder gravar na tabela layer_styles!"
        except asyncpg.InsufficientPrivilegeError:
            print("  [✓] Maria foi bloqueada ao tentar sobrescrever estilos oficiais (Apenas Admin pode gravar).")

    finally:
        await conn_admin.close()
        await conn_maria.close()

async def main():
    print("=" * 75)
    print(" INICIANDO BATERIA DE TESTES DE SEGURANÇA E REGRAS MULTIUSUÁRIO (QGIS/POSTGIS) ")
    print("=" * 75)

    await test_1_admin_schema_isolation()
    await test_2_column_level_security()
    await test_3_row_level_security()
    await test_4_geometric_triggers()
    await test_5_audit_logs()
    await test_6_shared_schema_default_privileges()
    await test_7_qgis_styles_lock()

    print("\n" + "=" * 75)
    print(" [🎉 SUCESSO TOTAL] TODAS AS 14 REGRAS DE NEGÓCIO VALIDADAS COM 100% DE ÊXITO! ")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(main())
