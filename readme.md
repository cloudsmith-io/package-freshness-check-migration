# Indeed Package Freshness Checker

This tool helps Indeed track the freshness of packages (Maven, NPM, Python) during migration from Nexus to Cloudsmith. It addresses the concern that during migration, the `uploadDate` of packages cached from upstream might be set to the current date, which would override the actual upload date from the upstream and falsely report that packages are "fresher" than they should be.

## Problem Statement

During migration to Cloudsmith, there are several scenarios where package freshness dates might be incorrectly reported:

1. Package exists only in Nexus (not yet cached in Cloudsmith)
2. Package exists only in Cloudsmith (newly uploaded)
3. Package is cached in Cloudsmith from Nexus upstream
4. Package exists in both Cloudsmith (local) and Nexus, with local being newer
5. Package exists in both Cloudsmith (local) and Nexus, with Nexus being newer

The solution implemented here allows for proper tracking of package freshness by:
- Querying both Nexus and Cloudsmith for package information
- Excluding packages with specific tags (e.g., "nexus-upstream") from freshness calculation
- Taking the later of the two dates from Nexus and Cloudsmith as the true freshness date

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

# Check only packages in Nexus
python freshness_checker.py --nexus-only

# Check only packages in Cloudsmith
python freshness_checker.py --cloudsmith-only

# Specify tags to exclude (default is "nexus-upstream")
python freshness_checker.py --exclude-tag nexus-upstream --exclude-tag another-tag

# Output results to CSV
python freshness_checker.py --output-csv results.csv
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

## Examples

The `examples` directory contains sample scripts demonstrating different aspects of the freshness checker:

### Basic Usage Example

```bash
python examples/usage_example.py
```

This shows a simple usage of the freshness checker API.

### Maven-specific Example

```bash
python examples/maven_example.py
```

This demonstrates how the freshness checker works specifically with Maven packages, including:
- The structure of maven-metadata.xml files
- How lastUpdated dates are extracted
- Handling of Nexus vs. Cloudsmith dates for Maven packages

## Implementation Guide

To help you implement this solution in your environment, we've provided an implementation guide:

```bash
python implementation_guide.py
```

This guide provides step-by-step instructions for:
- Configuring your environment
- Tagging packages cached from Nexus
- Integrating the freshness checker into your workflow
- Running the freshness check
- Interpreting the results

## Testing

Run the tests to ensure everything is working properly:

```bash
python -m pytest test_freshness_checker.py
```

## Implementation Details

### Nexus Client

The `NexusClient` class provides functionality to:
- List all Maven package groups in Nexus
- Retrieve the `lastUpdated` date from maven-metadata.xml for each package group

For testing purposes, it uses mocked data. In a production implementation, it would parse the HTML index or use the Nexus API.

### Cloudsmith Client

The `CloudsmithClient` class provides functionality to:
- List all Maven package groups in Cloudsmith
- Retrieve the `uploadedAt` date for each package group, with the ability to exclude packages with specific tags

### Freshness Calculation

For each package group, the script:
1. Retrieves the lastUpdated date from Nexus (if available)
2. Retrieves the uploadedAt date from Cloudsmith (if available), excluding packages with specified tags
3. Takes the later of the two dates as the true freshness date

