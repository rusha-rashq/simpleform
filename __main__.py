import pulumi
import pulumi_aws as aws
import pulumi_gcp as gcp
import yaml

# --- 1. GLOBALS & MAPPINGS ---
VM_SIZES = {
    "small": {"aws": "t3.micro", "gcp": "e2-micro"},
    "medium": {"aws": "t3.medium", "gcp": "e2-medium"},
}

vm_startup_script = """#!/bin/bash
echo "Simpleform v1.2: Full Stack Networking & Compute Live" > index.html
nohup python3 -m http.server 80 &
"""

REGION_MAP = {
    "us-east": {"aws": "us-east-1", "gcp": "us-east1"},
    "us-west": {"aws": "us-west-2", "gcp": "us-west1"},
    "europe": {"aws": "eu-central-1", "gcp": "europe-west3"},
}

with open("simpleform.yaml", "r") as f:
    config = yaml.safe_load(f)

settings = config.get("settings", {})
target_region = REGION_MAP.get(settings.get("region", "us-east"))
is_public = settings.get("public_access", False)
use_versioning = settings.get("versioning", False)

# --- 2. AWS DYNAMIC IMAGE DISCOVERY ---
ubuntu_ami = aws.ec2.get_ami(
    most_recent=True,
    filters=[
        {
            "name": "name",
            "values": ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"],
        },
        {"name": "virtualization-type", "values": ["hvm"]},
    ],
    owners=["099720109477"],
)

# --- 3. INFRASTRUCTURE ENGINE ---

# MODULE A: STORAGE (Buckets, ACLs, Ownership, Public Access Blocks)
if config["resource"] == "bucket":
    if config["cloud"] == "aws":
        bucket = aws.s3.Bucket(
            config["name"],
            versioning=aws.s3.BucketVersioningArgs(enabled=use_versioning),
        )

        ownership = aws.s3.BucketOwnershipControls(
            f"{config['name']}-oc",
            bucket=bucket.id,
            rule={"object_ownership": "BucketOwnerPreferred"},
        )

        pab = aws.s3.BucketPublicAccessBlock(
            f"{config['name']}-pab",
            bucket=bucket.id,
            block_public_acls=False,
            block_public_policy=False,
            ignore_public_acls=False,
            restrict_public_buckets=False,
        )

        if is_public:
            aws.s3.BucketAclV2(
                f"{config['name']}-acl",
                bucket=bucket.id,
                acl="public-read",
                opts=pulumi.ResourceOptions(depends_on=[ownership, pab]),
            )

        pulumi.export("bucket_endpoint", bucket.bucket_regional_domain_name)

    elif config["cloud"] == "gcp":
        bucket = gcp.storage.Bucket(
            config["name"],
            location=target_region["gcp"],
            versioning=gcp.storage.BucketVersioningArgs(enabled=use_versioning),
        )
        if is_public:
            gcp.storage.BucketIAMMember(
                f"{config['name']}-iam",
                bucket=bucket.name,
                role="roles/storage.objectViewer",
                member="allUsers",
            )
        pulumi.export("bucket_url", bucket.self_link)

# MODULE B: COMPUTE & NETWORKING (VPC, Subnets, IGW, Route Tables, Firewalls, VMs)
elif config["resource"] == "server":
    if config["cloud"] == "aws":
        # Network Foundation
        vpc = aws.ec2.Vpc(
            f"{config['name']}-vpc", cidr_block="10.0.0.0/16", enable_dns_hostnames=True
        )
        igw = aws.ec2.InternetGateway(f"{config['name']}-igw", vpc_id=vpc.id)
        subnet = aws.ec2.Subnet(
            f"{config['name']}-sn",
            vpc_id=vpc.id,
            cidr_block="10.0.1.0/24",
            map_public_ip_on_launch=True,
        )

        # Routing Logic
        rt = aws.ec2.RouteTable(
            f"{config['name']}-rt",
            vpc_id=vpc.id,
            routes=[{"cidr_block": "0.0.0.0/0", "gateway_id": igw.id}],
        )
        aws.ec2.RouteTableAssociation(
            f"{config['name']}-rta", subnet_id=subnet.id, route_table_id=rt.id
        )

        # Security (The Firewall/SG)
        sg = aws.ec2.SecurityGroup(
            f"{config['name']}-sg",
            vpc_id=vpc.id,
            ingress=[
                {
                    "protocol": "tcp",
                    "from_port": 80,
                    "to_port": 80,
                    "cidr_blocks": ["0.0.0.0/0"],
                }
            ],
        )

        # The Compute Instance
        server = aws.ec2.Instance(
            config["name"],
            instance_type=VM_SIZES[settings.get("size", "small")]["aws"],
            ami=ubuntu_ami.id,
            subnet_id=subnet.id,
            vpc_security_group_ids=[sg.id],
            user_data=vm_startup_script,
        )

        pulumi.export("server_ip", server.public_ip)
        pulumi.export("vpc_id", vpc.id)

    elif config["cloud"] == "gcp":
        # Network Foundation
        network = gcp.compute.Network(
            f"{config['name']}-vpc", auto_create_subnetworks=False
        )
        subnet = gcp.compute.Subnetwork(
            f"{config['name']}-sn",
            ip_cidr_range="10.0.1.0/24",
            network=network.id,
            region=target_region["gcp"],
        )

        # Security (Firewall)
        fw = gcp.compute.Firewall(
            f"{config['name']}-fw",
            network=network.name,
            allows=[{"protocol": "tcp", "ports": ["80"]}],
            source_ranges=["0.0.0.0/0"],
        )

        # The Compute Instance
        server = gcp.compute.Instance(
            config["name"],
            machine_type=VM_SIZES[settings.get("size", "small")]["gcp"],
            boot_disk={"initializeParams": {"image": "debian-cloud/debian-11"}},
            network_interfaces=[{"subnetwork": subnet.id, "accessConfigs": [{}]}],
            metadata_startup_script=vm_startup_script,
        )

        pulumi.export(
            "server_ip", server.network_interfaces[0]["accessConfigs"][0]["natIp"]
        )

pulumi.export("provider", config["cloud"])
