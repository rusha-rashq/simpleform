import pulumi
import pulumi_aws as aws
import pulumi_gcp as gcp
import yaml

# 1. Load the User's Form
with open("simpleform.yaml", "r") as f:
    config = yaml.safe_load(f)

# 2. Regional Mapping Dictionary
REGION_MAP = {
    "us-east": {"aws": "us-east-1", "gcp": "us-east1"},
    "us-west": {"aws": "us-west-2", "gcp": "us-west1"},
    "europe": {"aws": "eu-central-1", "gcp": "europe-west3"},
}

# Extract settings for readability
settings = config.get("settings", {})
target_region = REGION_MAP.get(settings.get("region", "us-east"))
is_public = settings.get("public_access", False)
use_versioning = settings.get("versioning", False)

# 3. Logic for AWS
if config["cloud"] == "aws":
    # Set the region dynamically
    aws_provider = aws.Provider("aws-provider", region=target_region["aws"])

    bucket = aws.s3.Bucket(
        config["name"],
        acl="public-read" if is_public else "private",
        versioning=aws.s3.BucketVersioningArgs(
            enabled=use_versioning,
        ),
        opts=pulumi.ResourceOptions(provider=aws_provider),
    )

    pulumi.export("bucket_url", bucket.website_endpoint)
    pulumi.export("cloud_provider", "Amazon Web Services")

# 4. Logic for GCP
elif config["cloud"] == "gcp":
    bucket = gcp.storage.Bucket(
        config["name"],
        location=target_region["gcp"],
        versioning=gcp.storage.BucketVersioningArgs(
            enabled=use_versioning,
        ),
    )

    # If public, we need to add a special IAM binding
    if is_public:
        gcp.storage.BucketIAMMember(
            f"{config['name']}-public-access",
            bucket=bucket.name,
            role="roles/storage.objectViewer",
            member="allUsers",
        )

    pulumi.export("bucket_url", bucket.self_link)
    pulumi.export("cloud_provider", "Google Cloud Platform")
