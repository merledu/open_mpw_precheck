# SPDX-FileCopyrightText: 2020 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

from strsimpy.sorensen_dice import SorensenDice

# Default value for file headers, names, and paths
_lib_license_filename = 'LICENSE'
_license_filename = 'LICENSE'
_approved_licenses_path = 'base_checks/_licenses/_approved_licenses'
_prohibited_licenses_path = 'base_checks/_licenses/_prohibited_licenses'

_spdx_copyright_header = 'SPDX-FileCopyrightText'
_spdx_license_header = 'SPDX-License-Identifier'

# Directories ignored for license check
IGNORED_DIRS = ['.git', 'gl', 'third_party']

# File extensions to be ignored for license check
IGNORED_EXTS = ['.cfg', '.csv', '.def', '.drc', '.gds', '.hex', '.jpg', '.lef', '.log', '.mag', '.out', '.pdf', '.png', '.pyc', '.rdb', '.spice', '.svg', '.txt', '.vcd', '.xml']

# Files ignored for license check
IGNORED_FILES = ['.git', '.gitignore', '.gitmodules', 'manifest', 'info.yaml', 'LICENSE', 'PDK_SOURCES', 'OPENLANE_VERSION']

def check_license(user_license_path, licenses_path):
    confidence_map = []
    user_license_content = user_license_path.open(encoding="utf-8").read()
    for license_file in Path(licenses_path).iterdir():
        try:
            license_content = license_file.open(encoding="utf-8").read()
            confidence = 100 * (1 - SorensenDice().distance(license_content.strip(), user_license_content.strip()))
            confidence_map.append({"license_key": license_file.stem, "confidence": confidence})
        except UnicodeDecodeError:
            continue
        except FileNotFoundError as not_found:
            if not os.path.islink(not_found.filename):
                print("FILE (%s) ERROR: %s" % (not_found.filename, e))
            continue

    license_check_result = max(confidence_map, key=lambda x: x["confidence"])
    return license_check_result["license_key"] if license_check_result["confidence"] > 95 else None

def check_main_license(path):
    path = Path(os.path.join(path, _license_filename))
    try:
        result = check_license(path, _prohibited_licenses_path)
        if result:
            return {"approved": False, "license_key": result, "path":path}
        else:
            result = check_license(path, _approved_licenses_path)
            return {"approved": True, "license_key": result, "path":path} if result else {"approved": True, "license_key": None, "path":path}
    except OSError as e:
        print("MAIN LICENSE OS ERROR: %s" % e)
        return None
    except Exception as e:
        print("MAIN LICENSE ERROR: %s" % e)
        return None


def check_lib_license(path):
    libs = []
    if os.path.exists(path):
        for lib_path in next(os.walk(path))[1]:
            result = check_main_license(os.path.join(path, lib_path))
            if result:
                libs.append(result)
    return libs


def check_dir_spdx_compliance(non_compliant_list, path, license_key=None):
    if os.path.exists(path):
        root, dirs, files = next(os.walk(path))
        for file in files:
            try:
                result = check_file_spdx_compliance(os.path.join(root, file), license_key)
                if result:
                    non_compliant_list.append(result)
            except Exception as e:
                print("DIRECTORY (%s) ERROR: %s" % (root, e))
        for dr in dirs:
            # NOTE: ignoring third party directory for SPDX compliance
            if dr in IGNORED_DIRS:
                continue
            try:
                check_dir_spdx_compliance(non_compliant_list, os.path.join(root, dr), license_key)
            except Exception as e:
                print("DIRECTORY (%s) ERROR: %s" % (dr, e))

    return non_compliant_list


def check_file_spdx_compliance(file_path, license_key):
    global _spdx_license_header
    _spdx_license_header = '%s: %s' % ('SPDX-License-Identifier', license_key) if license_key else _spdx_license_header

    spdx_compliant = spdx_cp_compliant = spdx_ls_compliant = False

    # Filter out ignored files and extensions
    file_base = os.path.basename(file_path)
    if file_base in IGNORED_FILES:
        return None
    _, file_ext = os.path.splitext(file_base)
    if file_ext in IGNORED_EXTS:
        return None

    try:
        with open(file_path, "tr", encoding="utf-8") as f:
            lines = [x.rstrip() for x in f.readlines()]
        f.close()
        if lines and list(filter(None, lines)):
            for line in lines:
                if line:
                    if _spdx_copyright_header in line:
                        spdx_cp_compliant = True
                    if _spdx_license_header in line:
                        spdx_ls_compliant = True

                if spdx_cp_compliant and spdx_ls_compliant:
                    spdx_compliant = True
                    break
            return file_path if not spdx_compliant else None
    except UnicodeDecodeError as e:
        print("FILE (%s) UD ERROR: %s" % (file_path, e))
        pass
    except FileNotFoundError as not_found:
        if not os.path.islink(not_found.filename):
            print("FILE (%s) ERROR: %s" % (not_found.filename, e))
        pass
    except Exception as e:
        print("FILE (%s) ERROR: %s" % (file_path, e))
    return None

def check_submodules_license(path):
    licenses_approval = []

    for root, dirs, files in os.walk(path):
        if ".git" not in dirs or root == path:
            continue
        result = check_main_license(root)
        if result:
            licenses_approval.append(result)
    return licenses_approval

if __name__ == "__main__":
    _prohibited_licenses_path = '_licenses/_prohibited_licenses'
    _approved_licenses_path = '_licenses/_approved_licenses'

    print("{{RESULT}} License there! ") if check_main_license('.') else print("{{FAIL}} License not there or empty!")

    spdx_non_compliant_list = check_dir_spdx_compliance([], '.')
    if spdx_non_compliant_list:
        print("{{SPDX COMPLIANCE WARNING}} We found %s files that are not compliant with the SPDX Standard" % spdx_non_compliant_list.__len__())
    else:
        print("{{SPDX COMPLIANCE PASSED}} Project is compliant with SPDX Standard")

    print("{{RESULT}} ", check_lib_license('.'))
