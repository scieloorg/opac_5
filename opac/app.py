import os
import sys
import unittest

import click
from flask import Flask

HERE = os.path.dirname(os.path.abspath(__file__))
WEBAPP_PATH = os.path.abspath(os.path.join(HERE, "webapp"))
sys.path.insert(0, HERE)
sys.path.insert(1, WEBAPP_PATH)

FLASK_COVERAGE = os.environ.get("FLASK_COVERAGE", None)

if FLASK_COVERAGE:
    try:
        import coverage
    except ImportError:
        msg = "Não é possível importar o modulo coverage"
        raise RuntimeError(msg)
    COV = None
    if FLASK_COVERAGE:
        COV = coverage.coverage(branch=True, include="opac/webapp/*")
        COV.start()
else:
    COV = None

from opac_schema.v1.models import Collection  # noqa
from opac_schema.v1.models import Article, AuditLogEntry, Issue, Journal, Sponsor
from webapp import controllers  # noqa
from webapp import cache, create_app, dbmongo, dbsql, mail  # noqa
from webapp.admin.forms import EmailForm
from webapp.tasks import clear_scheduler, setup_scheduler  # noqa
from webapp.utils import create_new_journal_page  # noqa
from webapp.utils import (
    create_db_tables,
    create_user,
    reset_db,
    send_audit_log_daily_report,
)
from webapp.utils.journal_static_page import PAGE_NAMES_BY_LANG  # noqa

app = Flask(__name__)
app = create_app()


@app.route('/')
def root():
    """
    Redireciona raiz para idioma do navegador ou padrão.
    """
    from flask import request, redirect, url_for, current_app

    langs = current_app.config.get("LANGUAGES", {})
    browser_lang = request.accept_languages.best_match(list(langs.keys()))
    lang = browser_lang if browser_lang else 'pt'

    return redirect(url_for('main.index', ilang=lang))


@app.shell_context_processor
def make_shell_context():
    app_models = {
        "Collection": Collection,
        "Sponsor": Sponsor,
        "Journal": Journal,
        "Issue": Issue,
        "Article": Article,
        "AuditLogEntry": AuditLogEntry,
    }
    return dict(
        app=app,
        dbsql=dbsql,
        dbmongo=dbmongo,
        mail=mail,
        cache=cache,
        controllers=controllers,
        **app_models
    )


@app.cli.command("invalidate_cache")
@click.option("-f", "--force_clear", default=False)
def invalidate_cache(force_clear=False):
    def clear_cache():
        keys_invalidated = cache.clear()
        print("Chaves invalidadas: %s" % keys_invalidated)
        print("Cache zerado com sucesso!")

    if force_clear:
        clear_cache()
    else:
        # pedimos confirmação
        user_confirmation = None
        while user_confirmation is None:
            user_confirmation = input(
                "Tem certeza que deseja limpar todo o cache? [y/N]: "
            ).strip()
            if user_confirmation.lower() == "y":
                clear_cache()
            elif user_confirmation.lower() == "n":
                print("O cache permance sem mudanças!")
            else:
                user_confirmation = None
                print('Resposta inválida. Responda "y" ou "n" (sem aspas)')


@app.cli.command("reset_dbsql")
@click.option("-f", "--force_delete", default=False)
def reset_dbsql(force_delete=False):
    """
    Remove todos os dados do banco de dados SQL.
    Por padrão: se o banco SQL já existe, o banco não sera modificado.
    Utilize o parametro --force=True para forçar a remoção dos dados.

    Uma vez removidos os dados, todas as tabelas serão criadas vazias.
    """
    db_path = app.config["DATABASE_PATH"]
    print(app.config["DATABASE_PATH"])
    if not os.path.exists(db_path) or force_delete:
        reset_db()
        print("O banco esta limpo!")
        print("Para criar um novo usuário execute o comando: create_superuser")
        print("flask --app opac.app create_superuser")
    else:
        print("O banco já existe (em %s)." % db_path)
        print("remova este arquivo manualmente ou utilize --force.")


@app.cli.command("create_tables_dbsql")
@click.option("-f", "--force_delete", "--force_delete", default=False)
def create_tables_dbsql(force_delete=False):
    """Cria as tabelas necessárias no banco de dados SQL."""

    db_path = app.config["DATABASE_PATH"]
    if not os.path.exists(db_path):
        create_db_tables()
        print("As tabelas foram criadas com sucesso!")
    else:
        print("O banco já existe (em %s)." % db_path)
        print("Para remover e crias as tabelas use o camando:")
        print("flask --app opac.app reset_dbsql --help")


