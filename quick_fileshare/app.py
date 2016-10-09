from __future__ import absolute_import

import os
import os.path
import string
import random

try:
  from urllib import quote
except ImportError:
  from urllib.parse import quote

from builtins import range
from flask import Flask, render_template, abort, send_file, redirect, url_for, request, safe_join, session, flash
from werkzeug.utils import secure_filename


def get_envbool(name, default):
  value = os.environ.get(name, default)
  if isinstance(value, str):
    value = value.lower()

  if not value or value in ("0", "false"):
    return False
  else:
    return True

TOKEN_CHARACTERS = string.ascii_letters + string.digits


def generate_csrf_token():
  if "_csrf_token" not in session:
    rng = random.SystemRandom()
    session["_csrf_token"] = "".join([rng.choice(TOKEN_CHARACTERS) for i in range(32)])

  return session["_csrf_token"]


app = Flask(__name__)
app.config.update(
  ALLOW_DELETE=get_envbool("QFS_ALLOW_DELETE", False),
  BASEPATH=os.environ.get("QFS_BASEPATH", os.getcwd()),
  READONLY=get_envbool("QFS_READONLY", True),
  SECRET_KEY=os.urandom(24),
)

app.jinja_env.filters["urlencode"] = lambda u: quote(u)
app.jinja_env.globals["csrf_token"] = generate_csrf_token


@app.before_request
def csrf_protect():
  if request.method == "POST":
    token = session.pop("_csrf_token", None)
    if not token or token != request.form.get("_csrf_token"):
      abort(400)


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
      return abort(405)

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


@app.route("/delete/", defaults={"filepath": ""}, methods=["POST"])
@app.route("/delete/<path:filepath>", methods=["POST"])
def delete_file(filepath):
  if app.config["READONLY"] or not app.config["ALLOW_DELETE"]:
    return abort(405)

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
    flash("No file selected.", "alert")
    return redirect(url_for("files", filepath=filepath))

  filename = secure_filename(file.filename)
  file_local_path = os.path.join(local_directory_path, filename)
  if os.path.exists(file_local_path) and not os.path.isfile(file_local_path):
    return abort(400)

  file.save(file_local_path)
  return redirect(url_for("files", filepath=filepath))


def main():
  app.run(host=os.environ.get("HOST"), port=os.environ.get("PORT", 8000), debug=False)
