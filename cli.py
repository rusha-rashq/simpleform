import subprocess

import questionary
import yaml


def run_cli():
    # 1. Collect User Intent
    cloud = questionary.select(
        "Which cloud provider do you want to use?", choices=["aws", "gcp"]
    ).ask()

    resource = questionary.select(
        "What resource are you deploying?", choices=["bucket", "server"]
    ).ask()

    name = questionary.text("Give your resource a name:").ask()

    region = questionary.select(
        "Select a global region:", choices=["us-east", "us-west", "europe"]
    ).ask()

    # 2. Bucket-Specific Settings
    settings = {"region": region}
    if resource == "bucket":
        public = questionary.confirm("Should this bucket be public?").ask()
        versioning = questionary.confirm("Enable versioning for data safety?").ask()
        settings["public_access"] = public
        settings["versioning"] = versioning

    # 3. Server-Specific Settings
    elif resource == "server":
        size = questionary.select(
            "What size server?", choices=["small", "medium"]
        ).ask()
        settings["size"] = size

    # 4. Write the YAML File
    config = {"cloud": cloud, "resource": resource, "name": name, "settings": settings}

    with open("simpleform.yaml", "w") as f:
        yaml.dump(config, f)

    print(f"\n✅ Configuration saved to simpleform.yaml for {cloud}!")

    # 5. Trigger Pulumi
    if questionary.confirm("Do you want to deploy this now?").ask():
        subprocess.run(["pulumi", "up"])


if __name__ == "__main__":
    run_cli()
