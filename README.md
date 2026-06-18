# Police Operation Desktop

Interface desktop moderna para o sistema **Police Operation API**, desenvolvida com Python, Tkinter e ttkbootstrap.

---

## Sumário

- [Tecnologias](#tecnologias)
- [Arquitetura](#arquitetura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Configuração](#configuração)
- [Funcionalidades](#funcionalidades)
- [Fluxo de Uso](#fluxo-de-uso)
- [Estrutura de Arquivos](#estrutura-de-arquivos)

---

## Tecnologias

| Tecnologia | Versão |
|---|---|
| Python | 3.11+ |
| ttkbootstrap | 1.10.1 |
| requests | 2.31.0 |
| python-dotenv | 1.0.1 |
| Pillow | 10.3.0 |

---

## Arquitetura

Separação em camadas com responsabilidades bem definidas:

```
Screens    →  UI completa de cada tela (listas, formulários, detalhes)
Components →  Widgets reutilizáveis (header, sidebar, tabela, loading, dialogs)
Services   →  Comunicação HTTP com a Police Operation API
Models     →  Representação dos dados da API como objetos Python
Utils      →  Constantes e funções auxiliares
```

---

## Pré-requisitos

- Python 3.11 ou superior
- **Police Operation API** rodando em `http://localhost:5000`
- pip

---

## Instalação e Execução

```powershell
# 1. Acesse o diretório do projeto
cd police-operation-desktop

# 2. Crie e ative o ambiente virtual
py -3 -m venv venv
.\venv\Scripts\Activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o frontend (com a API já rodando em outro terminal)
python main.py
```

---

## Configuração

O arquivo `.env` contém apenas a URL da API:

```env
API_BASE_URL=http://localhost:5000
```

Altere essa variável se a API estiver em outro host ou porta.

---

## Funcionalidades

### Listagem de Operações
- Tabela com colunas: Nome, Tipo, Localização e Data de Criação
- ID gerenciado internamente — nunca exibido ao usuário
- Atualização manual via botão **Atualizar**
- Estado de seleção habilita/desabilita botões de ação automaticamente
- Double-click na linha abre os detalhes

### Nova Operação
- Formulário modal com campos: Nome, Tipo, Localização, Descrição
- **Seção dinâmica** baseada no tipo selecionado:
  - **Ostensiva**: checkboxes de armamentos, lista de viaturas (nome + blindada), checkboxes de cargos
  - **Investigativa**: pistola fixa (aviso visual), checkboxes de equipamentos, checkboxes de cargos
  - **Tática**: checkboxes de armamentos, lista de viaturas, checkboxes de cargos

### Editar Operação
- Selecione uma linha → clique **Editar**
- Formulário pré-preenchido com os dados da operação
- Salva via `PUT /operations/{id}`

### Visualizar Detalhes
- Selecione uma linha → clique **Visualizar** (ou dê double-click)
- Modal somente leitura com todos os campos e recursos
- Dados buscados via `GET /operations/{id}`

### Excluir Operação
- Selecione uma linha → clique **Excluir**
- Confirmação antes da exclusão
- Tabela atualizada automaticamente

### Gerar Relatório PDF
- Selecione uma linha → clique **Gerar PDF**
- O PDF é baixado de `GET /operations/{id}/report`
- Salvo automaticamente na pasta **Downloads** do usuário
- Opção de abrir o arquivo imediatamente

---

## Fluxo de Uso

```
1. Inicie a Police Operation API:
   cd police-operation-api && python run.py

2. Em outro terminal, inicie o desktop:
   cd police-operation-desktop && python main.py

3. A tabela carregará automaticamente todas as operações.

4. Use os botões da barra de ações para criar, editar,
   visualizar, excluir ou gerar PDFs das operações.
```

---

## Tratamento de Erros

| Cenário | Comportamento |
|---|---|
| API offline | MessageBox de erro com instrução de verificação |
| Timeout | Aviso com orientação para tentar novamente |
| Validação rejeitada (400) | Mensagem clara com o motivo da rejeição |
| Não encontrado (404) | Aviso de registro não encontrado |
| Erro do servidor (500) | Mensagem de erro interno com detalhe |

---

## Estrutura de Arquivos

```
police-operation-desktop/
│
├── main.py                          # Entry point — cria e inicializa o app
│
├── src/
│   ├── screens/
│   │   ├── operation_list_screen.py     # Tela principal (tabela + ações)
│   │   ├── operation_form_screen.py     # Formulário criar/editar (modal)
│   │   ├── operation_details_screen.py  # Detalhes somente leitura (modal)
│   │   └── report_screen.py             # Serviço de geração de PDF
│   │
│   ├── services/
│   │   └── operation_api_service.py     # HTTP client da Police Operation API
│   │
│   ├── components/
│   │   ├── header.py          # Barra de título superior
│   │   ├── sidebar.py         # Menu de navegação lateral
│   │   ├── operation_table.py # Treeview com mapeamento interno de IDs
│   │   ├── dialogs.py         # Helpers para MessageBox padronizados
│   │   └── loading.py         # Overlay de carregamento (progress bar)
│   │
│   ├── models/
│   │   └── __init__.py        # OperationModel e VehicleModel (dataclasses)
│   │
│   ├── utils/
│   │   ├── constants.py       # Cores, fontes, tipos, listas de domínio
│   │   └── helpers.py         # Formatação, caminhos, center_window, etc.
│   │
│   └── assets/                # (reservado para ícones futuros)
│
├── .env
├── requirements.txt
└── README.md
```
