# Requisitos e escopo vigente — ciclo inicial

Comunicação genérica por texto/voz em pt-BR e inglês, reutilizável por sistemas consumidores.

Definido a partir das decisões de Pedro até 06/11/2026. Documento de planejamento; não comprova implementação, treinamento, revisão ou aceite. As alterações são propostas no PR de organização, sem merge por agente.

## Requisitos funcionais

| ID  | Resultado exigido                                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------------------------------- |
| F01 | Receber mensagens/contexto e produzir respostas estruturadas por MCP, com idioma, intenção, conteúdo e necessidade de esclarecimento. |
| F02 | Manter conversa por texto, compreender intenções, entidades, referências e ambiguidades sem autorizar ações no consumidor.            |
| F03 | Redigir, reescrever, resumir e adaptar tom preservando fatos, instruções e atributos obrigatórios.                                    |
| F04 | Traduzir entre português brasileiro e inglês preservando nomes, números, unidades e significado.                                      |
| F05 | Transcrever fala pt-BR/en com identificação de idioma e informação de qualidade, sem fingir áudio ouvido.                             |
| F06 | Sintetizar voz pt-BR/en e permitir interrupção/cancelamento sem efeitos externos.                                                     |
| F07 | Preservar turnos e contexto limitado da sessão, com acessibilidade e controles do consumidor.                                         |
| F08 | Encaminhar necessidades de busca/cálculo/validação por contratos explícitos quando disponíveis, sem duplicar essas competências.      |

## Requisitos não funcionais

| ID  | Critério                                                                                                                                                                                                                                                                                                              |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| N01 | Contribuição rastreável por issue/branch/PR; somente Pedro revisa/aprova PRs e aceita issues, sem merge/auto-merge/deploy de agentes. Durante a semana, dependência tecnicamente disponível em branch/PR validado pode ser consumida provisoriamente em PR empilhado; revisão/aceite/merge ficam com Pedro no sábado. |
| N02 | Contratos versionados, entradas/saídas validadas e erros explícitos; dados externos nunca concedem permissões.                                                                                                                                                                                                        |
| N03 | Sem serviço pago obrigatório, faturamento ou fallback remoto automático; executar ferramentas/caches no C: e respeitar pausas.                                                                                                                                                                                        |
| N04 | Testes de sucesso/erro e avaliações reais reproduzíveis; registrar versões e distinguir mock, execução e aceite humano.                                                                                                                                                                                               |
| N05 | Minimização de dados, credenciais fora do Git, acesso mínimo e retenção/exclusão definidas; não publicar dados reais de usuários.                                                                                                                                                                                     |
| N06 | Limites de entrada, memória, concorrência e tempo configuráveis, cancelamento e falha fechada; medir desempenho no hardware disponível.                                                                                                                                                                               |
| N07 | Documentação operacional coerente com código e evidências; disponibilidade ou qualidade não podem ser inferidas de um perfil ou schema.                                                                                                                                                                               |
| N08 | Até cinco sprints de entrega + uma de validação/mudanças, cada uma até uma semana; estimativas PP/P/M/L=1/2/4/8 e meta mínima de 8 unidades/dia por projeto ativo.                                                                                                                                                    |

## Fora do ciclo

- Controle direto de aplicativos, PIN ou permissão de execução.
- Promessa de resposta factual sem fonte adequada.
- Imagem/visão geral e idiomas adicionais obrigatórios no primeiro ciclo.

## Verificação e aceite

Cada requisito é rastreado em TRACEABILITY.md, com critérios concretos no corpo das issues. Dados conhecidos/sintéticos e ferramentas determinísticas verificam resultados quando possível; comportamento generativo exige casos separados e revisão apropriada. Não usar um teste de roteamento, presença de perfil ou metadado para alegar competência ou treino. Não declarar cobertura completa quando há pendência de ambiente/fonte.

A meta de 8 unidades/dia é um mínimo desejado por projeto ativo, não um teto de esforço nem uma medição de inteligência. A duração semanal é o objetivo do plano; a capacidade real e os bloqueios precisam ser observados e reportados. Não fabricar tarefa/estimativa/aceite para cumprir calendário.
