# This makefile has been created to help developers perform common actions.
# Most actions assume it is operating in a virtual environment where the
# python command links to the appropriate virtual environment Python.

MAKEFLAGS += --no-print-directory

# Variables
REPO_SLUG = infrascielo
PROJECT_NAME = opac_5

# Envs: 
export OPAC_WEBAPP_VERSION=$(strip $(shell cat VERSION))
export OPAC_BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
export COMMIT=$(strip $(shell git rev-parse --short HEAD))

# This check if docker compose version
ifneq ($(shell docker compose version 2>/dev/null),)
  DOCKER_COMPOSE=docker compose
else
  DOCKER_COMPOSE=docker-compose
endif

COMPOSE_FILES := docker-compose.yml docker-compose-dev.yml

ifeq ($(filter $(COMPOSE_FILES),$(compose)),)
  @echo "Arquivo docker-compose inválido:" $(compose)
else
  DOCKER_COMPOSE_FILE := $(compose) 
endif

ifeq ($(compose),docker-compose.yml)
  DATA_PATH = data_opac_prod
else
  DATA_PATH = data_opac_dev
endif

# Do not remove this block. It is used by the 'help' rule when
# constructing the help output.
# help:
# help: Make SciELO Site (OPAC)
# help:

# help: help                           - display this makefile's help information
.PHONY: help
help:
	@grep "^# help\:" Makefile | grep -v grep | sed 's/\# help\: //' | sed 's/\# help\://'

# help: opac_version                   - OPAC version.
opac_version:
	@echo "Version file: " $(OPAC_WEBAPP_VERSION)

# help: venv                           - create a virtual environment for development
.PHONY: venv
venv:
	@rm -Rf venv
	@python3 -m venv venv --prompt opac
	@/bin/bash -c "source venv/bin/activate && pip install pip --upgrade && pip install -r requirements.dev.txt && pip install -r requirements.txt"
	@echo "Enter virtual environment using:\n\n\t$ source venv/bin/activate\n"

# help: clean                          - clean all files using .gitignore rules
.PHONY: clean
clean:
	@git clean -X -f -d 

# help: scrub                          - clean all files, even untracked files
.PHONY: scrub
scrub:
	git clean -x -f -d


##################
## python format #
##################

# help: format                         - perform code style format
.PHONY: format
format:
	@black opac 


# help: check-format                   - check code format compliance
.PHONY: check-format
check-format:
	@black --check opac 


# help: sort-imports                   - apply import sort ordering
.PHONY: sort-imports
sort-imports:
	@isort . --profile black


#########
## i18n #
#########

# IMPORTANTE: Seguir os seguintes passos para atualização dos .pot e po:
#
# 1. make make_message (Varre todos os arquivo [.html, .py, .txt, ...] buscando por tags de tradução)
# 2. make update_catalog (Atualizar todos os com .po a apartir do .pot)
# 3. acessar a ferramenta de tradução colaborativa Transifex(https://www.transifex.com) atualizar o arquivo .pot
# 4. utilizando a interface do Transifex é possível realizar as traduções
# 5. após finalizar as traduções realize o download manual dos arquivo traduzidos para suas correspondentes pasta ```opac/webapp/translations/{LANG}/LC_MESSAGES```
# 6. make compile_messages para gerar os arquivo .mo
# 7. realize a atualização no repositório de códigos.

# help: make_messages                  - Faz um scan em toda a opac/webapp buscando strings traduzíveis e o resultado fica em opac/webapp/translations/messages.pot
.PHONY: make_messages
make_messages:
	pybabel extract -F opac/webapp/config/babel.cfg -k lazy_gettext -k __ -o opac/webapp/translations/messages.pot .

# help: create_catalog                 - cria o catalogo para o idioma definido pela variável LANG, a partir das strings: opac/webapp/translations/messages.pot executar: $LANG=en make create_catalog
.PHONY: create_catalog
create_catalog:
	pybabel init -i opac/webapp/translations/messages.pot -d opac/webapp/translations -l $(LANG)

# help: update_catalog                 - atualiza os catalogos, a partir das strings: opac/webapp/translations/messages.pot
.PHONY: update_catalog
update_catalog:
	pybabel update -i opac/webapp/translations/messages.pot -d opac/webapp/translations

