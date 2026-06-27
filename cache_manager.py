import os
import shutil
import uuid


class CacheManager:

    CACHE_DIR = "cache"

    SUBDIRS = {
        "image": "images",
        "text": "documents",
        "other": "other"
    }

    @classmethod
    def init(cls):
        os.makedirs(cls.CACHE_DIR, exist_ok=True)

        for folder in cls.SUBDIRS.values():
            os.makedirs(
                os.path.join(cls.CACHE_DIR, folder),
                exist_ok=True
            )

    @classmethod
    def cache_file(cls, source_path):

        ext = os.path.splitext(source_path)[1].lower()

        if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}:
            category = "image"

        elif ext in {
            ".py", ".txt", ".md", ".json",
            ".xml", ".yaml", ".yml",
            ".cpp", ".c", ".h",
            ".cs", ".java",
            ".ini", ".cfg"
        }:
            category = "text"

        else:
            category = "other"

        uid = uuid.uuid4().hex[:8]

        filename = f"{uid}_{os.path.basename(source_path)}"

        target = os.path.join(
            cls.CACHE_DIR,
            cls.SUBDIRS[category],
            filename
        )

        shutil.copy2(source_path, target)

        return target