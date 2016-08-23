Google Play Music channel plugin for Plex
=========================================

<a href="https://play.google.com/music/">
<img src="https://github.com/sjlouw/GoogleMusic.bundle/raw/master/Contents/Resources/icon-default.png" width="256" height="256" border="0">
</a>

A Plex channel plugin for Google Play Music. An All Access account is not required but many of the features will not work without one. Original source cloned from **jwdempsey's** [fixed branch](https://github.com/pablorusso/GoogleMusic.bundle/tree/update_gmusicapi_fix_login)

Linux Installation Instructions
-------------------------------

```
cd /usr/local/src/
git clone https://github.com/sjlouw/GoogleMusic.bundle
```

1. You will need to compile the Python Cryptographic modules, [pycrypto](https://pypi.python.org/pypi/pycrypto), and copy them into the plugin bundle directory:

**NOTE:** You will need some dependencies like "python-devel" and "gcc" to compile. Install as needed.

```
wget https://pypi.python.org/packages/60/db/645aa9af249f059cc3a368b118de33889219e0362141e75d4eaf6f80f163/pycrypto-2.6.1.tar.gz
tar -zxvf pycrypto-2.6.1.tar.gz

cd pycrypto-2.6.1
python setup.py build

cd build/lib<tab> (directory name could be different - tab-completing it)
cp Crypto/Hash/*.so /usr/local/src/GoogleMusic.bundle/Contents/Libraries/Shared/Crypto/Hash/
cp Crypto/Util/*.so /usr/local/src/GoogleMusic.bundle/Contents/Libraries/Shared/Crypto/Util/
cp Crypto/Cipher/*.so /usr/local/src/GoogleMusic.bundle/Contents/Libraries/Shared/Crypto/Cipher/

mv /usr/local/src/GoogleMusic.bundle/ /var/lib/plexmediaserver/Library/Application\ Support/Plex\ Media\ Server/Plug-ins/
```

2. Restart Plex Media Server

3. Add your Google username and password in the plugin settings after installation.

**Plugin Logs:**

```
/var/lib/plexmediaserver/Library/Application\ Support/Plex\ Media\ Server/Logs/PMS\ Plugin\ Logs/com.plexapp.plugins.googlemusic.log
```