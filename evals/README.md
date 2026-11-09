# Casos e protocolo de avaliação — Comunicação

Os arquivos development/cases.json e regression/cases.json são conjuntos públicos, sintéticos e versionados v1.0.0. Cobrem diálogo, ambiguidade, redação com preservação de restrições, tradução pt-BR/en e limites de voz/turno. Cada caso lista sinais observáveis, falhas críticas e exige revisão humana.

O compartimento reserve tem política v1.0.0, custódia de Pedro e fica fora do repositório. Está definido, mas não populado nesta entrega; nenhum caso privado foi criado ou publicado. Não copiar os casos de regressão para ajuste como se fossem reserva oculta.

Este protocolo não contém respostas do modelo. Casos textuais e critérios podem ser usados quando o runtime existir; voz/transcrição exigem payload sintético/licenciado e homologação real. O verificador só confere estrutura/cobertura, não qualidade de geração, tradução ou áudio. Não há baseline nem pontuação de desempenho nesta issue.

## Execução

Na raiz do repositório, execute scripts/validate_eval_cases.py com CPython 3.13.15. O programa valida versão, separação, cobertura de ferramentas, critérios e invariantes determinísticas aplicáveis. Um caso aprovado pelo validador de fixtures significa apenas que seus dados/rubricas são coerentes; não representa avaliação do agente, execução, baseline ou aceite humano.
