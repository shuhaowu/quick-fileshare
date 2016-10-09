from __future__ import absolute_import

import os
import os.path

try:
  from urllib import quote
except ImportError:
  from urllib.parse import quote

from flask import Flask, render_template, abort, send_file, redirect, url_for, request, safe_join
from werkzeug.utils import secure_filename


def get_envbool(name, default):
  value = os.environ.get(name, default)
  if isinstance(value, str):
    value = value.lower()

  if not value or value in ("0", "false"):
    return False
  else:
    return True


app = Flask(__name__)
app.config.update(
  BASEPATH=os.environ.get("QFS_BASEPATH", os.getcwd()),
  READONLY=get_envbool("QFS_READONLY", True),
  ALLOW_DELETE=get_envbool("QFS_ALLOW_DELETE", False),
)
app.jinja_env.filters["urlencode"] = lambda u: quote(u)


@app.route("/")
def index():
  return redirect(url_for("files"))


@app.route("/files/", defaults={"filepath": ""}, methods=["GET", "POST"])
@app.route("/files/<path:filepath>", methods=["GET", "POST"])
def files(filepath):
  local_path = safe_join(app.config["BASEPATH"], filepath)
  if not os.path.exists(local_path):
    return abort(404)

  if request.method == "POST":
    if app.config["READONLY"]:
      return abort(403)

    return upload_file(local_path, filepath)
  elif os.path.isfile(local_path):
    return send_file(local_path)

  current_path = filepath
  if not current_path.startswith("/"):
    current_path = "/" + current_path

  if not current_path.endswith("/"):
    current_path = current_path + "/"

  variables = {
    "readonly": app.config["READONLY"],
    "allow_delete": app.config["ALLOW_DELETE"],
    "listing": [],
    "current_path": current_path,
  }

  if current_path != "/":
    variables["parent_path"] = os.path.dirname(current_path.rstrip("/"))

  files = []
  directories = []
  for fn in os.listdir(local_path):
    path = os.path.join(local_path, fn)
    if os.path.isfile(path):
      # the str conversion is such that we don't display -- for a size of 0
      files.append({"name": fn, "type": "file", "size": str(os.path.getsize(path))})
    elif os.path.isdir(path):
      directories.append({"name": fn, "type": "dir"})

  files.sort(key=lambda x: x["name"].lower())
  directories.sort(key=lambda x: x["name"].lower())

  variables["listing"].extend(directories)
  variables["listing"].extend(files)

  return render_template("files.html", **variables)


@app.route("/delete/", defaults={"filepath": ""})
@app.route("/delete/<path:filepath>")
def delete_file(filepath):
  if app.config["READONLY"] or not app.config["ALLOW_DELETE"]:
    return abort(403)

  local_path = safe_join(app.config["BASEPATH"], filepath)
  if not os.path.exists(local_path):
    return abort(404)

  if not os.path.isfile(local_path):
    return abort(501)

  os.remove(local_path)
  return redirect(url_for("files", filepath=os.path.dirname(filepath)))


def upload_file(local_directory_path, filepath):
  file = request.files.get("file")
  if not file or file.filename == "":
    return redirect(url_for("files", filepath=filepath))

  filename = secure_filename(file.filename)
  file.save(os.path.join(local_directory_path, filename))
  return redirect(url_for("files", filepath=filepath))


def main():
  app.run(host=os.environ.get("HOST"), port=os.environ.get("PORT", 8000), debug=False)
