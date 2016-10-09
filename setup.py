from setuptools import setup

setup(
  name="quick-fileshare",
  version="0.1",
  include_package_data=True,
  zip_safe=False,
  install_requires=["Flask"],
  url="https://github.com/shuhaowu/flask-fileshare",
  author="Shuhao Wu",
  packages=["quick_fileshare"],
  entry_points={
    "console_scripts": [
      "quick-fileshare = quick_fileshare.app:main"
    ]
  }
)
