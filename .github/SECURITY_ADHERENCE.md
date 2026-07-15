# Aderência à Segurança da Informação

Este documento declara como este repositório atende às diretrizes da **NSI.04 – Norma de Desenvolvimento Seguro** (SciELO/FapUNIFESP), alinhada à NBR ISO/IEC 27.001:2022 e à LGPD.

> Preencher e manter atualizado a cada mudança relevante de arquitetura, dependências críticas ou classificação de dados. Revisar no mínimo a cada release maior.

## 1. Identificação

| Campo | Valor |
|---|---|
| Nome do sistema | *(ex: OJS/PKP, SciELO Data, ARQUIWEB...)* |
| Responsável técnico | |
| Classificação da informação tratada | Pública / Interna / Restrita / Sigilosa |
| Dados pessoais tratados (LGPD)? | Sim / Não — se sim, quais categorias |
| Ambiente de produção | *(ex: Kubernetes on-prem, Rocky Linux 9...)* |

## 2. Controles de segurança aplicados (NSI.04 §3)

- [ ] Segregação entre ambientes de dev, teste e produção (§3.1)
- [ ] Controle de acesso ao banco de dados com permissões mínimas necessárias, sem uso de usuário root (§3.2)
- [ ] Senhas e segredos gerenciados fora do código-fonte (§3.3) — informar cofre utilizado: *(ex: GitHub Secrets, Vault...)*
- [ ] Comunicação via HTTPS/TLS em todas as interfaces expostas (§3.4)
- [ ] Prevenção a SQL Injection, XSS e quebra de autenticação/sessão (§3.5)
- [ ] Logs de auditoria implementados conforme criticidade do sistema (§3.6)
- [ ] Procedimento de backup e teste de restauração definido (§3.7)
- [ ] Dados sensíveis criptografados em trânsito e em repouso, sem algoritmos obsoletos (MD5, SHA1, DES/3DES, RC2/RC4, MD4) (§3.8)

## 3. Pipeline de CI/CD e verificação automatizada

| Ferramenta | Finalidade | Gate obrigatório? |
|---|---|---|
| SonarQube | Qualidade de código e SAST | Sim/Não |
| Trivy | Vulnerabilidades na imagem de container | Sim/Não |
| SBOM | Inventário de dependências (software bill of materials) | Sim/Não |
| ArgoCD | Deploy controlado em homologação/produção | Sim/Não |

Critério de aprovação do gate: *(ex: zero vulnerabilidades críticas/altas sem exceção documentada)*

## 4. Ciclo de vida (NSI.04 §4)

- [ ] Requisitos de segurança levantados junto às partes interessadas (§4.1)
- [ ] Riscos de segurança avaliados no planejamento (§4.2)
- [ ] Separação de ambientes validada na análise (§4.3)
- [ ] Revisão de código por membro qualificado antes do merge (§4.4)
- [ ] Testes com dados fictícios/anonimizados, ambiente de teste isolado (§4.5)
- [ ] Plano de implantação com procedimento de rollback (§4.6)
- [ ] Processo de manutenção com aplicação de patches e gestão de mudanças — GMUD (§4.7)

## 5. Desenvolvimento terceirizado (se aplicável, NSI.04 §6)

- [ ] Contrato prevê cláusulas de confidencialidade e propriedade intelectual
- [ ] Acesso do terceiro limitado ao estritamente necessário
- [ ] Revisões de código e auditorias técnicas realizadas

## 6. Exceções e riscos aceitos

Registrar aqui qualquer desvio das diretrizes acima, com justificativa técnica, aprovação e prazo de mitigação, conforme previsto na NSI.04 (seção 3, introdução).

| Desvio | Justificativa | Aprovado por | Prazo de mitigação |
|---|---|---|---|
| | | | |

## 7. Histórico

| Data | Alteração | Responsável |
|---|---|---|
| | Criação do documento | |

---
*Referência normativa: NSI.04 - Norma de Desenvolvimento Seguro, v3.2 (07/07/2025).*