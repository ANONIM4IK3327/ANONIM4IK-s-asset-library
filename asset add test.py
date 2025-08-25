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
# Имя, которое будет использоваться для создания папки аддона, если аддон устанавливается как пакет
ADDON_NAME = "anonim4ik_asset_updater"
# ----------------------------------

# URL-ы для получения данных с GitHub (основная ветка)
GITHUB_REPO_URL_MAIN = "https://api.github.com/repos/ANONIM4IK3327/ANONIM4IK-s-asset-library/commits?sha=main"
DOWNLOAD_URL_MAIN = "https://github.com/ANONIM4IK3327/ANONIM4IK-s-asset-library/archive/refs/heads/main.zip"

# URL-ы для получения данных с GitHub (экспериментальная ветка)
EXPERIMENTAL_GITHUB_REPO_URL = "https://api.github.com/repos/ANONIM4IK3327/ANONIM4IK-s-asset-library/commits?sha=experimental"
EXPERIMENTAL_DOWNLOAD_URL = "https://github.com/ANONIM4IK3327/ANONIM4IK-s-asset-library/archive/refs/heads/experimental.zip"

def get_blender_user_data_base_path():
    """
    Возвращает базовый путь к пользовательским данным Blender (например, .../Blender/4.1).
    Это основа для asset_libraries и других пользовательских настроек.
    Использует pathlib.Path для корректного построения путей на разных ОС.
    """
    version_tuple = bpy.app.version
    major_minor = f"{version_tuple[0]}.{version_tuple[1]}"
    system = platform.system()

    if system == "Windows":
        base_path = Path(os.getenv('APPDATA')) if os.getenv('APPDATA') else Path.home() / "AppData" / "Roaming"
        data_path = base_path / "Blender Foundation" / "Blender" / major_minor
    elif system == "Darwin":
        data_path = Path.home() / "Library" / "Application Support" / "Blender" / major_minor
    else: # Linux
        data_path = Path.home() / ".config" / "blender" / major_minor
    
    return data_path.as_posix() # Возвращаем строку с прямыми слешами

# ASSETS_PATH_OBJ: Объект Path, представляющий путь к папке ассетов
# ASSETS_PATH_STR: Строка пути к папке ассетов, используемая в shutil и os
ASSETS_PATH_OBJ = Path(get_blender_user_data_base_path()) / "datafiles" / "asset_libraries" / ASSET_LIBRARY_NAME
ASSETS_PATH_STR = ASSETS_PATH_OBJ.as_posix() # Используем строку для всех операций с os и shutil

def get_current_urls(use_experimental_branch):
    """Возвращает URL-ы GitHub в зависимости от выбранной ветки."""
    if use_experimental_branch:
        return EXPERIMENTAL_GITHUB_REPO_URL, EXPERIMENTAL_DOWNLOAD_URL
    else:
        return GITHUB_REPO_URL_MAIN, DOWNLOAD_URL_MAIN