#help: compile_messages                - compila as traduções dos .po em arquivos .mo prontos para serem utilizados.
.PHONY: compile_messages
compile_messages:
	pybabel compile -d opac/webapp/translations

#build_i18n 
.PHONY: build_i18n
build_i18n:
	@make make_messages && make update_catalog && make compile_messages


#########
## test #
#########


# help: test                           - run local tests
.PHONY: test
test: make_messages compile_messages build_i18n
	export OPAC_CONFIG="config/templates/testing.template" && flask --app opac.app test

# help: coverage                       - perform test coverage checks
.PHONY: coverage
coverage:
	export OPAC_CONFIG="config/templates/testing.template" && export FLASK_COVERAGE="1" && flask --app opac/app.py test

##########
# cache  #
##########

# help: invalidate_cache               - invalidate cache
.PHONY: invalidate_cache
invalidate_cache:
	flask --app opac/app.py invalidate_cache

# help: invalidate_cache_forced        - invalidate cache forced
.PHONY: invalidate_cache_forced
invalidate_cache_forced:
	flask --app opac/app.py invalidate_cache --force_clear true

#################
## static files #
#################

# help: clean_js_bundles               - clean the scielo-article-standalone.js and scielo-bundle.js
.PHONY: clean_js_bundles
clean_js_bundles:
	@rm -f ./opac/webapp/static/js/scielo-article-standalone.js \
	      ./opac/webapp/static/js/scielo-bundle.js
	@echo 'arquivo JS removidos com sucesso!'

# help: clean_all_bundles              - clean all JS and CSSs
.PHONY: clean_all_bundles
clean_all_bundles: clean_js_bundles
	@echo 'arquivo JS e CSS removidos com sucesso!'

# help: check_js_deps                  - check all dependence of Javascript (NodeJS, NPM andGulp)
.PHONY: check_js_deps
check_js_deps:
	@echo 'NodeJs version:' $(shell node -v)
	@echo 'npm version:' $(shell npm -v)
	@echo 'Gulp.js version:' $(shell gulp -v)

# help: install_npm_deps               - install npm dependece from package.json
.PHONY: install_npm_deps
install_npm_deps:
	@echo 'instalando as dependência (package.json):'
	@npm install

# help: build_bundles                  - construct all static files
.PHONY: build_bundles
build_bundles:
	@echo 'Generating CSS and JS files'
	@gulp



#################
## docker       #
#################

# help: build                          - build the containers
.PHONY: build
build:
	$(DOCKER_COMPOSE) -f $(compose) build

# help: up           	               - start the containers
.PHONY: up
up:
	$(DOCKER_COMPOSE) -f $(compose) up -d

# help: logs           	               - show the containers logs
.PHONY: logs
logs:
	$(DOCKER_COMPOSE) -f $(compose) logs -f 

# help: logs_tail           	       - show the containers logs 50 latest lines
.PHONY: logs_tail
logs_tail:
	$(DOCKER_COMPOSE) -f $(compose) logs -f --tail=50

# help: stop           	               - stop the containers
.PHONY: stop
stop:
	$(DOCKER_COMPOSE) -f $(compose) stop

# help: ps           	               - show the containers Process Status
.PHONY: ps
ps:
	$(DOCKER_COMPOSE) -f $(compose) ps

# help: rm           	               - remove all containers from $(compose)
.PHONY: rm
rm:
	$(DOCKER_COMPOSE) -f $(compose) rm -f

# help: pull_webapp           	       - pull opac_webapp image from $(compose)
.PHONY: pull_webapp
pull_webapp:
	@echo "Pulling OPAC_5 version $(SCMS_WEBAPP_VERSION) ..."
	$(DOCKER_COMPOSE) -f $(compose) pull opac_webapp

# help: down_webapp           	       - down opac_webapp, scheduler and worker containers
.PHONY: down_webapp
down_webapp:
	$(DOCKER_COMPOSE) -f $(compose) rm -s -f opac_webapp opac-rq-scheduler opac-rq-worker-1

# help: shell                          - open a shell from containers
.PHONY: shell
shell: up
	$(DOCKER_COMPOSE) -f $(compose) exec opac_webapp sh

