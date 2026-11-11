<!-- BEGIN CURRENT PLAN 2026-11-06 -->

# sofiee-agent-communication

Comunicação genérica por texto/voz em pt-BR e inglês, reutilizável por sistemas consumidores.

**Planejamento vigente em 06/11/2026: até 5 sprints de entrega + S6 de validação extra/mudanças.** As issues e a matriz documentam todo o ciclo; não comprovam implementação, treinamento, integração ou aceite. Preservar código e PRs existentes. Somente Pedro revisa/aprova PRs e aceita issues.

- [Requisitos e limites](docs/REQUIREMENTS.md)
- [Arquitetura e fronteiras](docs/ARCHITECTURE_PLAN.md)
- [Todas as sprints e issues](docs/DELIVERY_PLAN.md)
- [Rastreabilidade](docs/TRACEABILITY.md)
- [Execução semanal por dependências e PRs encadeados](docs/WEEKLY_EXECUTION.md)
- [Retomada diária](docs/EXECUTION_PLAN.md)
- [Contribuição](docs/CONTRIBUTION_POLICY.md)
- [Contratos MCP v1 — proposta da issue #5](contracts/v1/README.md)

Busca encontra fontes em qualquer lugar pertinente e preserva filtros do usuário; Validação escolhe a base adequada ao tipo de dado e verifica as referências independentemente. Não aplicar uma whitelist científica global ao Busca. O modelo pode ser compartilhado; as ferramentas e critérios de domínio são específicos.

Trabalho exclusivamente no C:, sem serviços pagos obrigatórios. SlothGeo é separado e adiado para 21/11, não um sexto agente desta rotina.
- Ambiente e versões locais: [inventário reproduzível](docs/LOCAL_ENVIRONMENT.md).
<!-- END CURRENT PLAN 2026-11-06 -->

<details>
<summary>Descrição anterior da base e propostas — consultar com o estado vivo dos PRs</summary>

# Sofiee — Agente de Comunicação

Comunicação em sistemas e processos de empresas.

Projeto independente da linha Sofiee, criado a pedido de Pedro em 05/11/2026. Este commit inicial registra finalidade, limites e preparação para o planejamento. Ainda não existe runtime, modelo treinado, ferramenta MCP ou integração implementada.

## Planejamento pendente

Canais, idiomas, modalidades, tipos de interação e limites de atuação. Casos de uso, contratos, avaliações, arquitetura, tecnologias e sprints serão definidos com Pedro no fim de semana. Consulte [o registro de escopo](docs/ESCOPO.md).

Depois dessa definição, todas as issues de todas as sprints planejadas devem ser criadas, com dependências e critérios de aceite. O formulário de issue já está disponível neste repositório.

## Portfólio

Este é um dos quatro agentes gerais: [comunicação](https://github.com/PHnsilva/sofiee-agent-communication), [cálculo](https://github.com/PHnsilva/sofiee-agent-calculation), [validação](https://github.com/PHnsilva/sofiee-agent-validation) e [busca](https://github.com/PHnsilva/sofiee-agent-search).

[SlothEngineer](https://github.com/PHnsilva/SlothEngineer) é um sistema separado, com direção inicial de especialização em DevOps. O chat **agents** acompanha os cinco projetos.

## Contribuições

O repositório é público para consulta e sugestões por issue ou PR. Mudanças posteriores ao bootstrap usam issue, branch e PR com evidências. Revisão e aceite são de Pedro.

</details>

## Runtime local proposto na issue #7

O núcleo usa contratos v1, valida entradas e saídas e permite operações de texto com um modelo local Ollama opt-in. O adaptador não habilita rede externa ou fallback remoto. Transcrição e síntese de áudio retornam indisponível até a integração de voz ser implementada. O runtime ainda não fornece servidor MCP; isso está separado na issue #8.

- Runtime: CPython 3.13.15.
- Verificações locais: C:\SDKs\Python313\python.exe -m unittest discover -s tests -v; C:\SDKs\Python313\python.exe scripts\validate_contracts.py; C:\SDKs\Python313\python.exe scripts\check_environment.py.
- O modelo usado precisa estar disponível num servidor Ollama em 127.0.0.1:11434 iniciado com cloud desativado. Defina SOFIEE_AGENT_LOCAL_MODEL com uma tag local validada antes de executar texto.
- Candidatura/licença/medição e limites: [seleção local de modelo](docs/LOCAL_MODEL_SELECTION.md).
- O CLI de uma chamada lê JSON {tool, input} de stdin e escreve um único resultado JSON. Ele não é um servidor MCP.

Exemplo de chamada com texto de teste:

    $env:SOFIEE_AGENT_LOCAL_MODEL = 'hf.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF:Q4_K_M'
    Get-Content -Raw .\request.json | C:\SDKs\Python313\python.exe scripts\run_runtime.py


## Servidor MCP local — issue #8

O servidor interno expõe somente as ferramentas MCP versionadas em `contracts/v1/contracts.json`. Execute com CPython 3.13.15 e as dependências exatas de `requirements.lock`: `python -m agent_runtime.mcp_server`. O transporte local usa stdio; stdout é reservado ao protocolo. Não fornece shell, caminhos de arquivo ou acesso de rede arbitrários. Operações que exigem modelo ou fonte continuam sujeitas aos limites e estados retornados pelo runtime.

Para preparar um ambiente virtual isolado com as versões fixadas, execute python -m pip install -r requirements.lock depois de ativar o CPython 3.13.15.
