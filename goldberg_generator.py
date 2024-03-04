import configparser
import json
import os
import shutil
import zipfile

import requests

from generate_emu_config import generate_config

GOLDBERG_GITLAB_RELEASES_URL = (
    "https://gitlab.com/api/v4/projects/Mr_Goldberg%2Fgoldberg_emulator/releases"
)
GOLDBERG_VERSION_PATH = "emulator/version.txt"
STEAM_APP_LIST_URL = "http://api.steampowered.com/ISteamApps/GetAppList/v2"
APP_LIST_PATH = "app_list.json"
GOLDBERG_SAVE_PATH = os.getenv("APPDATA") + "\\Goldberg SteamEmu Saves"

ANSI_RED = "\033[0;31m"
ANSI_YELLOW = "\033[0;33m"
ANSI_BLUE = "\033[0;34m"
ANSI_RESET = "\033[0m"

CREDS_PATH = "creds.ini"
config = configparser.ConfigParser(interpolation=None)


def logger(msg, level="info"):
    if level.lower() == "error":
        print(f"{ANSI_RED}[ERROR]{ANSI_RESET} {msg}")
    elif level.lower() == "warning":
        print(f"{ANSI_YELLOW}[WARNING]{ANSI_RESET} {msg}")
    elif level.lower() == "info":
        print(f"{ANSI_BLUE}[INFO]{ANSI_RESET} {msg}")


def download_latest_goldberg(assets, version):
    if len(assets) == 0:
        return "No assets found"

    try:
        shutil.rmtree("emulator")
    except FileNotFoundError:
        logger("No previous emulator found")

    url = assets["links"][0]["url"]
    response = requests.get(url, timeout=5)
    filename = "goldberg.zip"
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        with zipfile.ZipFile(filename, "r") as zip_ref:
            zip_ref.extractall("emulator")
        os.remove(filename)

        with open(GOLDBERG_VERSION_PATH, "w", encoding="utf-8") as f:
            f.write(version)

        return "Downloaded latest Goldberg release"
    else:
        return "Failed to download latest Goldberg release"


def check_for_emulator_updates():
    response = requests.get(GOLDBERG_GITLAB_RELEASES_URL, timeout=5)

    if response.status_code == 200:
        releases = response.json()
        if releases:
            latest_release = releases[0]
            version = latest_release["tag_name"]
            logger("Latest Goldberg release: " + version)
            if (
                os.path.exists(GOLDBERG_VERSION_PATH)
                and open(GOLDBERG_VERSION_PATH, "r", encoding="utf-8").read() == version
            ):
                return "No need to update"
            else:
                return download_latest_goldberg(latest_release["assets"], version)
        else:
            return "No releases found"
    else:
        return "Failed to get latest release"


