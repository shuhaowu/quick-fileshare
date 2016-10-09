# quick-fileshare

Like SimpleHTTPServer, but with optional upload/delete. 

The idea is that you can install this thing and then just type:

    $ quick-fileshare

This then spawns a server at a default port (8000) and then be able to show
files from the current working directory for others to download. You can change
the directory by using the environment variable `QFS_BASEPATH`

For security reasons, the upload/file deletion functionalities are disabled and
can be enabled with the environment variables:

    QFS_READONLY=false # allows uploading if true. By default this is true. 
    QFS_ALLOW_DELETE=false # allow delete if true. QFS_READONLY must also be false for this to work

## installation

    $ python setup.py install

## development

    $ mkvirtualenv quick-fileshare
    $ pip install Flask
    $ ./dev_server # in a virtualenv

Look at that script to toggle settings.