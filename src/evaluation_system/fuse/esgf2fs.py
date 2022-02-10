import os
import errno
import threading
import logging
import grp
import socket

from stat import S_IFDIR, S_IFREG
from time import time, sleep, mktime
from datetime import datetime
from subprocess import Popen, PIPE, STDOUT
from errno import *

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

from evaluation_system.model.esgf import P2P
from evaluation_system.misc import config
from esgf_crawl_config import Solr2EsgfConfig

from cdo import Cdo

logging.getLogger().setLevel(logging.INFO)


class EsgfFuse(Operations):
    def __init__(self):

        self.logcache = config.get("esgf_logcache")
        # self.logcache= '/pf/b/b324029/cache'
        self.esgftmp = "%s/%s/" % (self.logcache, "ESGF_CACHE")
        self.logpath = "%s/%s/" % (self.logcache, "ESGF_LOG")
        self.esgf_server = config.get("esgf_server").split(",")
        self.hostname = socket.gethostname()

        self.certs = config.get("private_key")
        self.wget = config.get("wget_path")

        self.threadLimiter = threading.BoundedSemaphore(
            int(config.get("parallel_downloads"))
        )
        self.rwlock = threading.Lock()

        self.gid = grp.getgrnam("bmx828").gr_gid
        try:
            os.makedirs(self.logpath, 0e0775)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    #         try:
    #             file(self.logpath+self.wgetlog,'a+').close()
    #             os.chown(self.logpath+self.wgetlog, -1,self.gid)
    #             os.chmod(self.logpath+self.wgetlog,S_IREAD|S_IWRITE|S_IRGRP|S_IWGRP)
    #
    #             file(self.logpath+self.downlog,'a+').close()
    #             os.chown(self.logpath+self.downlog, -1,self.gid)
    #             os.chmod(self.logpath+self.downlog,S_IREAD|S_IWRITE|S_IRGRP|S_IWGRP)
    #         except IOError as e:
    #             pass

    def get_url(self, path, size=False):

        esgfpath, filename = os.path.split(path)

        if size:
            try:
                size = os.path.getsize(self.esgftmp + path)
                return None, size
            except OSError:
                pass
        try:
            (
                project,
                product,
                institute,
                model,
                experiment,
                time_frequency,
                realm,
                variable,
                ensemble,
            ) = esgfpath[1:].split("/")
        except ValueError:
            raise FuseOSError(ENOENT)

        cmor_path = Solr2EsgfConfig().project_select(esgfpath, filename)
        fields = ["url", "size", "timestamp"]
        print(path)
        facets = {
            "project": cmor_path["project"],
            "type": "File",
            "product": cmor_path["product"],
            "institute": cmor_path["institute"],
            "experiment": cmor_path["experiment"],
            "time_frequency": cmor_path["time_frequency"],
            "realm": cmor_path["realm"],
            "variable": cmor_path["variable"],
            "ensemble": cmor_path["ensemble"],
            "title": cmor_path["filename"],
        }
        timestamp = 0
        url = None

        for server in self.esgf_server:
            p2p = P2P(node=server)
            for ncfile in p2p.get_datasets(fields=",".join(fields), **facets):
                url = [url for url in ncfile["url"] if "application/netcdf" in url][0]
                if url is None:
                    continue
                if (
                    mktime(
                        (
                            datetime.strptime(ncfile["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
                        ).timetuple()
                    )
                    >= timestamp
                ):
                    timestamp = mktime(
                        (
                            datetime.strptime(ncfile["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
                        ).timetuple()
                    )
                    size = int(ncfile["size"])
            if url is not None:
                break
        if url is None:
            raise FuseOSError(ENETUNREACH)
        # raise FuseOSError(ENETUNREACH)
        url = url.split("|")[0]
        try:
            return url, size
        except UnboundLocalError:
            print("PATH: " + path)
            print("No url for this PATH")

    def download(self, esgfpath, path, filename, cdo=Cdo()):
        httppath, _ = self.get_url(path)

        with open(self.esgftmp + path + ".lock", "w"):
            pass
        cmor_path = Solr2EsgfConfig().project_select(esgfpath, filename)
        wgetlog = "%s_wget_%s.log" % (
            socket.gethostname(),
            datetime.now().strftime("%Y%m%d"),
        )
        self.rwlock.release()

        command = (
            self.wget
            + " --no-check-certificate -O "
            + self.esgftmp
            + esgfpath
            + "/"
            + filename
            + ".tmp"
            " --secure-protocol=TLSv1 --certificate "
            + self.certs
            + " --private-key "
            + self.certs
            + " "
            + httppath
        )
        if os.path.isfile(self.esgftmp + esgfpath + "/" + filename + ".tmp"):
            return
        self.threadLimiter.acquire()
        process = Popen(command, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        all_res = process.communicate()[0]
        self.rwlock.acquire()
        with open(self.logpath + wgetlog, "a+") as f:
            f.write(all_res + "\n")
        self.rwlock.release()
        #                         if 'OpenSSL: error:' in line:
        #                             download.write('Certificate Error:\n')
        #                             download.write('URL: '+httppath+'\n')
        #                   print process.wait()

        if cmor_path["project"] == "specs":
            # os.rename(self.esgftmp+esgfpath+'/'+filename+'.tmp',self.esgftmp+esgfpath+'/'+filename)
            cdo.shifttime(
                "-365days",
                input="-selvar,"
                + cmor_path["variable"]
                + " "
                + self.esgftmp
                + esgfpath
                + "/"
                + filename
                + ".tmp",
                output=self.esgftmp + esgfpath + "/" + filename,
                options=" -O ",
            )
            os.remove(self.esgftmp + esgfpath + "/" + filename + ".tmp")
        else:
            os.rename(
                self.esgftmp + esgfpath + "/" + filename + ".tmp",
                self.esgftmp + esgfpath + "/" + filename,
            )
        os.remove(self.esgftmp + path + ".lock")
        self.threadLimiter.release()

    def getattr(self, path, fh=None):
        filepath, extension = os.path.splitext(path)
        st = dict(st_mode=(S_IFDIR | 0e0755), st_nlink=2)
        if extension == ".nc":
            try:
                self.threadLimiter.acquire()
                st = dict(
                    st_mode=(S_IFREG | 0e0444), st_size=self.get_url(path, True)[1]
                )
                self.threadLimiter.release()
            except TypeError:
                raise FuseOSError(ENETUNREACH, "Bla")
        st["st_ctime"] = st["st_mtime"] = st["st_atime"] = time()
        return st

    def open(self, path, fh):

        sleep(0.1)
        esgfpath, filename = os.path.split(path)
        try:
            with open(self.esgftmp + path) as testfile:
                pass
            return fh
        except IOError:
            pass

        self.rwlock.acquire()
        try:
            with open(self.esgftmp + path + ".lock") as testfile:
                pass
            self.rwlock.release()
        except IOError:
            try:
                os.makedirs(self.esgftmp + esgfpath, 0e0775)
            except OSError as exception:
                if exception.errno != errno.EEXIST:
                    raise
            self.download(esgfpath, path, filename)

        while True:
            sleep(5)
            if not os.path.isfile(self.esgftmp + path + ".lock"):
                if os.path.isfile(self.esgftmp + path):
                    break
        return fh

    #         sleep(0.1)
    #         # create directories recursively
    #         try:
    #             os.makedirs(self.esgftmp+esgfpath,0775)
    # #             [os.chown(dir, -1, 1000) for root, dirs, _ in os.walk(self.esgftmp+esgfpath) for dir in dirs]
    # #             [os.chmod(os.path.join(root,dir),S_IREAD|S_IWRITE|S_IRGRP|S_IWGRP) for root, dirs, _ in os.walk(self.esgftmp+esgfpath) for dir in dirs]
    #         except OSError as exception:
    #             if exception.errno != errno.EEXIST: raise
    #         try: # look for lock file - lock file = signal for download
    #                  with open(self.esgftmp+path+'.lock') as testfile:pass
    #                  sleep (.1)
    #                  self.open(path, fh)
    #         except IOError as e:
    #             try:
    #                 with open(self.esgftmp+path) as testfile: pass
    #                 return fh
    #             except IOError as e:
    #                 with self.rwlock:
    #                     self.download(esgfpath,path,filename)
    #                     return fh

    def read(self, path, length, offset, fh):
        with open(self.esgftmp + path) as f:
            f.seek(offset, 0)
            buf = f.read(length)
            f.close()
            return buf

    readdir = None
    access = None
    flush = None
    getxattr = None
    listxattr = None
    opendir = None
    releasedir = None
    statfs = None
    release = None