def download_latest_app_list():
    response = requests.get(STEAM_APP_LIST_URL, timeout=5)

    if response.status_code == 200:
        data = response.json()
        with open(APP_LIST_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return "Downloaded latest app list"
    else:
        return "Failed to download latest app list"


def update_app_list():
    # TODO: When UI is ready there will be a button to update the app list
    pass


def get_appid_by_name(game_name):
    if not os.path.exists(APP_LIST_PATH):
        download_latest_app_list()

    with open(APP_LIST_PATH, "r", encoding="utf-8") as data:
        json_data = json.load(data)
        app_list = json_data["applist"]["apps"]

        options = []
        for app in app_list:
            if game_name.lower() in app["name"].lower():
                options.append(app)
                print(f"{len(options)}. {app['name']} [{app['appid']}]")

        if len(options) == 0:
            logger("No games found", "error")
            return None

        selection = input("Select game: ")
        while (
            not selection.isdigit()
            or int(selection) < 1
            or int(selection) > len(options)
        ):
            selection = input("Invalid selection. Select game: ")

        return options[int(selection) - 1]["appid"]


def find_steamapi_path(original_path):
    for root, _dirs, files in os.walk(original_path):
        if "steam_api64.dll" in files or "steam_api.dll" in files:
            return root


def backup_original_dll(path):
    if os.path.exists(os.path.join(path, "steam_api64.dll")):
        if os.path.exists(os.path.join(path, "steam_api64.dll.bk")):
            logger("Backup already exists")
        else:
            logger("Backing up original steam_api64.dll")
            shutil.copy(
                os.path.join(path, "steam_api64.dll"),
                os.path.join(path, "steam_api64.dll.bk"),
            )

    if os.path.exists(os.path.join(path, "steam_api.dll")):
        if os.path.exists(os.path.join(path, "steam_api.dll.bk")):
            logger("Backup already exists")
        else:
            logger("Backing up original steam_api.dll")
            shutil.copy(
                os.path.join(path, "steam_api.dll"),
                os.path.join(path, "steam_api.dll.bk"),
            )


def replace_original_dll(path):
    if os.path.exists(os.path.join(path, "steam_api64.dll")):
        logger("Applying cracked steam_api64.dll")
        shutil.copy(
            os.path.join("emulator", "steam_api64.dll"),
            os.path.join(path, "steam_api64.dll"),
        )

    if os.path.exists(os.path.join(path, "steam_api.dll")):
        logger("Applying cracked steam_api.dll")
        shutil.copy(
            os.path.join("emulator", "steam_api.dll"),
            os.path.join(path, "steam_api.dll"),
        )


# TODO: To use when UI is ready
def delete_temporary_files():
    # TODO: delete appid_outputs and backups
    pass


# NOTE: Not working anymore?
# def generate_steam_TOTP():
#     import hmac, time, base64, hashlib

#     code = ""
#     char = "23456789BCDFGHJKMNPQRTVWXY"

#     hex_time = "%016x" % (int(time.time()) // 30)
#     byte_time = bytes.fromhex(hex_time)

#     digest = hmac.new(
#         base64.b32decode(STEAM_SECRET_KEY), byte_time, hashlib.sha1
#     ).digest()
#     begin = ord(digest[19:20]) & 0xF
#     c_int = int.from_bytes((digest[begin : begin + 4]), "big") & 0x7FFFFFFF

#     for r in range(5):
#         code += char[int(c_int) % len(char)]
#         c_int /= len(char)

#     return code


def get_creds():
    user = None
    pw = None

    if not os.path.exists(CREDS_PATH):
        logger("No creds found, creating new creds file...")
        user = input("Enter your steam username: ")
        pw = input("Enter your steam password: ")

        config.add_section("CREDS")
        config.set("CREDS", "username", user)
        config.set("CREDS", "password", pw)

        with open(CREDS_PATH, "w", encoding="utf-8") as f:
            config.write(f)
    else:
        logger("Creds found")
        config.read(CREDS_PATH)
        user = config.get("CREDS", "username")
        pw = config.get("CREDS", "password")

    return user, pw


if __name__ == "__main__":
    if len(os.sys.argv) < 3:
        print('Usage: python goldberg_generator.py "<game_name>" "<game_path>"')
        exit(1)

    logger(check_for_emulator_updates())

    # TODO: Will do with UI later
    game_path = os.sys.argv[2]

    if not os.path.exists(game_path):
        logger("Invalid path", "error")
        exit(1)

    appid = get_appid_by_name(os.sys.argv[1])
    if appid is None:
        logger("No appid found", "error")
        exit(1)

    steam_dll_path = find_steamapi_path(game_path)

    logger(f"Found DLL path of {appid} in {steam_dll_path}")

    backup_original_dll(steam_dll_path)
    replace_original_dll(steam_dll_path)

    if not os.path.exists(f"{appid}_output"):
        logger("Generating emu config...")
        username, password = get_creds()
        generate_config(appid, username, password)
    else:
        logger("Emu config found")

    if os.path.exists(f"{appid}_output/steam_settings"):
        if os.path.exists(f"{steam_dll_path}/steam_settings"):
            shutil.rmtree(f"{steam_dll_path}/steam_settings")

        logger(f"Copying {appid}_output/steam_settings to {steam_dll_path}")
        shutil.copytree(
            f"{appid}_output/steam_settings", f"{steam_dll_path}/steam_settings"
        )
        logger("Copied steam_settings to game folder")
    else:
        logger("No steam_settings found", "error")
        exit(1)

    appid_save_path = os.path.join(GOLDBERG_SAVE_PATH, str(appid))
    if not os.path.exists(appid_save_path):
        logger("Creating saves folder")
        os.mkdir(appid_save_path)
    else:
        logger("Saves folder already exists")
