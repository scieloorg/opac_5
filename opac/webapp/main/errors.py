# coding: utf-8
from flask import current_app, jsonify, redirect, render_template, request

from . import main


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
        # Build the classic site URL with the same path and query string
        classic_url = classic_site_url.rstrip("/") + request.full_path.rstrip("?")
        return redirect(classic_url, code=302)
    
    # If no classic site is configured, show the 404 page with migration message
    context = {
        "message": e,
        "classic_site_url": classic_site_url
    }
    return render_template("errors/404.html", **context), 404


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
