_Update: Development team, 16-Oct-2026_

# Envio de logs de acesso ao Usage

O container `opac-log-shipper` só transporta logs de acesso já fechados para o bucket MinIO do Usage. Ele não altera bytes, compressão, nome nem a árvore `ano/Mês`. A rotação continua a cargo do Nginx ou do logrotate. A validação, o parsing e as métricas continuam no Usage.

O estado fica no `opac.sqlite` do site, nas tabelas `log_shipment` e `log_shipper_run`. O admin, em Gestão, mostra o que foi enviado, o que falhou, o que falta, os conflitos e o erro de cada execução. `uploaded` significa apenas que o MinIO recebeu o objeto.

## Container

O serviço usa a imagem do OPAC e o comando `python -m log_shipper run`. Não atende HTTP. O cliente não apaga o arquivo de origem. A cópia na área de pendências sai só depois do recebimento confirmado. Volumes, endpoint e credenciais estão na seção de configuração de cada ambiente.

## Comandos

No diretório `/app/opac`:

```bash
python -m log_shipper once
python -m log_shipper status
python -m log_shipper check
python -m log_shipper send 2026/Apr/arquivo-2026-04-22.log.gz
```

`once` envia o histórico que já está fechado, com o nome e o caminho originais. `check` confere no MinIO configurado cada registro `uploaded` (presença, tamanho e MD5) e não altera esses registros. `send` envia um único arquivo. O log aberto e os temporários continuam recusados.

## Configuração

O endereço do MinIO não tem valor padrão no código. O container de envio usa `OPAC_LOG_SHIPPER_ENDPOINT` para o `PUT`. O `opac_webapp` usa o mesmo nome de variável para montar o link do admin. Quando o navegador não alcança o endpoint interno, `OPAC_LOG_SHIPPER_PUBLIC_BASE_URL` é o endereço do link. A linha no `opac.sqlite` guarda a chave, não o host.

| Variável | Função |
|---|---|
| `OPAC_LOG_SHIPPER_ENDPOINT` | Host e porta do MinIO. Obrigatório para enviar. |
| `OPAC_LOG_SHIPPER_SECURE` | `true` com TLS, `false` sem TLS. |
| `OPAC_LOG_SHIPPER_PUBLIC_BASE_URL` | Base do link no admin, se for diferente do endpoint. |
| `OPAC_LOG_SHIPPER_ACCESS_KEY` / `OPAC_LOG_SHIPPER_SECRET_KEY` | Credenciais do produtor. |
| `OPAC_LOG_SHIPPER_BUCKET` | Bucket. Padrão `usage-logs`. |
| `OPAC_LOG_SHIPPER_COLLECTION` | Coleção. Padrão `OPAC_COLLECTION` ou `scl`. |
| `OPAC_LOG_SHIPPER_ORIGIN` | Vazio se a coleção só tem OPAC. `opac` ou `classic` quando as duas origens convivem. |
| `OPAC_LOG_SHIPPER_PRODUCER` | Identificador estável do servidor, por exemplo `server-01`. |
| `OPAC_LOG_SHIPPER_SOURCE_DIR` | Diretório dos logs fechados. |
| `OPAC_LOG_SHIPPER_PENDING_DIR` | Cópias ainda não confirmadas. |
| `OPAC_DATABASE_DIR` / `OPAC_DATABASE_FILE` | O mesmo `opac.sqlite` do site. |

### Ambiente local

Arquivo `docker-compose-dev.yml`. O serviço `opac-log-shipper` sobe com a imagem de desenvolvimento e lê estas variáveis, já definidas no compose:

| Variável | Valor |
|---|---|
| `OPAC_LOG_SHIPPER_ENDPOINT` | `minio:9000` |
| `OPAC_LOG_SHIPPER_SECURE` | `false` |
| `OPAC_LOG_SHIPPER_PUBLIC_BASE_URL` | `http://127.0.0.1:9000` |
| `OPAC_LOG_SHIPPER_ACCESS_KEY` | `minio` |
| `OPAC_LOG_SHIPPER_SECRET_KEY` | `minio123` |
| `OPAC_LOG_SHIPPER_BUCKET` | `usage-logs` |
| `OPAC_LOG_SHIPPER_COLLECTION` | `scl` |
| `OPAC_LOG_SHIPPER_PRODUCER` | `server-01` |
| `OPAC_LOG_SHIPPER_SOURCE_DIR` | `/var/log/nginx` |
| `OPAC_LOG_SHIPPER_PENDING_DIR` | `/app/data/log-shipper` |
| `OPAC_LOG_SHIPPER_CREATE_BUCKET` | `true` |
| `OPAC_DATABASE_DIR` | `/app/data` |
| `OPAC_DATABASE_FILE` | `opac.sqlite` |
| `OPAC_LOG_SHIPPER_INTERVAL_SECONDS` | `60` |

