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
    # 1. Create the Bucket
    bucket = aws.s3.Bucket(
        config["name"],
        versioning=aws.s3.BucketVersioningArgs(
            enabled=use_versioning,
        ),
    )

    # 2. Fix the Ownership (Allows ACLs to work)
    ownership = aws.s3.BucketOwnershipControls(
        f"{config['name']}-ownership",
        bucket=bucket.id,
        rule={"object_ownership": "BucketOwnerPreferred"},
    )

    # 3. Disable the "Block Public Access" (Allows public buckets)
    public_access_block = aws.s3.BucketPublicAccessBlock(
        f"{config['name']}-pab",
        bucket=bucket.id,
        block_public_acls=False,
        block_public_policy=False,
        ignore_public_acls=False,
        restrict_public_buckets=False,
    )

    # 4. Set the ACL only AFTER ownership and public access are configured
    if is_public:
        bucket_acl = aws.s3.BucketAclV2(
            f"{config['name']}-acl",
            bucket=bucket.id,
            acl="public-read",
            opts=pulumi.ResourceOptions(depends_on=[ownership, public_access_block]),
        )

    pulumi.export(
        "bucket_url", bucket.id.apply(lambda id: f"https://{id}.s3.amazonaws.com")
    )
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