# help: docker_test           	       - run the tests from containers
.PHONY: docker_test
docker_test: up
	$(DOCKER_COMPOSE) -f $(compose) exec opac_webapp make test

# help: mongodb_backup                 - run mongo_dump to backup mongo database 
.PHONY: mongodb_backup
mongodb_backup: up
	$(DOCKER_COMPOSE) -f $(compose) exec opac_mongo mongodump --db opac --out ../$(DATA_PATH)/backups/`date +"%Y-%m-%d"`

# help: restore - Restaura o banco MongoDB e o SQLite
.PHONY: restore
restore: up
	@echo "♻️  Restaurando MongoDB e SQLite..."
	@BACKUP_DATE=$(RESTORE_DATE); \
	if [ -z "$$BACKUP_DATE" ]; then \
		echo "❌ Variável RESTORE_DATE não definida. Use: make restore RESTORE_DATE=YYYY-MM-DD"; \
		exit 1; \
	fi; \
	echo "📦 Restaurando MongoDB de $$BACKUP_DATE..."; \
	$(DOCKER_COMPOSE) -f $(compose) exec opac_mongo mongorestore --dir ../$(DATA_PATH)/backups/$$BACKUP_DATE --drop && \
	echo "🗄  Restaurando opac.sqlite..."; \
	if [ ! -f ../$(DATA_PATH)/backups/sqlite/opac.sqlite ]; then \
		echo "❌ Arquivo ../$(DATA_PATH)/backups/sqlite/opac.sqlite não encontrado!"; \
		exit 1; \
	fi; \
	cp ../$(DATA_PATH)/backups/sqlite/opac.sqlite ../$(DATA_PATH)/opac.sqlite && \
	echo "✅ Restauração concluída!"

# help: backup_sqlite - Faz backup do banco SQLite (opac.sqlite)
.PHONY: backup_sqlite
backup_sqlite:
	@BACKUP_DIR=../$(DATA_PATH)/backups/sqlite; \
	mkdir -p $$BACKUP_DIR && \
	cp ../$(DATA_PATH)/opac.sqlite $$BACKUP_DIR/opac.sqlite && \
	echo "✅ Backup do SQLite concluído: $$BACKUP_DIR/opac.sqlite"

# help: backup - Faz backup completo (MongoDB + SQLite)
.PHONY: backup
backup: mongodb_backup backup_sqlite
	@echo "✅ Backup completo (MongoDB + SQLite) finalizado!"


# help: check_perms - run check_perms to folders
.PHONY: check_perms
check_perms:
	@echo "🔍 Verificando permissões dos volumes..."

	@echo "\n🔸 Redis"
	@if [ -d ../data_opac_prod/redis-cache-data-dev ]; then \
		ls -ld ../data_opac_prod/redis-cache-data-dev; \
	else echo "🔴 Diretório inexistente"; fi

	@echo "\n🔸 MongoDB"
	@if [ -d ../data_opac_prod/db ]; then \
		ls -ld ../data_opac_prod/db; \
	else echo "🔴 Diretório inexistente"; fi
	@if [ -d ../data_opac_prod/backups ]; then \
		ls -ld ../data_opac_prod/backups; \
	else echo "🔴 Diretório inexistente"; fi

	@echo "\n🔸 WebApp / Worker / Scheduler"
	@if [ -d ../data_opac_prod ]; then \
		ls -ld ../data_opac_prod; \
	else echo "🔴 Diretório inexistente"; fi
	@if [ -d ../data_opac_prod/img ]; then \
		ls -ld ../data_opac_prod/img; \
	else echo "🔴 Diretório inexistente"; fi

	@echo "\n🔸 MinIO"
	@if [ -d ../data_opac_prod/minio/data ]; then \
		ls -ld ../data_opac_prod/minio/data; \
	else echo "🔴 Diretório inexistente"; fi

	@echo "\n✅ Verificação finalizada. Se houver diretórios em vermelho, execute: make fix_perms"

