# @manager.command
# @manager.option('-d', '--directory', dest="pattern")
# def upload_images(directory='.'):
#     """
#     Esse comando realiza um cadastro em massa de images com extensões contidas
#     na variável: app.config['IMAGES_ALLOWED_EXTENSIONS_RE'] de um diretório
#     determinado pelo parâmetro --directory (utilizar caminho absoluto).
#     """

#     extensions = app.config['IMAGES_ALLOWED_EXTENSIONS_RE']

#     print("Coletando todas a imagens da pasta: %s" % directory)

#     for root, dirnames, filenames in os.walk(directory):
#         for extension in extensions:
#             for filename in fnmatch.filter(filenames, extension):

#                 image_path = os.path.join(root, filename)

#                 create_image(image_path, filename)


# @manager.command
# @manager.option('-d', '--domain', dest="domain")
# @manager.option('-f', '--filename', dest="filename")
# def populate_database(domain="http://127.0.0.1", filename="fixtures/default_info.json"):
#     """
#     Esse comando realiza o cadastro dos metadados de uma coleção a partir de um
#     arquivo JSON, localizado em: fixtures/default_info.json.

#     Por padrão o conteúdo é o da coleção SciELO Brasil.

#     As imagens são coletadas da pasta: fixtures/imgs
#     """

#     data = json.load(open(filename))

#     collection = Collection.objects.first()

#     if collection:
#         collection.name = data['collection']['name']
#         collection.address1 = data['collection']['address1']
#         collection.address2 = data['collection']['address2']

#         print("Cadastrando as imagens da coleção %s" % collection.name)

#         for imgs in data['collection']['images']:

#             for key, val in imgs.items():

#                 img = create_image(val, os.path.basename(val))

#                 setattr(collection, key, '%s%s' % (domain, img.get_absolute_url))

#         print("Cadastrando os financiadores da coleção %s" % collection.name)

#         sponsors = []

#         for _ in data['sponsors']:
#             sponsor = Sponsor()
#             sponsor._id = str(uuid4().hex)
#             sponsor.order = _['order']
#             sponsor.name = _['name']
#             img = create_image(_['logo_path'], os.path.basename(_['logo_path']))
#             sponsor.logo_url = '%s%s' % (domain, img.get_absolute_url)
#             sponsor.url = _['url']
#             sponsor.save()
#             sponsors.append(sponsor)

#         collection.sponsors = sponsors

#         collection.save()

#     else:
#         print("Nenhuma coleção encontrada!")


# @manager.command
# @manager.option('-f', '--filename', dest="filename")
# def populate_pdfs_path_html_version(filename="fixtures/pdfs_path_file_html_version.json"):
#     """
#     Esse comando tem como responsabilidade enriquecer os registros de artigos com o caminho da URL do site anterior para os PDFs.

#     Além do nome dos arquivos em PDF o site precisa dos caminhos dos PDFs para que seja possível resolver URLs como http://www.scielo.br/pdf/aa/v36n2/v36n2a09.pdf

#     O arquivo ``fixtures/pdfs_path_file_html_version.json` é extraído uma única vez, contendo todos os PIDs da versão HTML, caminho dos PDFs e idioma.

#     Estrutura do arquivo: ``pdfs_path_file_html_version.json``:

#     [
#       {
#         "pid": "S0044-59672004000100001",
#         "file_path": "/pdf/aa/v34n1/v34n1a01.pdf",
#         "lang": "pt"
#       },
#     ]

#     """

#     with open(filename) as fp:

#         data_json = json.load(fp)

#     for art_pdf_path in data_json:

#         art = controllers.get_article_by_pid(art_pdf_path['pid'])

#         if art.pdfs:
#             for pdf in art.pdfs:
#                 if art_pdf_path.get('lang', '') == pdf.get('lang'):
#                     pdf['file_path'] = art_pdf_path.get('file_path')

#             art.save()

#             print("PDF do PID: %s atualizado com sucesso, caminho %s" % (art_pdf_path.get('pid'), art_pdf_path.get('file_path')))
#         else:

#             print("PDF do PID: %s não encontrado na base de dados do OPAC." % (art_pdf_path.get('pid')))


# @manager.command
# def populate_journal_pages():
#     """
#     Esse comando faz o primeiro registro das páginas secundárias
#     dos periódicos localizado em /data/pages.
#     Cada vez que executa cria um novo registro.

#     As páginas dos periódico SciELO contém a seguinte estrutura:

#     - eaboutj.htm
#     - einstruc.htm
#     - eedboard.htm
#     - esubscrp.htm (Assinatura)

#     Sendo que o prefixo "e" indica Espanhol, prefixo "i" Inglês e o prefixo "p"
#     português.

#     OBS.: A extensão dos html é htm.

#     Assinatura não esta sendo importada conforme mencionado no tk:
#     https://github.com/scieloorg/opac/issues/630
#     """
#     acron_list = [journal.acronym for journal in Journal.objects.all()]
#     j_total = len(acron_list)
#     done = 0
#     for j, acron in enumerate(sorted(acron_list)):
#         print('{}/{} {}'.format(j+1, j_total, acron))
#         for lang, files in PAGE_NAMES_BY_LANG.items():
#             create_new_journal_page(acron, files, lang)
#             done += 1
#     print('Páginas: {}\nPeriódicos: {}'.format(done, j_total))


# # @manager.command
# # @manager.option('-p', '--pattern', dest='pattern')
# # @manager.option('-f', '--force', dest='force_clear', default=False)
# # def invalidate_cache_pattern(pattern, force_clear=False):
#     _redis_cli = cache.cache._client

#     def count_key_pattern(pattern):
#         keys_found = _redis_cli.scan_iter(match=pattern)
#         return len([k for k in keys_found])

#     def delete_cache_pattern(pattern):
#         print('Removendo do cache as chaves com pattern: %s' % pattern)
#         keys_found = _redis_cli.scan_iter(match=pattern)
#         deleted_keys_count = _redis_cli.delete(*keys_found)
#         print('%s chaves removidas do cache' % deleted_keys_count)

#     if not pattern:
#         print('Não é possível buscar chaves se o pattern é vazio!')
#         print('O cache permance sem mudanças!')
#     else:
#         if force_clear:
#             keys_found_count = count_key_pattern(pattern)
#             if keys_found_count > 0:
#                 delete_cache_pattern(pattern)
#             else:
#                 print('Não foi encontrada nenhuma chave pelo pattern: %s' % pattern)
#         else:
#             # pedimos confirmação
#             user_confirmation = None
#             while user_confirmation is None:
#                 user_confirmation = input('Tem certeza que deseja limpar o cache filtrando pelo pattern: %s? [y/N]: ' % pattern).strip()
#                 if user_confirmation.lower() == 'y':
#                     keys_found_count = count_key_pattern(pattern)
#                     if keys_found_count > 0:
#                         delete_cache_pattern(pattern)
#                     else:
#                         print('Não foi encontrada nenhuma chave pelo pattern: %s' % pattern)
#                 elif user_confirmation.lower() == 'n':
#                     print('O cache permance sem mudanças!')
#                 else:
#                     user_confirmation = None
#                     print('Resposta inválida. Responda "y" ou "n" (sem aspas)')
