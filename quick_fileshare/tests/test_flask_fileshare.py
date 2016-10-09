from __future__ import absolute_import

import os
from io import BytesIO
import unittest
import shutil
import tempfile

from ..app import app


class QfsTestCase(unittest.TestCase):

  def setUp(self):
    self.base_path = tempfile.mkdtemp()
    self.touch_file("file1", "file1content")
    self.touch_file("file2", "file2content")
    os.mkdir(os.path.join(self.base_path, "dir1"))
    self.touch_file("dir1/file3", "file3content")
    os.mkdir(os.path.join(self.base_path, "dir2"))
    self.touch_file("dir2/file4", "file4content")

    app.config["BASEPATH"] = self.base_path
    app.config["READONLY"] = True
    app.config["ALLOW_DELETE"] = False
    app.config["TESTING"] = True
    self.app = app.test_client()

  def enable_upload(self):
    app.config["READONLY"] = False

  def enable_delete(self):
    self.enable_upload()
    app.config["ALLOW_DELETE"] = True

  def set_csrf(self):
    with self.app.session_transaction() as sess:
      sess["_csrf_token"] = "csrf"

  def touch_file(self, name, content=""):
    with open(os.path.join(self.base_path, name), "w") as f:
      f.write(content)

  def tearDown(self):
    shutil.rmtree(self.base_path)

  def test_list_root_files_correctly(self):
    rv = self.app.get("/files/")
    assert b"file1" in rv.data
    assert b"file2" in rv.data
    assert b"dir1" in rv.data
    assert b"dir2" in rv.data
    assert b".." not in rv.data

  def test_list_directory_files_correctly(self):
    rv = self.app.get("/files/dir1/")
    assert b"file1" not in rv.data
    assert b"file2" not in rv.data
    assert b"dir2" not in rv.data
    assert b".." in rv.data
    assert b"file3" in rv.data

    rv = self.app.get("/files/dir2/")
    assert b"file1" not in rv.data
    assert b"file2" not in rv.data
    assert b"dir1" not in rv.data
    assert b".." in rv.data
    assert b"file4" in rv.data

  def test_get_file_correctly(self):
    rv = self.app.get("/files/file1")
    assert b"file1content" == rv.data
    rv.close()

    rv = self.app.get("/files/file2")
    assert b"file2content" == rv.data
    rv.close()

    rv = self.app.get("/files/dir1/file3")
    assert b"file3content" == rv.data
    rv.close()

    rv = self.app.get("/files/dir2/file4")
    assert b"file4content" == rv.data
    rv.close()

  def test_get_nonexistent_file_will_404(self):
    rv = self.app.get("/files/file3")
    assert 404 == rv.status_code

    rv = self.app.get("/files/dir1/file1")
    assert 404 == rv.status_code

    rv = self.app.get("/files/dir2/file3")
    assert 404 == rv.status_code

  def test_upload_file(self):
    self.set_csrf()
    self.enable_upload()

    rv = self.app.post("/files/", content_type="multipart/form-data", data={
      "_csrf_token": "csrf",
      "file": (BytesIO(b"hello world"), "uploaded_file.txt")
    })

    self.assertEqual(302, rv.status_code)
    assert rv.location.endswith("/files/")

    local_path = os.path.join(self.base_path, "uploaded_file.txt")
    assert os.path.isfile(local_path)
    with open(local_path) as f:
      assert "hello world" == f.read()

  def test_upload_file_will_overwrite(self):
    self.enable_upload()
    self.set_csrf()
    rv = self.app.post("/files/", content_type="multipart/form-data", data={
      "_csrf_token": "csrf",
      "file": (BytesIO(b"hello world2"), "file1")
    })

    self.assertEqual(302, rv.status_code)
    assert rv.location.endswith("/files/")

    local_path = os.path.join(self.base_path, "file1")
    assert os.path.isfile(local_path)
    with open(local_path) as f:
      assert "hello world2" == f.read()

  def test_upload_file_will_upload_into_directory(self):
    self.enable_upload()
    self.set_csrf()
    rv = self.app.post("/files/dir1/", content_type="multipart/form-data", data={
      "_csrf_token": "csrf",
      "file": (BytesIO(b"hello world3"), "uploaded_file.txt")
    })

    self.assertEqual(302, rv.status_code)
    assert rv.location.endswith("/files/dir1/")

    local_path = os.path.join(self.base_path, "dir1/uploaded_file.txt")
    assert os.path.isfile(local_path)
    with open(local_path) as f:
      assert "hello world3" == f.read()

  def test_upload_file_will_400_without_csrf(self):
    self.enable_upload()

    rv = self.app.post("/files/", content_type="multipart/form-data", data={
      "file": (BytesIO(b"hello world"), "uploaded_file.txt")
    })

    self.assertEqual(400, rv.status_code)

    assert not os.path.isfile(os.path.join(self.base_path, "dir1/uploaded_file.txt"))

  def test_upload_file_while_readonly_will_405(self):
    self.set_csrf()

    rv = self.app.post("/files/", content_type="multipart/form-data", data={
      "_csrf_token": "csrf",
      "file": (BytesIO(b"hello world"), "uploaded_file.txt"),
    })

    self.assertEqual(405, rv.status_code)

    assert not os.path.isfile(os.path.join(self.base_path, "dir1/uploaded_file.txt"))

  def test_upload_file_that_is_a_directory_will_400(self):
    self.set_csrf()
    self.enable_upload()

    rv = self.app.post("/files/", content_type="multipart/form-data", data={
      "_csrf_token": "csrf",
      "file": (BytesIO(b"hello world"), "dir1"),
    })

    self.assertEqual(400, rv.status_code)

  def test_upload_file_that_in_non_existent_directory_will_404(self):
    self.set_csrf()
    self.enable_upload()

    rv = self.app.post("/files/dir3/", content_type="multipart/form-data", data={
      "_csrf_token": "csrf",
      "file": (BytesIO(b"hello world"), "uploaded_file.txt"),
    })

    self.assertEqual(404, rv.status_code)

    assert not os.path.isfile(os.path.join(self.base_path, "dir3/uploaded_file.txt"))

  def test_delete_file(self):
    self.set_csrf()
    self.enable_upload()
    self.enable_delete()

    rv = self.app.post("/delete/file1", data={
      "_csrf_token": "csrf",
    })

    self.assertEqual(302, rv.status_code)
    assert rv.location.endswith("/files/")

    assert not os.path.exists(os.path.join(self.base_path, "file1"))

  def test_delete_file_will_400_without_csrf(self):
    self.enable_upload()
    self.enable_delete()

    rv = self.app.post("/delete/file1")

    self.assertEqual(400, rv.status_code)

    assert os.path.exists(os.path.join(self.base_path, "file1"))

  def test_delete_file_will_405_if_readonly(self):
    self.set_csrf()
    app.config["ALLOW_DELETE"] = True

    rv = self.app.post("/delete/file1", data={"_csrf_token": "csrf"})

    self.assertEqual(405, rv.status_code)

    assert os.path.exists(os.path.join(self.base_path, "file1"))

  def test_delete_file_will_405_if_not_allowed_to_delete(self):
    self.set_csrf()
    self.enable_upload()

    rv = self.app.post("/delete/file1", data={"_csrf_token": "csrf"})

    self.assertEqual(405, rv.status_code)

    assert os.path.exists(os.path.join(self.base_path, "file1"))

  def test_delete_file_will_501_if_trying_to_delete_directory(self):
    self.set_csrf()
    self.enable_upload()
    self.enable_delete()

    rv = self.app.post("/delete/dir1", data={"_csrf_token": "csrf"})

    self.assertEqual(501, rv.status_code)

    assert os.path.exists(os.path.join(self.base_path, "dir1"))

  def test_delete_file_will_delete_file_in_directory(self):
    self.set_csrf()
    self.enable_upload()
    self.enable_delete()

    rv = self.app.post("/delete/dir1/file3", data={
      "_csrf_token": "csrf",
    })

    self.assertEqual(302, rv.status_code)
    assert rv.location.endswith("/files/dir1")

    assert not os.path.exists(os.path.join(self.base_path, "dir1/file3"))

  def test_delete_file_will_404_if_file_does_not_exist(self):
    self.set_csrf()
    self.enable_upload()
    self.enable_delete()

    rv = self.app.post("/delete/dir1/file44", data={
      "_csrf_token": "csrf",
    })

    self.assertEqual(404, rv.status_code)
