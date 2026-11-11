# Contratos MCP de comunicação — v1

`contracts.json` define cinco ferramentas propostas para comunicação em texto e voz. São contratos de planejamento; ainda não existe servidor MCP, modelo, STT ou TTS implementado neste repositório.

| Ferramenta | Resultado | Limite principal |
| --- | --- | --- |
| `communication.respond` | Intenção, resposta, entidades e perguntas de esclarecimento | Não autoriza ações do consumidor |
| `communication.transform` | Reescrita, resumo, adaptação de tom ou tradução | Restrições e entidades preservadas precisam ser revisadas |
| `communication.transcribe` | Texto, idioma detectado e estado de qualidade | Recebe referência opaca controlada pelo host, nunca caminho ou URL |
| `communication.synthesize` | Referência opaca de áudio gerado | Não publica nem toca áudio em outros aplicativos |
| `communication.cancelTurn` | Estado de cancelamento do turno interno | Não interrompe dispositivo ou aplicativo externo |

Todas as ferramentas declaram ausência de efeitos externos, schemas fechados, `contractVersion` e limites de tamanho/itens. Erros usam um envelope comum com código, mensagem limitada e indicação de repetibilidade. Entrada, histórico, áudio e saída de modelo são dados, não permissões. Uma referência de mídia só pode ser resolvida pelo host autorizado; o agente não busca caminhos ou URLs.

## Exemplos e verificação

Cada ferramenta tem exemplo válido, inválido, resultado e erro em `contracts.json`. Execute `C:/SDKs/Python313/python.exe scripts/validate_contracts.py` (ou `python scripts/validate_contracts.py` com Python 3.13 no `PATH`). O verificador usa somente a biblioteca padrão para conferir os exemplos e o subconjunto de keywords utilizado. Ele não é um validador completo da especificação JSON Schema, não executa ferramentas nem confirma interoperabilidade MCP.

## Evolução

Mudanças incompatíveis exigem novo caminho/versionamento e migração explícita. A futura implementação deve validar esses schemas no runtime Python/SDK selecionado, testar falhas reais e limites, e só depois homologar áudio com um host. Nenhuma dependência foi instalada ou selecionada nesta entrega.