O `opac_webapp` de desenvolvimento usa outro endpoint, o que o navegador abre:

| Variável | Valor |
|---|---|
| `OPAC_LOG_SHIPPER_ENDPOINT` | `127.0.0.1:9000` |
| `OPAC_LOG_SHIPPER_SECURE` | `false` |
| `OPAC_LOG_SHIPPER_BUCKET` | `usage-logs` |

Volumes no host:

- `../data_opac_dev/logs` → `/var/log/nginx` (somente leitura). Coloque aqui os `.log.gz` já fechados.
- `.:/app`, com o `opac.sqlite` e as pendências em `/app/data/log-shipper`, no mesmo volume do site

O MinIO local é o serviço `minio` do mesmo compose (portas `9000` e `9001`, usuário `minio`, senha `minio123`). Com `OPAC_LOG_SHIPPER_CREATE_BUCKET=true`, o container cria o bucket `usage-logs` se ele ainda não existir. O console fica em `http://127.0.0.1:9001`.

Fora do Docker, `start_dev.sh` exporta as mesmas variáveis apontando o endpoint para `127.0.0.1:9000`. O envio é outro processo, no diretório `opac`:

```bash
python -m log_shipper run
```

```bash
docker compose -f docker-compose-dev.yml up -d opac-log-shipper
docker compose -f docker-compose-dev.yml exec opac-log-shipper python -m log_shipper status
```

### Produção

Arquivo `docker-compose.yml`, serviço `opac-log-shipper`. A configuração fica em `.envs/.production/.log-shipper`, lido pelo container de envio e pelo `opac_webapp`. O banco continua em `.envs/.production/.db-sqlite`.

```bash
cp .envs/.production-template/.log-shipper .envs/.production/.log-shipper
cp .envs/.production-template/.db-sqlite .envs/.production/.db-sqlite
```

Preencha no `.log-shipper` o endpoint real, o TLS, as credenciais e o produtor. Exemplo:

```bash
OPAC_LOG_SHIPPER_ENDPOINT=minio.scielo.br
OPAC_LOG_SHIPPER_SECURE=true
OPAC_LOG_SHIPPER_PUBLIC_BASE_URL=https://minio.scielo.br
OPAC_LOG_SHIPPER_ACCESS_KEY=
OPAC_LOG_SHIPPER_SECRET_KEY=
OPAC_LOG_SHIPPER_BUCKET=usage-logs
OPAC_LOG_SHIPPER_CREATE_BUCKET=false
OPAC_LOG_SHIPPER_COLLECTION=scl
OPAC_LOG_SHIPPER_ORIGIN=
OPAC_LOG_SHIPPER_PRODUCER=server-01
OPAC_LOG_SHIPPER_SOURCE_DIR=/var/log/nginx
OPAC_LOG_SHIPPER_PENDING_DIR=/var/lib/opac-log-shipper
OPAC_LOG_SHIPPER_INTERVAL_SECONDS=300
```

Volumes no host:

- `./nginx/logs` → `/var/log/nginx` (somente leitura), o diretório real dos logs do Nginx
- `../data_opac_prod` → `/app/data`, o mesmo volume do `opac.sqlite`
- `../data_opac_prod/log-shipper` → `/var/lib/opac-log-shipper`

Esse diretório de pendências precisa ser gravável pelo usuário `nobody` e ficar fora do logrotate. As credenciais só podem operar no prefixo do produtor: `s3:ListBucket`, `s3:GetObject`, `s3:HeadObject` e `s3:PutObject`. Sem `DeleteObject`.

```bash
docker compose up -d opac-log-shipper
docker compose exec opac-log-shipper python -m log_shipper status
```

## Chave e tradutor no Usage

Bucket padrão: `usage-logs`.

| Prefixo | Fonte | Tradutor no Usage |
|---|---|---|
| `scl/server-01/` | OPAC SciELO Brasil, produtor `server-01` | o mesmo já usado para o access log dessa coleção |
| `wid/opac/server-01/` | OPAC West Indies | o tradutor já usado para o OPAC dessa coleção |
| `wid/classic/server-01/` | site clássico (evolução futura) | o tradutor já usado para o site clássico |

`OPAC_LOG_SHIPPER_ORIGIN` fica vazio quando a coleção só tem OPAC. Preencha `opac` ou `classic` quando as duas origens convivem. O produtor (`OPAC_LOG_SHIPPER_PRODUCER`) é estável entre reinícios e deploys; não use o hostname.

O formato das linhas permanece o que o servidor já grava. Referências: [Log File Naming Conventions](https://github.com/scieloorg/usage/wiki/Log-File-Naming-Conventions) e [Log-Format](https://github.com/scieloorg/usage/wiki/Log-Format). Não há tradutor novo.
