import os
import subprocess

import questionary
import yaml


def run_cli():
    print("--- 🚀 Simpleform v1.0 CLI ---")

    # 1. Choose Action
    action = questionary.select(
        "What would you like to do?",
        choices=["Deploy New Infrastructure", "Destroy Existing Infrastructure"],
    ).ask()

    # Handle Destroy
    if action == "Destroy Existing Infrastructure":
        confirm = questionary.confirm(
            "⚠️ This will delete ALL resources in the current stack. Proceed?"
        ).ask()
        if confirm:
            env = os.environ.copy()
            print("🔥 Destroying infrastructure...")
            subprocess.run(["pulumi", "destroy", "--yes"], env=env)
        return

    # 2. Collect Intent for Deployment
    cloud = questionary.select("Which cloud provider?", choices=["aws", "gcp"]).ask()

    resource = questionary.select("Resource type?", choices=["bucket", "server"]).ask()

    name = questionary.text("Resource name:").ask()

    region = questionary.select(
        "Global region:", choices=["us-east", "us-west", "europe"]
    ).ask()

    settings = {"region": region}

    if resource == "bucket":
        settings["public_access"] = questionary.confirm("Public access?").ask()
        settings["versioning"] = questionary.confirm("Enable versioning?").ask()

    elif resource == "server":
        settings["size"] = questionary.select(
            "Server size:", choices=["small", "medium"]
        ).ask()

    # 3. Write YAML
    config = {"cloud": cloud, "resource": resource, "name": name, "settings": settings}
    with open("simpleform.yaml", "w") as f:
        yaml.dump(config, f)

    # 4. Deploy
    if questionary.confirm("Deploy now?").ask():
        env = os.environ.copy()
        subprocess.run(["pulumi", "up", "--yes"], env=env)


if __name__ == "__main__":
    run_cli()