def get_last_commit_date(operator_instance, use_experimental_branch): # Передаем operator_instance и флаг ветки
    """Получает дату последнего коммита с GitHub."""
    github_url, _ = get_current_urls(use_experimental_branch)
    try:
        response = requests.get(github_url)
        if response.status_code == 200:
            commits = response.json()
            if commits:
                last_commit_date_str = commits[0]['commit']['committer']['date']
                return time.strptime(last_commit_date_str, "%Y-%m-%dT%H:%M:%SZ")
            else:
                operator_instance.report({'WARNING'}, f"Нет коммитов в репозитории по URL: {github_url}")
                return None
        else:
            operator_instance.report({'ERROR'}, f"Не удалось получить данные о коммитах с {github_url}: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        operator_instance.report({'ERROR'}, f"Ошибка сети при получении данных о коммитах с {github_url}: {e}")
        return None
    except Exception as e:
        operator_instance.report({'ERROR'}, f"Неизвестная ошибка при получении данных о коммитах с {github_url}: {e}")
        return None

def get_folder_modification_date(path, operator_instance): # Передаем operator_instance
    """Получает дату последнего изменения указанной папки."""
    try:
        if not os.path.exists(path):
            operator_instance.report({'WARNING'}, f"Папка не найдена для проверки даты изменения: {path}")
            return None
        timestamp = os.path.getmtime(path)
        return time.gmtime(timestamp)
    except Exception as e:
        operator_instance.report({'ERROR'}, f"Ошибка при получении даты изменения папки {path}: {e}")
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

    print(f"[INFO] Библиотека «{library_name}» зарегистрирована. Пожалуйста, сохраните настройки Blender вручную, если это необходимо.")


def download_and_replace_assets(operator_instance, use_experimental_branch): # Передаем operator_instance и флаг ветки
    """Скачивает архив с GitHub и устанавливает (или обновляет) ассеты из подпапки 'assets' в ASSETS_PATH_STR."""
    _, download_url = get_current_urls(use_experimental_branch)
    try:
        temp_dir = Path(bpy.app.tempdir) / "anonim4ik-assets-temp"
        zip_path = temp_dir / "assets.zip"
        
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir(parents=True, exist_ok=True)

        operator_instance.report({'INFO'}, f"Скачивание активов с {download_url}...")
        response = requests.get(download_url, stream=True)
        response.raise_for_status() # Вызывает HTTPError для плохих ответов (4xx или 5xx)

        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        operator_instance.report({'INFO'}, f"Архив успешно скачан в {zip_path.name}")

        operator_instance.report({'INFO'}, f"Распаковка архива...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        operator_instance.report({'INFO'}, f"Архив успешно распакован.")

        extracted_folders = [f for f in temp_dir.iterdir() if f.is_dir() and f.name.startswith("ANONIM4IK-s-asset-library-")]
        
        if not extracted_folders:
            operator_instance.report({'ERROR'}, "Не удалось найти корневую папку скачанного репозитория (например, 'ANONIM4IK-s-asset-library-main' или 'ANONIM4IK-s-asset-library-experimental').")
            shutil.rmtree(temp_dir)
            return

        repo_root_folder = extracted_folders[0] # Это папка типа ANONIM4IK-s-asset-library-main/experimental
        
        # Определяем путь к папке 'assets' внутри скачанного репозитория
        source_assets_folder = repo_root_folder / "assets"
        
        if not source_assets_folder.is_dir():
            operator_instance.report({'ERROR'}, f"Папка с ассетами '{source_assets_folder.name}' не найдена внутри скачанного репозитория. Убедитесь, что ассеты находятся в подпапке 'assets'.")
            shutil.rmtree(temp_dir)
            return

        # Удаляем существующую папку активов (если есть) перед копированием
        if Path(ASSETS_PATH_STR).exists():
            operator_instance.report({'INFO'}, f"Удаление существующей папки активов: {ASSETS_PATH_STR}")
            shutil.rmtree(ASSETS_PATH_STR)

        # Создаем целевую папку для ассетов, если она не существует
        Path(ASSETS_PATH_STR).mkdir(parents=True, exist_ok=True)
        operator_instance.report({'INFO'}, f"Копирование активов из {source_assets_folder.as_posix()} в {ASSETS_PATH_STR}")
        
        # Копируем содержимое папки 'assets' из архива в ASSETS_PATH_STR
        shutil.copytree(source_assets_folder.as_posix(), ASSETS_PATH_STR, dirs_exist_ok=True)

        operator_instance.report({'INFO'}, "Активы успешно обновлены!")
        register_asset_library(ASSETS_PATH_STR)
        
    except requests.exceptions.RequestException as e:
        operator_instance.report({'ERROR'}, f"Ошибка сети при скачивании активов: {e}")
    except zipfile.BadZipFile:
        operator_instance.report({'ERROR'}, "Скачанный файл не является действительным ZIP-архивом. Возможно, файл поврежден.")
    except Exception as e:
        operator_instance.report({'ERROR'}, f"Общая ошибка при скачивании или установке активов: {e}")
    finally:
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                print(f"[INFO] Временная директория очищена.") # Вывод в консоль, не в UI
            except Exception as e:
                print(f"[WARN] Не удалось удалить временную директорию: {e}") # Вывод в консоль

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
        
        # Добавляем галочку для выбора экспериментальной ветки
        row = layout.row()
        row.prop(context.scene, "use_experimental_branch", text="Использовать экспериментальную ветку")


class ANONIM4IK_UpdateAssetsOperator(bpy.types.Operator):
    bl_idname = "wm.anonim4ik_update_assets"
    bl_label = "Check for Updates"
    
    def execute(self, context):
        # Получаем значение галочки из контекста сцены
        use_experimental_branch = context.scene.use_experimental_branch

        # Если папки ассетов не существует или она пуста, скачиваем их в первый раз
        if not Path(ASSETS_PATH_STR).exists() or not list(Path(ASSETS_PATH_STR).iterdir()):
            self.report({'INFO'}, "Папка ассетов не найдена или пуста, скачиваем заново...")
            download_and_replace_assets(self, use_experimental_branch) # Передаем self и флаг
            return {'FINISHED'}

        folder_mod_date = get_folder_modification_date(ASSETS_PATH_STR, self) # Передаем self
        if not folder_mod_date:
            self.report({'ERROR'}, "Не удалось получить дату изменения папки. Возможно, папка не существует.")
            return {'CANCELLED'}

        last_commit_date = get_last_commit_date(self, use_experimental_branch) # Передаем self и флаг
        if not last_commit_date:
            self.report({'ERROR'}, "Не удалось получить дату последнего коммита. Проверьте подключение к интернету или URL репозитория.")
            return {'CANCELLED'}

        # Сравниваем даты
        if folder_mod_date < last_commit_date:
            self.report({'INFO'}, "Найдены новые обновления. Запуск обновления...")
            download_and_replace_assets(self, use_experimental_branch) # Передаем self и флаг
        else:
            self.report({'INFO'}, "Активы актуальны. Обновления не требуются.")
        return {'FINISHED'}

classes = (ANONIM4IK_AssetUpdaterPanel, ANONIM4IK_UpdateAssetsOperator)

def register():
    # Регистрация свойств сцены (BoolProperty)
    bpy.types.Scene.use_experimental_branch = bpy.props.BoolProperty(
        name="Использовать экспериментальную ветку",
        description="Скачивать ассеты из экспериментальной ветки GitHub",
        default=False
    )

    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Регистрируем библиотеку ассетов при регистрации аддона, если папка ассетов уже существует
    # Это полезно, если пользователь уже скачал ассеты ранее или аддон был обновлен.
    # Проверка на существование и непустоту папки ASSETS_PATH_STR
    if Path(ASSETS_PATH_STR).exists() and list(Path(ASSETS_PATH_STR).iterdir()):
        print(f"[INFO] Обнаружена существующая папка активов: {ASSETS_PATH_STR}. Попытка регистрации библиотеки.")
        register_asset_library(ASSETS_PATH_STR)
    else:
        print(f"[INFO] Папка активов {ASSETS_PATH_STR} не существует или пуста. Активы будут скачаны при первом запуске оператора.")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Удаление свойств сцены при деактивации аддона
    del bpy.types.Scene.use_experimental_branch

