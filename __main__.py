import pulumi
import pulumi_aws as aws
import pulumi_gcp as gcp
import yaml

# 1. Load your 'Form'
with open("simpleform.yaml", "r") as f:
    config = yaml.safe_load(f)

target_cloud = config.get("cloud", "aws").lower()
res_name = config.get("name", "simple-res")

# 2. The Simpleform Translation Engine
if config.get("resource") == "bucket":
    if target_cloud == "aws":
        # Maps generic 'bucket' to AWS S3
        bucket = aws.s3.Bucket(res_name)
        pulumi.export("bucket_id", bucket.id)
        pulumi.export("provider", "Amazon Web Services")

    elif target_cloud == "gcp":
        # Maps generic 'bucket' to GCP Storage
        # We'll hardcode 'US' for the MVP today
        bucket = gcp.storage.Bucket(res_name, location="US")
        pulumi.export("bucket_id", bucket.name)
        pulumi.export("provider", "Google Cloud Platform")
