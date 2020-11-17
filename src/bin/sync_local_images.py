#! /usr/bin/python


from sticky_pi.sync_to_remote import SyncTool
from sticky_pi.api import StickyPiAPI
import getpass
import logging
import shutil
from optparse import OptionParser
import os
import psutil

def drive_valid_content(dir):

    for sd in os.listdir(dir):
        if not sd.startswith('.') and os.path.isdir(sd):
            try:
                int(sd, base=16)
                if len(sd) != 8:
                    raise ValueError
            except ValueError:
                logging.debug("%s is not a regular device name. does not look like the sticky pi drive!" % sd)
                return False
    return True


def get_dev_label(path):
    devs = {}
    for lab in os.listdir('/dev/disk/by-label'):
        link = os.readlink( os.path.join('/dev/disk/by-label/', lab))
        abs_dev_path = os.path.normpath(os.path.join('/dev/disk/by-label/', link))
        devs[abs_dev_path] = lab
    return devs[path]

def get_thumbdrive_dir(drive_label = 'SPI_DRIVE'):

    valid = []

    for p in psutil.disk_partitions():
        if p.fstype == 'vfat':
            try:
                label = get_dev_label(p.device)
                if label == drive_label:
                    valid.append(p)
            except Exception as e:
                logging.warning("Unable to look at disk label. Will infer disk from content")
                logging.warning(e)
                if drive_valid_content(p.mountpoint):
                    valid.append(p)
    if len(valid) == 0:
        raise Exception("No valid sticky pi drive detected")
    if len(valid) > 1:
        raise Exception("Multiple/ambiguous valid devices!")
    logging.info("Found device %s. Syncing from device to client dir" % valid[0].mountpoint)
    return valid[0].mountpoint


def copy_im_file(origin, target, api):
    if not os.path.exists(target):
        return True
    md5_o = api.cached_md5(origin)
    md5_t = api.cached_md5(target)
    if md5_o != md5_t:
        logging.warning('%s and %s have different md5! but should be the same file' % (origin, target))
        from sticky_pi.image import Image
        ori_valid = True
        target_valid = True
        try:
            _ = Image(origin).read()
        except Exception as e:
            logging.warning(e)
            ori_valid = False

        try:
            _ = Image(target).read()
        except Exception as e:
            logging.warning(e)
            target_valid = False
        if not target_valid and ori_valid:
            logging.warning('Only the thumbdrive image seems valid. Overwriting client image')
            return True
        if target_valid and not ori_valid:
            logging.warning('The thumbdrive image does not open, but the client one does! Corrupted thumbdrive?')
        if not target_valid and not ori_valid:
            logging.warning('Neither images open')
    return False

def mirror_im_dir(origin, target, api):

    import tempfile

    for f in sorted(os.listdir(origin)):
        if os.path.isdir(os.path.join(origin,f)):
            if f.startswith('.'):
                continue
            try:
                int(f, base=16)
            except ValueError:
                logging.warning('Skipping irregular directory %s in thumbdrive' % f)
            for im in sorted(os.listdir(os.path.join(origin, f))):
                if im.endswith('.jpg'):
                    full_im_path = os.path.join(origin, f, im)
                    full_im_target_path = os.path.join(target, f, im)
                    target_dir = os.path.dirname(full_im_target_path)
                    tmp_im_path = ""
                    logging.info('%s -> %s' % (full_im_path, full_im_target_path))
                    if copy_im_file(full_im_path, full_im_target_path, api):
                        if not os.path.isdir(target_dir):
                            os.mkdir(target_dir)
                        try:
                            tmp_im_path = tempfile.mktemp(prefix='.tmp_', suffix='.jpg', dir=target)
                            shutil.copy(full_im_path, tmp_im_path)
                            shutil.move(tmp_im_path, full_im_target_path)
                            logging.info(tmp_im_path)
                        finally:
                            if os.path.exists(tmp_im_path):
                                os.remove(tmp_im_path)

if __name__ == "__main__":

    parser = OptionParser()

    parser.add_option("-t", "--from-thumbdrive",
                      dest="from_thumbdrive",
                      help="Look for a drive named SPI_DRIVE, "
                            "and sync images from it to client dir",
                      default=False,
                      action='store_true')

    parser.add_option("-T", "--thumbdrive-dir",
                      dest="thumbdrive_dir",
                      help="Used in addition to `-t`. "
                            "The path where the drive is mounted."
                           "This is in case it cannot be discovered automatically",
                      default=None)

    parser.add_option("-d", "--directory", dest="directory", help="the sticky pi root directory",
                      )

    parser.add_option("-u", "--username", dest="username", help="username on server",
                      )
    parser.add_option("-w", "--host", dest="host", help="API host e.g. 'my.api.net'",
                      )

    parser.add_option("-k", "--protocol", dest="protocol", default='https', help="http or https",
                      )

    parser.add_option("-p", "--port", dest="port", default='443', help="API port",
                      )
    parser.add_option("-z", "--password", dest="password", default=None, help="Password. if not provided, will be prompted",
    )
    parser.add_option("-n", "--n-threads", dest="n_threads", default=1,
                      help="Number of parallel jobs",
                      )

    parser.add_option("-v", "--verbose", dest="verbose", default=False,
                      help="verbose",
                      action="store_true")

    parser.add_option("-D", "--debug", dest="debug", default=False,
                      help="show debug info",
                      action="store_true")

    parser.add_option("-s", "--skip-errors", dest="skip_errors", default=False,
                      help="show debug info",
                      action="store_true")
    parser.add_option("--delete-cache", dest="skip_errors", default=False,
                      help="show debug info",
                      action="store_true")

    (options, args) = parser.parse_args()
    option_dict = vars(options)

    if option_dict['verbose']:
        logging.getLogger().setLevel(logging.INFO)

    if option_dict['debug']:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("DEBUG mode ON")

    if not os.path.exists(option_dict['directory']):
        raise Exception('No such directory: %s' % option_dict['directory'])

    if option_dict['password']:
        password =  option_dict['password']
    else:
         password = getpass.getpass()

    api = StickyPiAPI(option_dict['host'],
                      option_dict['username'],
                      password,
                      protocol=option_dict['protocol'],
                      port=int(option_dict['port']),
                      sticky_pi_dir=option_dict['directory']
                      )

    if option_dict['from_thumbdrive']:
        if option_dict['thumbdrive_dir'] is None:
            t_dir = get_thumbdrive_dir()
        else:
            t_dir = option_dict['thumbdrive_dir']
            assert os.path.isdir(t_dir)

        target_dir = os.path.join(option_dict['directory'], 'raw_images')
        if not os.path.exists(target_dir):
            logging.info('% does not exist. Creating it. First time fetching data from thumbdrive?')
            os.mkdir(target_dir)

        mirror_im_dir(t_dir, target_dir, api)

    st = SyncTool(option_dict['directory'],
                  api,
                  n_threads=int(option_dict['n_threads']),
                  skip_errors=option_dict['skip_errors'])
    st.sync_all()

# sync_local_images.py  -d ~/sticky_pi_root/ -u quentin -w api.sticky_pi_api.computational-entomology.net -k http -v
