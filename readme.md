# Customer Package Freshness Checker

`./freshness_checker.py` example script helps Customer track the freshness of packages (Maven, NPM, Python) during migration from Nexus to Cloudsmith. It addresses the concern that during migration, the `uploadDate` of packages cached from upstream might be set to the current date, which would override the actual upload date from the upstream and falsely report that packages are "fresher" than they should be.

* Flow diagram explaining scenarios https://app.excalidraw.com/s/7aJ5mIbtXrP/8qSC4ceSRjE

## Problem Statement

During migration to Cloudsmith, Packages cached in Cloudsmith from Nexus upstream will override publish date, resulting in the incorrect package freshness dates, indicating that the packages in Cloudsmith cached from Nexus are built more recently than they trully are

The solution implemented here allows for proper tracking of package freshness by:
1. Querying Nexus for all versionless packages (Customer does this in the current package freshness check)
2. Querying Nexus for `uploadDate` for a versionless package (Customer does this in the current package freshness check)
3. Querying Cloudsmith for `uploadDate` for the same versionless package EXCLUDING package versions cached from the Nexus (using `NOT tag:nexus-upstream`). This will return `uploadDate` of a packages only pushed to Cloudsmith (e.g. `uploadDate` represents correct build date for a package)
4. Taking the later of the two dates from Nexus and Cloudsmith as the true freshness date for a package group (versionless package)


After the freshness period has passed during the migration (90 days?), Step 1 would need to include union of all versionless packages coming from Nexus AND coming from Cloudsmith (example given in the `CloudsmithClient.list_package_groups` method) to make sure that the new packages published only in Cloudsmith but not in Nexus are taken into account

## Setup

1. Create a Python virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure your environment:
   - Copy the `.env` file and fill in your Cloudsmith API key:
   ```
   cp .env.example .env
   # Edit .env with your details
   ```

## Usage

```bash
# Check all packages from both Nexus and Cloudsmith
python freshness_checker.py

# Specify tags to exclude (default is "upstream")
python freshness_checker.py --upstream-tag-to-exclude nexus-upstream
```

### Quick Demo

We've provided a demo script to quickly show how the solution works:

```bash
./run_demo.sh
```

This will:
1. Set up a virtual environment
2. Install dependencies
3. Run the example code
4. Run the main freshness checker


## Implementation Details

### Nexus Client

The `NexusClient` class provides functionality to:
- List all package groups in Nexus (supports Maven, NPM, and Python as per the script's capabilities).
- Retrieve the `lastUpdated` date for each package group (e.g., from `maven-metadata.xml` for Maven packages).

Data from `NexusClient` is mocked in `./fixtures/{format}/packages.json`. This is a showcase implementation. In a production implementation, Customer would replace it by existing script that parses the HTML index

### Cloudsmith Client

The `CloudsmithClient` class provides functionality to:
- `get_last_updated_date` method - Retrieves the `last_push` (`uploadedAt`) date for each package group (versionless package), with the ability to exclude packages with specific tags. e.g. This can give you last push date for a package group `com.google.guava:guava` for a group of packages only pushed to Cloudsmith (excluding the ones cached from Nexus upstream)
- `list_package_groups` method - List all unique package groups (versionless package) in Cloudsmith per format (maven, npm, python)

### Freshness Calculation

For each package group, the script:
1. Retrieves the lastUpdated date from Nexus
2. Retrieves the uploadedAt date from Cloudsmith (if available), excluding packages with specified upstream nexus tag
3. Takes the later of the two dates as the true freshness date
