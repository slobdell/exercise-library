import cv2
import os

from cStringIO import StringIO

from boto.s3.connection import S3Connection

AWS_S3_PARTIAL_URL = "https://%s.s3.amazonaws.com/%s"
TARGET_BUCKET = 'workout-generator-exercises'


def resized_frame(frame, desired_width):
    height, width = frame.shape[0: 2]
    desired_to_actual = float(desired_width) / width
    new_width = int(width * desired_to_actual)
    new_height = int(height * desired_to_actual)
    return cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)


class S3Client(object):

    _cls_cache = {}

    @classmethod
    def _get_bucket(cls, amazon_bucket_name):
        try:
            return cls._cls_cache[amazon_bucket_name]
        except KeyError:
            connection = S3Connection(os.environ['AWS_ACCESS_KEY_ID'],
                                      os.environ['AWS_SECRET_ACCESS_KEY'])
            cls._cls_cache[amazon_bucket_name] = connection.lookup(amazon_bucket_name)
            return cls._cls_cache[amazon_bucket_name]


class FileDownloader(S3Client):

    def __init__(self, aws_bucket_name):
        self.aws_bucket_name = aws_bucket_name

    def download_to_buffer(self, amazon_key):
        file_buffer = StringIO()
        bucket = self._get_bucket(self.aws_bucket_name)

        key = bucket.get_key(amazon_key)
        key.get_contents_to_file(file_buffer)
        file_buffer.seek(0)
        return file_buffer


class FileUploader(S3Client):

    def __init__(self, aws_bucket_name):
        self.aws_bucket_name = aws_bucket_name

    def _full_path(self, key):
        return AWS_S3_PARTIAL_URL % (self.aws_bucket_name, key.name)

    def upload(self, output_path, file_buffer):
        bucket = self._get_bucket(self.aws_bucket_name)
        key = bucket.new_key(output_path)
        key.set_contents_from_file(file_buffer)
        key.make_public()
        return self._full_path(key)


def generate_valid_frames(capture):
    while True:
        success, frame = capture.read()
        if not success:
            break
        yield frame


connection = S3Connection(os.environ['AWS_ACCESS_KEY_ID'],
                          os.environ['AWS_SECRET_ACCESS_KEY'])
bucket = connection.get_bucket(TARGET_BUCKET)
rs = bucket.list()


file_downloader = FileDownloader(TARGET_BUCKET)
file_uploader = FileUploader(TARGET_BUCKET)
for key in rs:
    if "smaller_mp4" in key.name and ".mp4" in key.name:
        file_buffer = file_downloader.download_to_buffer(key.name)
        with open("temp_file.mp4", "w+") as f:
            f.write(file_buffer.read())
        capture = cv2.VideoCapture("temp_file.mp4")
        all_frames = list(generate_valid_frames(capture))
        total_frames = len(all_frames)

        for desired_width in (100, 300):
            im1 = all_frames[total_frames / 3]
            im1 = resized_frame(im1, desired_width)

            im2 = all_frames[total_frames * 2 / 3]
            im2 = resized_frame(im2, desired_width)
            cv2.imwrite("im1.jpg", im1)
            cv2.imwrite("im2.jpg", im2)

            stripped_filename = key.name.split("/")[-1].split(".mp4")[0]
            with open("im1.jpg", "rb") as f:
                data_buffer = StringIO()
                data_buffer.write(f.read())
                data_buffer.seek(0)
                file_uploader.upload("thumbnails/1/%s/%s.jpg" % (desired_width, stripped_filename), data_buffer)

            with open("im2.jpg", "rb") as f:
                data_buffer = StringIO()
                data_buffer.write(f.read())
                data_buffer.seek(0)
                file_uploader.upload("thumbnails/2/%s/%s.jpg" % (desired_width, stripped_filename), data_buffer)

        print stripped_filename
        os.system("rm im1.jpg")
        os.system("rm im2.jpg")
        os.system("rm temp_file.mp4")
