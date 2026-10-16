# coding: utf-8
import argparse
import logging
import sys
import time

from log_shipper.config import ConfigError, load_config
from log_shipper.shipper import Shipper
from log_shipper.storage import MinioStorage
from log_shipper.store import Store

logger = logging.getLogger("log_shipper")


def build_parser():
    parser = argparse.ArgumentParser(prog="log_shipper")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("run", help="ciclo contínuo de envio")
    sub.add_parser("once", help="uma passagem, inclusive histórico")
    sub.add_parser("status", help="pendentes, último envio e erros")
    sub.add_parser("check", help="confere no MinIO os registros enviados")
    send = sub.add_parser("send", help="envia um único log")
    send.add_argument("path", help="caminho do arquivo dentro do diretório de origem")
    return parser


def _store(config):
    return Store(config.database_path)


def _shipper(config):
    return Shipper(config, _store(config), MinioStorage(config))


def print_status(store):
    counts = store.counts()
    pending = counts["pending"] + counts["failed"]
    print("pendentes: %s" % pending)
    print("falhas: %s" % counts["failed"])
    print("conflitos: %s" % counts["conflict"])
    print("enviados: %s" % counts["uploaded"])
    print("ultimo_envio: %s" % (store.last_uploaded_at() or "-"))
    latest = store.latest_run()
    if latest and latest["error_message"]:
        print("ultimo_erro:")
        print(latest["error_message"])
    else:
        print("ultimo_erro: -")
    return 0


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    try:
        if args.command == "status":
            config = load_config(require_endpoint=False, require_source=False)
            return print_status(_store(config))
        if args.command == "check":
            config = load_config(require_endpoint=True, require_source=False)
            result = _shipper(config).check()
            print(
                "conferidos: %s ausentes: %s divergentes: %s"
                % (len(result["ok"]), len(result["missing"]), len(result["mismatch"]))
            )
            return 0 if result["status"] == "success" else 1
        config = load_config(require_endpoint=True, require_source=True)
        shipper = _shipper(config)
        if args.command == "run":
            while True:
                try:
                    shipper.run_once()
                except Exception:
                    logger.exception("ciclo de envio falhou")
                time.sleep(config.interval_seconds)
        if args.command == "once":
            result = shipper.run_once()
            return 0 if result["status"] == "success" else 1
        if args.command == "send":
            result = shipper.send_file(args.path)
            return 0 if result["status"] == "success" else 1
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        logger.exception("erro de execução")
        print(str(exc), file=sys.stderr)
        return 1
    return 2
