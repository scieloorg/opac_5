# This makefile has been created to help developers perform common actions.
# Most actions assume it is operating in a virtual environment where the
# python command links to the appropriate virtual environment Python.

MAKEFLAGS += --no-print-directory

# Envs: 
export OPAC_WEBAPP_VERSION=$(strip $(shell cat VERSION))

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
	@git clean -X -f -d -n

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

# help: clean_js_bundles           	    - clean the scielo-article-standalone.js and scielo-bundle.js
.PHONY: clean_js_bundles
clean_js_bundles:
	@rm -f ./opac/webapp/static/js/scielo-article-standalone.js \
	      ./opac/webapp/static/js/scielo-bundle.js
	@echo 'arquivo JS removidos com sucesso!'

# help: clean_all_bundles           	    - clean all JS and CSSs
.PHONY: clean_all_bundles
clean_all_bundles: clean_js_bundles
	@echo 'arquivo JS e CSS removidos com sucesso!'

# help: check_js_deps           	    - check all dependence of Javascript (NodeJS, NPM andGulp)
.PHONY: check_js_deps
check_js_deps:
	@echo 'NodeJs version:' $(shell node -v)
	@echo 'npm version:' $(shell npm -v)
	@echo 'Gulp.js version:' $(shell gulp -v)

# help: install_npm_deps           	    - install npm dependece from package.json
.PHONY: install_npm_deps
install_npm_deps:
	@echo 'instalando as dependência (package.json):'
	@npm install

# help: build_bundles           	    - construct all static files
.PHONY: build_bundles
build_bundles:
	@echo 'Generating CSS and JS files'
	@gulp