@app.cli.command("create_superuser")
def create_superuser():
    """
    Cria um novo usuário a partir dos dados inseridos na linha de comandos.
    Para criar um novo usuário é necessario preencher:
    - email (deve ser válido é único, se já existe outro usuário com esse email deve inserir outro);
    - senha (modo echo off)
    - e se o usuário tem email confirmado (caso sim, pode fazer logim, caso que não, deve verificar por email)
    """
    user_email = None
    user_password = None

    while user_email is None:
        user_email = input("Email: ").strip()
        if user_email == "":
            user_email = None
            print("Email não pode ser vazio")
        else:
            form = EmailForm(data={"email": user_email})
            if not form.validate():
                user_email = None
                print("Deve inserir um email válido!")
            elif controllers.get_user_by_email(user_email):
                user_email = None
                print("Já existe outro usuário com esse email!")

    os.system("stty -echo")
    while user_password is None:
        user_password = input("Senha: ").strip()
        if user_password == "":
            user_password = None
            print("Senha não pode ser vazio")
    os.system("stty echo")

    email_confirmed = input("\nEmail confirmado? [y/N]: ").strip()
    if email_confirmed.upper() in ("Y", "YES"):
        email_confirmed = True
    else:
        email_confirmed = False
        print("Deve enviar o email de confirmação pelo admin")

    # cria usuario
    create_user(user_email, user_password, email_confirmed)
    print("Novo usuário criado com sucesso!")


@app.cli.command("test")
@click.option("-p", "--pattern", default=None)
@click.option("-f", "--failfast", default=False)
def test(pattern=None, failfast=False):
    """Executa tests unitarios.
    Lembre de definir a variável: OPAC_CONFIG="path do arquivo de conf para testing"
    antes de executar este comando:
    > export OPAC_CONFIG="/foo/bar/config.testing" && flask --app opac.app test --failfast=true

    Utilize -p para rodar testes específicos'

    ex.: export OPAC_CONFIG="config/templates/testing.template" && flask --app opac.app test
         export OPAC_CONFIG="config/templates/testing.template" && flask --app opac.app test -p "test_main_views"
         export OPAC_CONFIG="config/templates/testing.template" && flask --app opac.app test -f
    """
    failfast = True if failfast else False

    if COV and not FLASK_COVERAGE:
        os.environ["FLASK_COVERAGE"] = "1"
        os.execvp(sys.executable, [sys.executable] + sys.argv)

    if pattern is None:
        tests = unittest.TestLoader().discover("tests")
    else:
        tests = unittest.TestLoader().loadTestsFromName("tests." + pattern)

    result = unittest.TextTestRunner(verbosity=2, failfast=failfast).run(tests)

    if COV:
        COV.stop()
        COV.save()
        print("Coverage Summary:")
        COV.report()
        # basedir = os.path.abspath(os.path.dirname(__file__))
        # covdir = 'tmp/coverage'
        # COV.html_report(directory=covdir)
        # print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

    if result.wasSuccessful():
        return sys.exit()
    else:
        return sys.exit(1)


@app.cli.command("setup_scheduler_tasks")
@click.option("-c", "--cron_string")
def setup_scheduler_tasks(cron_string=None):
    cron_string = cron_string or app.config["MAILING_CRON_STRING"]
    if not cron_string:
        print(
            "Valor de cron nulo para o scheduler. Definit cron pelo parâmetro ou pela var env."
        )
        return sys.exit(1)
    queue_name = "mailing"
    clear_scheduler(queue_name)
    setup_scheduler(send_audit_log_daily_report, queue_name, cron_string)


@app.cli.command("clear_scheduler_tasks")
def clear_scheduler_tasks():
    clear_scheduler(queue_name="mailing")


@app.cli.command("send_audit_log_emails")
def send_audit_log_emails():
    print("coletando registros de auditoria modificados hoje!")
    print(
        "envio de notificações habilitado? (AUDIT_LOG_NOTIFICATION_ENABLED): ",
        app.config["AUDIT_LOG_NOTIFICATION_ENABLED"],
    )
    print(
        "lista recipients (além dos usuários) AUDIT_LOG_NOTIFICATION_RECIPIENTS: ",
        app.config["AUDIT_LOG_NOTIFICATION_RECIPIENTS"],
    )
    send_audit_log_daily_report()


@app.cli.command("create_empty_sqlite")
def create_empty_sqlite_db():
    """
    Cria um banco de dados SQLite vazio com todas as tabelas definidas.
    Essa operação remove todas as tabelas existentes.
    """

    app = create_app()
    db_path = app.config["DATABASE_PATH"]

    print(f"⚠️  Isso irá remover TODAS as tabelas existentes no banco: {db_path}")
    confirm = input("Tem certeza que deseja continuar? [y/N]: ").strip().lower()

    if confirm not in ("y", "yes"):
        print("❌ Operação cancelada pelo usuário.")
        return

    with app.app_context():
        print(f"🛠 Criando banco vazio em: {db_path}")
        dbsql.drop_all()
        dbsql.create_all()
        print("✅ Banco SQLite criado com sucesso!")


app.cli.add_command(test)
app.cli.add_command(create_tables_dbsql)
app.cli.add_command(create_superuser)
app.cli.add_command(reset_dbsql)
app.cli.add_command(clear_scheduler_tasks)
app.cli.add_command(send_audit_log_emails)
app.cli.add_command(create_empty_sqlite_db)

if __name__ == "__main__":
    print(app.config["SERVER_NAME"])
    app.run()
