import bpy
import os
import time
import requests
import zipfile
import shutil
from pathlib import Path

bl_info = {
    "name": "ANONIM4IK Asset Updater",
    "author": "Your Name",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > ANONIM4IK Asset Updater",
    "description": "Updates the ANONIM4IK asset library from GitHub.",
    "warning": "",
    "wiki_url": "",
    "category": "Development",
}

# Процедурное определение пути к папке активов
ASSETS_DIR_NAME = "anonim4ik-asset's"
ASSETS_PATH = os.path.join(bpy.utils.user_resource('DATAFILES'), ASSETS_DIR_NAME)

GITHUB_REPO_URL = "https://api.github.com/repos/ANONIM4IK3327/ANONIM4IK-s-asset-library/commits"
DOWNLOAD_URL = "https://github.com/ANONIM4IK3327/ANONIM4IK-s-asset-library/archive/refs/heads/main.zip"

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
    """Получает дату последнего изменения папки."""
    try:
        timestamp = os.path.getmtime(path)
        return time.gmtime(timestamp)
    except Exception as e:
        print(f"Ошибка при получении даты изменения папки: {e}")
        return None

def download_and_replace_assets():
    """Скачивает архив с GitHub и заменяет существующую папку активов."""
    try:
        temp_dir = Path(bpy.app.tempdir) / "anonim4ik-assets-temp"
        zip_path = temp_dir / "assets.zip"

        # Создание временной директории
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Скачивание архива
        response = requests.get(DOWNLOAD_URL, stream=True)
        if response.status_code == 200:
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Распаковка архива
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Определение имени распакованной папки
            extracted_folder = list(temp_dir.glob("ANONIM4IK-s-asset-library-*"))[0]

            # Удаление старой папки активов
            if os.path.exists(ASSETS_PATH):
                shutil.rmtree(ASSETS_PATH)

            # Перемещение новой папки на место старой
            shutil.move(str(extracted_folder), ASSETS_PATH)

            # Удаление временных файлов
            shutil.rmtree(temp_dir)

            print("Активы успешно обновлены!")
        else:
            print(f"Не удалось скачать архив: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при скачивании или установке активов: {e}")

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
            self.report({'ERROR'}, f"Путь к папке активов не существует: {ASSETS_PATH}")
            return {'CANCELLED'}

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

classes = (
    ANONIM4IK_AssetUpdaterPanel,
    ANONIM4IK_UpdateAssetsOperator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()