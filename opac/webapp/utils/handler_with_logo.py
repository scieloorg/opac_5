import logging
import os
from urllib.parse import urlparse

import requests
from flask import current_app


def handler_with_logo(logo_url, folder):
    """
        Ex logo_url: https://core.scielo.org/media/original_images/av_glogo.gif
        
    """
    if not logo_url or logo_url == "null":
        return {}

    # Extrai o nome do arquivo com extensão a partir da URL.
    base_name = os.path.basename(urlparse(logo_url).path)
    rel_path = os.path.join(folder, base_name)
    # abs_path /app/opac/webapp/static/img/sponsors/screenshot_from_2024-10-14_11-20-16.png
    abs_path = os.path.join(current_app.static_folder, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    print(os.path.join(current_app.static_url_path, rel_path))
    try:
        resp = requests.get(logo_url, stream=True, timeout=60)
        resp.raise_for_status()

        with open(abs_path, "wb") as f:
            for chuck in resp.iter_content(chunk_size=8192):
                f.write(chuck)
        logging.info(f"File {base_name} downloaded successfully")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading file {base_name}: {e}")
    except OSError as e:
        logging.error(f"Error saving file {base_name}: {e}")

    return {
        'abs_path': abs_path, 
        'rel_path': os.path.join(
            current_app.static_url_path, 
            rel_path
            )
        }