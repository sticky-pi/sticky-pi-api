import logging
import os
import PIL
import PIL.Image
import PIL.ExifTags
from imread import imread_from_blob
from ast import literal_eval
import datetime
from sticky_pi_api.utils import md5, URLOrFileOpen, STRING_DATETIME_FILENAME_FORMAT


class ImageParser(dict):


    _thumbnail_size = (512, 384)
    _thumbnail_mini_size = (128, 96)
    # _timezone = pytz.timezone("UTC")
    _time_origin = datetime.datetime(2019, 11, 1)

    # the api name of metadata variables in the C-made images
    _headers_description_2022 = {
        'v': ("device_version", str),
        'T': ("temp", float),
        'H': ("hum", float),
        'B': ("bat", float), # todo ADD TO DB
        'L':("lum", float),
        'lat': ("lat", float),
        'lng':("lng", float),
        'a': ("alt", float),
        # 'l':("last_sync", float), # NOT USED IN DB
        'b': ("but", lambda x: bool(int(x)))  # todo button  ADD TO DB
    }

    def __init__(self, file):
        """
        A class derived from dict that contains image metadata in its fields.
        It parses data from an input JPEG image file taken by a Sticky Pi and retrieves its metadata
        from filename an exif fields. In addition, it computes md5 sum and generate thumbnails for the input image.
        :param file: path to file  or file like object
        """
        super().__init__()
        if type(file) == str:
            with URLOrFileOpen(file, 'rb') as f:
                self._parse(f)
        elif hasattr(file, 'read'):
            self._parse(file)
        else:
            raise TypeError('Unexpected type for file. Should be either a path or a file-like. file is %s' % type(file))


    def _device_datetime_info(self, filename):
        """
        Parse device id and datetime from the image filename.

        :param name: something like 7168f343.2019-11-27_20-57-22.jpg"
        :type name: str
        :return: {'device': str,
                'datetime': datetime.datetime(),
                'filename': str}
        :rtype: ()
        """
        fields = filename.split('.')

        if len(fields) != 3:
            raise Exception("Wrong file name: %s. Three dot-separated fields expected." % filename)

        device = fields[0]
        try:
            if len(device) != 8:
                raise ValueError()
            int(device, base=16)
        except ValueError:
            raise Exception("Invalid device name field in file: %s" % device)

        datetime_string = fields[1]
        try:
            date_time = datetime.datetime.strptime(datetime_string, STRING_DATETIME_FILENAME_FORMAT)
            # date_time = self._timezone.localize(date_time)
        except ValueError:
            raise Exception("Could not retrieve datetime from filename")

        if date_time < self._time_origin:
            raise Exception("Image taken before the platform even existed")


        return {'device': device,
                'datetime': date_time,
                'filename': filename}

    def _parse(self, file):

        self._filename = os.path.basename(file.name)
        self.update(self._device_datetime_info(self._filename))
        self['md5'] = md5(file)
        # ensure the image is a jpeg
        try:
            self._file_blob = file.read()

            imread_from_blob(self._file_blob, 'jpg')

            with PIL.Image.open(file) as img:
                exif_fields = {
                    PIL.ExifTags.TAGS[k]: v
                    for k, v in img._getexif().items()
                    if k in PIL.ExifTags.TAGS
                }

                self['width'] = img.width
                self['height'] = img.height

                img.thumbnail(self._thumbnail_size)
                self._thumbnail = img.copy()
                img.thumbnail(self._thumbnail_mini_size)
                self._thumbnail_mini = img.copy()
                try:
                    custom_img_metadata = literal_eval(exif_fields['Make'])
                    logging.warning(f"Parsing legacy image {self._filename}")


                    # gps data not available -> None
                    if custom_img_metadata['lat'] == 0 and custom_img_metadata['lng'] == 0 and custom_img_metadata['alt'] == 0:
                        custom_img_metadata['lat'] = custom_img_metadata['lng'] = custom_img_metadata['alt'] = None


                    # in the legacy images (2020), we have different metavariables to assess brightness
                    # here, we adapt the old to the new data format
                    # these variables are expressed as a fractional tuple. We cast them to floats
                    if "no_flash_bv" in custom_img_metadata.keys():
                        for var in ["no_flash_" + v for v in ("shutter_speed", "exposure_time", "bv")]:
                            custom_img_metadata[var] = custom_img_metadata[var][0] / \
                                                                custom_img_metadata[var][1]
                        custom_img_metadata["no_flash_analog_gain"] = custom_img_metadata["no_flash_iso"]
                        custom_img_metadata["no_flash_digital_gain"] = custom_img_metadata["no_flash_bv"]
                        del custom_img_metadata["no_flash_iso"]
                        del custom_img_metadata["no_flash_bv"]
                        del custom_img_metadata["no_flash_shutter_speed"]
                        del custom_img_metadata['datetime']

                except ValueError:
                    custom_img_metadata = {}
                    metadata = exif_fields["UserComment"].decode()
                    lines = metadata.split("\n")
                    assert len(lines) == 2, "Metadata should have exactly two lines"
                    headers = lines[0].split(',')
                    values = lines[1].split(',')

                    metadata_dict = {k: v for k, v in zip(headers, values)}

                    for k, v in metadata_dict.items():
                        if k in self._headers_description_2022:
                            name, parser = self._headers_description_2022[k]
                            custom_img_metadata[name] = parser(v)

                self.update(custom_img_metadata)

        finally:
            file.seek(0)

    @property
    def file_blob(self):
        return self._file_blob

    @property
    def filename(self):
        return self._filename

    @property
    def thumbnail(self):
        return self._thumbnail

    @property
    def thumbnail_mini(self):
        return self._thumbnail_mini
