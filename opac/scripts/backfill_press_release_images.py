#!/usr/bin/env python
"""Fill missing PressRelease.image_url values from the WordPress REST API."""

import argparse
import os
import re
from urllib.parse import urlencode

import requests
from pymongo import MongoClient, UpdateOne


POST_ID_RE = re.compile(r"[?&]p=(\d+)")
MISSING_IMAGE = {
    "$or": [
        {"image_url": {"$exists": False}},
        {"image_url": None},
        {"image_url": ""},
    ]
}
WORDPRESS_APIS = {
    "default": "https://pressreleases.scielo.org/wp-json/wp/v2/posts",
    "en": "https://pressreleases.scielo.org/en/wp-json/wp/v2/posts",
}


def chunks(items, size=100):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def wordpress_site(url):
    return "en" if "/en/" in (url or "") else "default"


def image_url(post):
    embedded_media = post.get("_embedded", {}).get("wp:featuredmedia", [])
    if not embedded_media:
        return None

    media = embedded_media[0]
    # source_url is the original featured image and therefore the best
    # quality made available by WordPress for this media item.
    if media.get("source_url"):
        return media["source_url"]

    sizes = media.get("media_details", {}).get("sizes", {})
    for preferred_size in ("large", "medium_large", "medium"):
        if sizes.get(preferred_size, {}).get("source_url"):
            return sizes[preferred_size]["source_url"]
    return None


def fetch_images(session, site, post_ids):
    images = {}
    for post_id_chunk in chunks(sorted(post_ids)):
        query = urlencode(
            {
                "include": ",".join(str(post_id) for post_id in post_id_chunk),
                "per_page": len(post_id_chunk),
                "_embed": "wp:featuredmedia",
                "_fields": "id,_links,_embedded",
            }
        )
        response = session.get(f"{WORDPRESS_APIS[site]}?{query}", timeout=60)
        response.raise_for_status()
        for post in response.json():
            url = image_url(post)
            if url:
                images[post["id"]] = url
    return images


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Update MongoDB. Without this option the script is read-only.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-evaluate records that already have an image URL.",
    )
    args = parser.parse_args()

    mongo_host = os.environ.get("OPAC_MONGODB_HOST", "localhost")
    mongo_port = int(os.environ.get("OPAC_MONGODB_PORT", "27017"))
    mongo_name = os.environ.get("OPAC_MONGODB_NAME", "opac")
    collection = MongoClient(mongo_host, mongo_port)[mongo_name].pressrelease

    record_filter = {} if args.refresh else MISSING_IMAGE
    records = list(collection.find(record_filter, {"url": 1, "title": 1}))
    records_by_site_and_post = {site: {} for site in WORDPRESS_APIS}
    without_post_id = []

    for record in records:
        match = POST_ID_RE.search(record.get("url") or "")
        if not match:
            without_post_id.append(record)
            continue
        site = wordpress_site(record.get("url"))
        records_by_site_and_post[site].setdefault(int(match.group(1)), []).append(record)

    session = requests.Session()
    session.headers["User-Agent"] = "SciELO-OPAC/press-release-image-backfill"
    images = {}
    for site, records_by_post in records_by_site_and_post.items():
        for post_id, url in fetch_images(session, site, records_by_post).items():
            images[(site, post_id)] = url

    updates = []
    matched_documents = 0
    for site, records_by_post in records_by_site_and_post.items():
        for post_id, post_records in records_by_post.items():
            url = images.get((site, post_id))
            if not url:
                continue
            for record in post_records:
                matched_documents += 1
                update_filter = {"_id": record["_id"]}
                if not args.refresh:
                    update_filter.update(MISSING_IMAGE)
                updates.append(
                    UpdateOne(update_filter, {"$set": {"image_url": url}})
                )

    modified = 0
    if args.apply and updates:
        result = collection.bulk_write(updates, ordered=False)
        modified = result.modified_count

    print(f"missing_image={len(records)}")
    print(f"matched_image={matched_documents}")
    print(f"without_post_id={len(without_post_id)}")
    print(f"unmatched_image={len(records) - matched_documents}")
    print(f"modified={modified}")
    print(f"refresh={args.refresh}")
    print(f"mode={'apply' if args.apply else 'dry-run'}")


if __name__ == "__main__":
    main()
