import datetime
import json
import os
import shutil


def _read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_json(file_path, default=None):
    """Load data from a JSON file with UTF-8 encoding.

    A missing file is normal (first run) and returns the default.
    A damaged file is never silently treated as empty: it is copied aside
    as <file>.corrupt-<timestamp> and the last good copy (<file>.bak) is used,
    so the next save cannot wipe the user's data.
    """
    if default is None:
        default = []
    if not os.path.exists(file_path):
        return default
    try:
        return _read_json(file_path)
    except (OSError, ValueError) as e:
        print(f"Error: cannot read {file_path}: {e}")

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        shutil.copy2(file_path, f"{file_path}.corrupt-{stamp}")
    except OSError as e:
        print(f"Error: cannot keep a copy of damaged {file_path}: {e}")

    backup_path = f"{file_path}.bak"
    if os.path.exists(backup_path):
        try:
            data = _read_json(backup_path)
            print(f"Restored {file_path} from {backup_path}")
            return data
        except (OSError, ValueError) as e:
            print(f"Error: backup {backup_path} is unreadable too: {e}")
    return default


def prepare_data_files(data_paths, app_dir=".", sample_dir="sample_data"):
    """Make sure every data file exists before the app loads it.

    Paths are relative to app_dir (e.g. "user_data/notify.json").
    - A file that older versions kept right in the app folder is moved into place,
      together with its .bak copy.
    - A file that doesn't exist anywhere yet is created from the demo data in sample_dir.
    Existing files are never touched. Returns the paths that were created from samples.
    """
    created_from_samples = []
    for rel_path in data_paths:
        target = os.path.join(app_dir, rel_path)
        if os.path.exists(target):
            continue
        os.makedirs(os.path.dirname(target) or app_dir, exist_ok=True)
        name = os.path.basename(rel_path)
        legacy = os.path.join(app_dir, name)
        sample = os.path.join(app_dir, sample_dir, name)
        if os.path.abspath(legacy) != os.path.abspath(target) and os.path.exists(legacy):
            shutil.move(legacy, target)
            if os.path.exists(f"{legacy}.bak"):
                shutil.move(f"{legacy}.bak", f"{target}.bak")
            print(f"Moved {legacy} to {target}")
        elif os.path.exists(sample):
            shutil.copy2(sample, target)
            created_from_samples.append(rel_path)
    return created_from_samples


def save_json(file_path, data):
    """Save data to a JSON file atomically.

    The data is written to a temp file first and then swapped in, so a crash
    or power loss mid-write leaves either the old or the new file, never a
    half-written one. The previous version is kept as <file>.bak.
    """
    tmp_path = f"{file_path}.tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    if os.path.exists(file_path):
        shutil.copy2(file_path, f"{file_path}.bak")
    os.replace(tmp_path, file_path)
