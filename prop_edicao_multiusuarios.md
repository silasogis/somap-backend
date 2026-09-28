Aqui estão propostas de regras de negócio de edição multiusuário baseadas na experiência de uso no QGIS-PostGIS. Organizadas por camada de controle:

**1. Hierarquia geral de permissões**
Toda permissão é explícita e em cascata: banco → schema → tabela → linha → coluna. Nenhum nível herda acesso do anterior automaticamente — ter `usage` num schema não dá `select` nas tabelas dele; ter `select` numa tabela não dá acesso a todas as colunas ou linhas dela. O acesso público (`PUBLIC`, ou seja, qualquer role de login) é revogado por padrão em todos os níveis; tudo precisa ser concedido caso a caso.

**2. Papéis de usuário (roles)**
- **Admin** (superusuário): acesso irrestrito a todos os schemas, tabelas, linhas e colunas, incluindo o schema `audit` e a tabela `layer_styles`.
- **Editores** (Sarah, John — role de grupo `camloops_editor`): podem conectar ao banco, ler/inserir/atualizar/excluir nas tabelas liberadas, criar tabelas em schemas específicos.
- **Leitor** (Phil — role de grupo `camloops_readonly`): apenas `select` nas tabelas liberadas; sem permissão de inserir, atualizar (exceto exceção pontual) ou excluir.
- Roles de grupo (sem login) concentram as permissões; roles de login (usuários individuais) herdam por membership — e essas mesmas roles valem em qualquer banco do servidor.

**3. Regra de banco de dados**
Toda role precisa de permissão explícita de `CONNECT` para acessar o banco (sem ela, o QGIS retorna "user does not have connect privilege"). `CREATE` (criar schemas) fica restrito a admins; `TEMP` permite tabelas temporárias.

**4. Regra de schema**
Acesso a um schema exige `USAGE` (e, para quem cria tabelas, `CREATE`) concedido separadamente por schema. O schema `admin` só é visível para o admin; editores veem apenas os schemas liberados ao grupo deles; o leitor não acessa o schema `admin` de forma alguma. O schema `public` recebe tratamento especial: leitura/execução de funções liberada, mas escrita (principalmente na tabela `layer_styles`) fica travada para não-admins.

**5. Regra de tabela**
Por tabela, a permissão é granular entre `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES` e `TRIGGER`. Editores recebem o pacote completo nas tabelas do seu domínio; leitores recebem só `SELECT`. Quem insere/edita também precisa de `USAGE` na *sequence* da tabela (para gerar IDs) — sem isso, o erro é "can't create sequence"; leitores não precisam dessa permissão, pois não inserem linhas.

**6. Regra de coluna (column-level security)**
Um usuário pode ter `SELECT` em todas as colunas de uma tabela, mas `UPDATE` restrito a apenas uma coluna específica. No exemplo, Phil (leitor) vê todos os campos de `property_parcels`, mas só pode editar a coluna `notes`; tentar alterar qualquer outro campo gera erro de permissão negada na tabela.

**7. Regra de linha (Row-Level Security)**
Em tabelas como `work_orders`, cada editor só vê e edita as linhas que ele mesmo criou — controlado por uma política RLS vinculada a um campo `created_by`, que é preenchido automaticamente por trigger (o usuário não escolhe esse valor). O admin, por não estar sujeito à política, vê todas as linhas de todos os editores. O leitor, sem acesso à tabela, não vê nada.

**8. Regra de permissões padrão / compartilhamento automático (schema "share")**
Qualquer tabela nova criada por um editor nesse schema já nasce com permissões padrão pré-definidas (`ALTER DEFAULT PRIVILEGES`): visível para outros editores em modo completo (select/insert/update/delete) e para leitores em modo `select`. Essa regra precisa ser configurada individualmente para cada editor "dono" de dados — senão os dados de Sarah não aparecem automaticamente para John, por exemplo.

**9. Regra de simbologia padrão**
A simbologia default de uma camada é armazenada centralizadamente (tabela `layer_styles`, no schema public). Somente o admin tem permissão de escrita nela — quando outro usuário tenta salvar um estilo como padrão, a operação falha silenciosamente. Qualquer usuário pode, porém, alterar a simbologia localmente na sua sessão QGIS sem afetar o padrão dos outros.

**10. Regra de projetos QGIS salvos no banco**
Projetos salvos no schema `maps` seguem a mesma lógica de permissão de escrita restrita: poucos usuários (idealmente só o admin) devem poder sobrescrever a estrutura do projeto. Usuários somente leitura podem abrir o projeto travado e usar templates de impressão prontos, sem alterar o conteúdo.

**11. Regra de concorrência ("last save wins")**
Não há bloqueio de conflito nativo: se dois usuários editam o mesmo dado ou a mesma estrutura de projeto ao mesmo tempo, a última gravação sobrescreve a anterior sem aviso. A visibilidade das mudanças de outros usuários só é atualizada quando o usuário faz refresh (ou zoom, que reconsulta o banco) — não há push automático.

**12. Regras de automação (triggers)**
Campos calculados (como área, em `area_sqm`, via `st_area()` arredondado) e campos de metadado (`created_by`, timestamps) são preenchidos automaticamente por trigger no insert/update — o usuário não os edita manualmente, eles ficam sob controle do banco.

**13. Regras de auditoria**
O schema `audit` é acessível somente ao admin. Toda operação de insert/update/delete nas tabelas monitoradas é registrada com valores "antes/depois", usuário e timestamp, permitindo reverter uma exclusão acidental. Para evitar que a tabela de auditoria cresça sem controle (ex.: scripts automáticos gerando muitas mudanças), a regra operacional sugerida é exportar periodicamente para CSV e esvaziar a tabela.

**14. Regras de integridade/validação de dados**
Constraints de tipo de dado, de intervalo (ex.: valor não pode ser maior que 62 nem menor que -78) e de chave estrangeira (restringindo a um conjunto fixo de valores válidos, como sim/não) impedem a inserção de dados inválidos independentemente do nível de permissão do usuário — qualquer violação gera erro do banco antes mesmo de chegar às regras de RLS ou coluna.