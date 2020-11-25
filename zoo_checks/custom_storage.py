from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorageS3(S3Boto3Storage):
    """Custom S3 Storage
    Note: not used unless set S3_MEDIA setting
    """

    bucket_name = "zootable-na"
    default_acl = "private"
    location = "media"
