import bpy
import os
import time
import requests
import zipfile
import shutil
import platform
from pathlib import Path

bl_info = {
    "name": "ANONIM4IK Asset Updater",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > ANONIM4IK Asset Updater",
    "description": "Downloads/updates the ANONIM4IK asset library from GitHub.",
    "warning": "",
    "wiki_url": "",
    "category": "Development",
}

# --- Настраиваемые параметры ---
ASSET_LIBRARY_NAME = "ANONIM4IK_Assets"   # Имя, под которым библиотека появится в Preferences
ADDON_NAME = "anonim4ik_assets"             # Имя папки, создаваемой в extensions/user_default
# ----------------------------------

# URL-ы для получения данных с GitHub
GITHUB_REPO_URL = "https://api.github.com/repos/ANONIM4IK3327/ANONIM4IK-s-asset-library/commits"
DOWNLOAD_URL = "https://github.com/ANONIM4IK3327/ANONIM4IK-s-asset-library/archive/refs/heads/main.zip"

def get_addon_path():
    r"""
    Возвращает путь к папке активов:
      Windows: C:\Users\<User>\AppData\Roaming\Blender Foundation\Blender\<major.minor>\extensions\user_default\<ADDON_NAME>
      macOS:   ~/Library/Application Support/Blender/<major.minor>/extensions/user_default/<ADDON_NAME>
      Linux:   ~/.config/blender/<major.minor>/extensions/user_default/<ADDON_NAME>
    """
    version_tuple = bpy.app.version  # Например, (3, 6, 2)
    major_minor = f"{version_tuple[0]}.{version_tuple[1]}"  # "3.6"
    system = platform.system()
    if system == "Windows":
        base = os.getenv('APPDATA')
        if not base:
            base = os.path.expanduser("~")
        return os.path.join(
            base,
            "Blender Foundation",
            "Blender",
            major_minor,
            "extensions",
            "user_default",
            ADDON_NAME
        )
    elif system == "Darwin":
        return os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "Blender",
            major_minor,
            "extensions",
            "user_default",
            ADDON_NAME
        )
    else:
        return os.path.join(
            os.path.expanduser("~"),
            ".config",
            "blender",
            major_minor,
            "extensions",
            "user_default",
            ADDON_NAME
        )

ASSETS_PATH = get_addon_path()

def get_last_commit_date():
    """Получает дату последнего коммита с GitHub."""
    try:
        response = requests.get(GITHUB_REPO_URL)
        if response.status_code == 200:
            commits = response.json()
            last_commit_date_str = commits[0]['commit']['committer']['date']
            return time.strptime(last_commit_date_str, "%Y-%m-%dT%H:%M:%SZ")
        else:
            print(f"Не удалось получить данные о коммитах: {response.status_code}")
            return None
    except Exception as e:
        print(f"Ошибка при получении данных о коммитах: {e}")
        return None

def get_folder_modification_date(path):
    """Получает дату последнего изменения указанной папки."""
    try:
        timestamp = os.path.getmtime(path)
        return time.gmtime(timestamp)
    except Exception as e:
        print(f"Ошибка при получении даты изменения папки: {e}")
        return None

def register_asset_library(library_path, library_name=ASSET_LIBRARY_NAME):
    """
    Регистрирует (или обновляет) библиотеку ассетов в настройках Blender:
    Edit → Preferences → File Paths → Asset Libraries
    """
    prefs = bpy.context.preferences
    filepaths = prefs.filepaths
    library = filepaths.asset_libraries.get(library_name)
    if library is None:
        library = filepaths.asset_libraries.new(name=library_name)
    library.path = library_path

    if not bpy.app.background:
        try:
            bpy.ops.wm.save_userpref()
            print(f"[INFO] Библиотека «{library_name}» зарегистрирована и настройки сохранены.")
        except RuntimeError as ex:
            print(f"[WARN] Не удалось сохранить настройки: {ex}")
    else:
        print(f"[INFO] Blender запущен в фоновом режиме: библиотека «{library_name}» добавлена, но настройки не сохранены автоматически.")

def download_and_replace_assets():
    """Скачивает архив с GitHub и устанавливает (или обновляет) ассеты в ASSETS_PATH."""
    try:
        # Создаем родительскую папку для ASSETS_PATH, если её нет
        Path(os.path.dirname(ASSETS_PATH)).mkdir(parents=True, exist_ok=True)

        temp_dir = Path(bpy.app.tempdir) / "anonim4ik-assets-temp"
        zip_path = temp_dir / "assets.zip"
        temp_dir.mkdir(parents=True, exist_ok=True)

        response = requests.get(DOWNLOAD_URL, stream=True)
        if response.status_code == 200:
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            extracted_folders = list(temp_dir.glob("ANONIM4IK-s-asset-library-*"))
            if not extracted_folders:
                print("[ERROR] Распакованная папка не найдена!")
                return
            extracted_folder = extracted_folders[0]

            if os.path.exists(ASSETS_PATH):
                shutil.rmtree(ASSETS_PATH)

            shutil.move(str(extracted_folder), ASSETS_PATH)
            print("[INFO] Активы успешно обновлены!")
            register_asset_library(ASSETS_PATH)
            shutil.rmtree(temp_dir)
        else:
            print(f"[ERROR] Не удалось скачать архив: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Ошибка при скачивании или установке активов: {e}")

class ANONIM4IK_AssetUpdaterPanel(bpy.types.Panel):
    bl_label = "ANONIM4IK Asset Updater"
    bl_idname = "OBJECT_PT_ANONIM4IK_ASSET_UPDATER"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ANONIM4IK'
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("wm.anonim4ik_update_assets", text="Check for Updates")

class ANONIM4IK_UpdateAssetsOperator(bpy.types.Operator):
    bl_idname = "wm.anonim4ik_update_assets"
    bl_label = "Check for Updates"
    
    def execute(self, context):
        if not os.path.exists(ASSETS_PATH):
            self.report({'INFO'}, "Папка ассетов не найдена, скачиваем заново...")
            download_and_replace_assets()
            return {'FINISHED'}

        folder_mod_date = get_folder_modification_date(ASSETS_PATH)
        if not folder_mod_date:
            self.report({'ERROR'}, "Не удалось получить дату изменения папки.")
            return {'CANCELLED'}

        last_commit_date = get_last_commit_date()
        if not last_commit_date:
            self.report({'ERROR'}, "Не удалось получить дату последнего коммита.")
            return {'CANCELLED'}

        if folder_mod_date < last_commit_date:
            self.report({'INFO'}, "Найдены новые обновления. Запуск обновления...")
            download_and_replace_assets()
        else:
            self.report({'INFO'}, "Активы актуальны. Обновления не требуются.")
        return {'FINISHED'}

classes = (ANONIM4IK_AssetUpdaterPanel, ANONIM4IK_UpdateAssetsOperator)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    if os.path.exists(ASSETS_PATH):
        register_asset_library(ASSETS_PATH)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()