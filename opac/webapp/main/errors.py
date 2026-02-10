# coding: utf-8
from flask import current_app, jsonify, redirect, render_template, request
import re
from . import main
from .helper import build_classic_website_uri
from webapp import controllers


@main.app_errorhandler(400)
def bad_request(e):
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        response = jsonify({"error": e.get_description()})
        response.status_code = 400
        return response
    context = {"message": e.get_description()}
    return render_template("errors/400.html", **context), 400


@main.app_errorhandler(403)
def forbidden(e):
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        response = jsonify({"error": e.get_description()})
        response.status_code = 403
        return response
    context = {"message": e.get_description()}
    return render_template("errors/403.html", **context), 403


@main.app_errorhandler(404)
def page_not_found(e):
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        response = jsonify({"error": e})
        response.status_code = 404
        return response
    
    # Try to redirect to the classic site if configured
    classic_site_url = current_app.config.get("PREVIOUS_WEBSITE_URI", "")
    if classic_site_url:
        # Try to build a specific classic URL based on the resource type
        classic_url = _build_classic_url_for_resource(request.path)
        
        # If we couldn't build a specific URL, fallback to the simple redirect
        if not classic_url:
            classic_url = classic_site_url.rstrip("/") + request.full_path.rstrip("?")
        
        return redirect(classic_url, code=302)
    
    # If no classic site is configured, show the 404 page
    context = {"message": e}
    return render_template("errors/404.html", **context), 404


def _build_classic_url_for_resource(path):
    """
    Tenta construir uma URL específica para o site clássico com base no tipo de recurso.
    
    Args:
        path: o caminho da requisição
    
    Returns:
        String com a URL completa para o site clássico ou None se não puder ser construída
    """
    # Pattern para journal: /j/<url_seg>/
    journal_pattern = r'^/j/([^/]+)/?$'
    match = re.match(journal_pattern, path)
    if match:
        url_seg = match.group(1)
        journal = controllers.get_journal_by_url_seg(url_seg)
        if journal:
            return build_classic_website_uri('journal', journal)
    
    # Pattern para issue: /j/<url_seg>/i/<url_seg_issue>/
    issue_pattern = r'^/j/([^/]+)/i/([^/]+)/?$'
    match = re.match(issue_pattern, path)
    if match:
        url_seg = match.group(1)
        url_seg_issue = match.group(2)
        issue = controllers.get_issue_by_url_seg(url_seg, url_seg_issue)
        if issue:
            return build_classic_website_uri('issue', issue)
    
    # Pattern para article: /j/<url_seg>/a/<article_pid_v3>/ ou /j/<url_seg>/a/<article_pid_v3>/<part>/
    article_pattern = r'^/j/([^/]+)/a/([^/]+)(?:/[^/]+)?/?$'
    match = re.match(article_pattern, path)
    if match:
        url_seg = match.group(1)
        article_pid_v3 = match.group(2)
        # Tenta obter o artigo pelo aid (v3 PID)
        try:
            from opac_schema.v1.models import Article
            article = Article.objects(aid=article_pid_v3).first()
            if article:
                return build_classic_website_uri('article', article)
        except Exception:
            pass
    
    return None


@main.app_errorhandler(500)
def internal_server_error(e):
    if (
        request.accept_mimetypes.accept_json
        and not request.accept_mimetypes.accept_html
    ):
        response = jsonify({"error": "internal server error"})
        response.status_code = 500
        return response
    return render_template("errors/500.html"), 500