# help: fix_perms - run fix_perms to folders
.PHONY: fix_perms
fix_perms:
	@echo "🔧 Ajustando permissões usando o usuário atual do host..."
	@sh -c '\
		HOST_UID=$$(id -u); \
		HOST_GID=$$(id -g); \
		echo "👤 Usando UID: $$HOST_UID | GID: $$HOST_GID"; \
		sudo mkdir -p ../data_opac_prod/redis-cache-data-dev && \
		sudo chown -R $$HOST_UID:$$HOST_GID ../data_opac_prod/redis-cache-data-dev && \
		sudo chmod -R 775 ../data_opac_prod/redis-cache-data-dev && \
		sudo mkdir -p ../data_opac_prod/db ../data_opac_prod/backups && \
		sudo chown -R $$HOST_UID:$$HOST_GID ../data_opac_prod/db ../data_opac_prod/backups && \
		sudo chmod -R 775 ../data_opac_prod/db ../data_opac_prod/backups && \
		sudo mkdir -p ../data_opac_prod/img && \
		sudo chown -R $$HOST_UID:$$HOST_GID ../data_opac_prod ../data_opac_prod/img && \
		sudo chmod -R 775 ../data_opac_prod ../data_opac_prod/img && \
		sudo mkdir -p ../data_opac_prod/minio/data && \
		sudo chown -R $$HOST_UID:$$HOST_GID ../data_opac_prod/minio/data && \
		sudo chmod -R 775 ../data_opac_prod/minio/data; \
		echo "✅ Permissões aplicadas com sucesso!" \
	'

#################
##docker release#
#################

# help: release_docker_build           - create a docker release
.PHONY: release_docker_build
release_docker_build:
	@echo "[Building] Release version: " $(OPAC_WEBAPP_VERSION)
	@echo "[Building] Latest commit: " $(COMMIT)
	@echo "[Building] Build date: " $(OPAC_BUILD_DATE)
	@echo "[Building] Image full tag: $(REPO_SLUG):$(COMMIT)"
	@docker build \
	-t $(REPO_SLUG):$(COMMIT) \
	--build-arg OPAC_BUILD_DATE=$(OPAC_BUILD_DATE) \
	--build-arg COMMIT=$(COMMIT) \
	--build-arg OPAC_WEBAPP_VERSION=$(OPAC_WEBAPP_VERSION) .

# help: release_docker_tag             - create a docker release tag
.PHONY: release_docker_tag
release_docker_tag:
	@echo "[Tagging] Target image -> $(REPO_SLUG):$(COMMIT)"
	@echo "[Tagging] Image name:latest -> $(REPO_SLUG):latest"
	@echo "[Tagging] Image name:$(OPAC_WEBAPP_VERSION) -> $(REPO_SLUG)/$(PROJECT_NAME):$(OPAC_WEBAPP_VERSION)"
	@docker tag $(REPO_SLUG):$(COMMIT) $(REPO_SLUG):latest
	@docker tag $(REPO_SLUG):$(COMMIT) $(REPO_SLUG)/$(PROJECT_NAME):$(OPAC_WEBAPP_VERSION)

# help: release_docker_push            - push release version to $(REPO_SLUG)/$(PROJECT_NAME):$(OPAC_WEBAPP_VERSION)
.PHONY: release_docker_push
release_docker_push:
	@echo "[Pushing] pushing image: $(REPO_SLUG)/$(PROJECT_NAME):$(OPAC_WEBAPP_VERSION)"
	@docker push $(REPO_SLUG)/$(PROJECT_NAME):$(OPAC_WEBAPP_VERSION)
	@echo "[Pushing] push $(REPO_SLUG)/$(PROJECT_NAME):$(OPAC_WEBAPP_VERSION) done!"


#################
##image update##
#################

exclude_opac_production:  ## Exclude all production images
	@if [ -n "$$(docker images --filter=reference='infrascielo/opac_5' -q)" ]; then \
		echo "Deleting containers $$(docker images --filter=reference='infrascielo/opac_5' -q --format '{{.Repository}}:{{.Tag}}')"; \
		docker rmi -f $$(docker images --filter=reference='infrascielo/opac_5' -q); \
	else \
		echo "No images found for 'infrascielo/opac_5'"; \
	fi

# help: update                         - stop, remove old images, and start the containers
.PHONY: update
update: backup stop exclude_opac_production up

update_webapp: pull_webapp down_webapp up
