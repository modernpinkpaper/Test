"""Fill the library page with the collected sound list: python asmr/build_library_page.py LIB_DIR
(LIB_DIR from collect_sounds.py). Writes LIB_DIR/index.html next to LIB_DIR/sounds/."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
lib_dir = sys.argv[1]
lib = json.load(open(os.path.join(lib_dir, "library.json")))
page = open(os.path.join(HERE, "library_page.html")).read()
page = page.replace("/*LIBRARY*/[]", json.dumps(lib, ensure_ascii=False).replace("</", "<\\/"))
open(os.path.join(lib_dir, "index.html"), "w").write(page)
print(len(lib), "clips")
