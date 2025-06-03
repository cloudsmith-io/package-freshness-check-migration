#!/usr/bin/env python3
"""
Indeed Package Freshness Implementation Guide

This script provides a step-by-step guide for implementing the freshness
check solution in Indeed's environment.
"""

import os
import sys
from colorama import init, Fore, Style


def print_header(text):
    """Print a header with color."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}")
    print("-" * len(text))


def print_step(number, title):
    """Print a step with color."""
    print(f"\n{Fore.GREEN}{Style.BRIGHT}Step {number}: {title}{Style.RESET_ALL}")


def print_code(code):
    """Print code with color."""
    print(f"{Fore.YELLOW}{code}{Style.RESET_ALL}")


def main():
    """Main function showing the implementation guide."""
    init()  # Initialize colorama
    
    print_header("INDEED PACKAGE FRESHNESS IMPLEMENTATION GUIDE")
    print("""
This guide will help you implement the freshness check solution in your Indeed environment.
The solution addresses the concern about package freshness during migration from Nexus to Cloudsmith.
""")
    
    print_step(1, "Configure your environment")
    print("""
Create a .env file with your Nexus and Cloudsmith credentials:
""")
    print_code("""
NEXUS_BASE_URL=https://nexus.corp.indeed.com
CLOUDSMITH_BASE_URL=https://api.cloudsmith.io
CLOUDSMITH_API_KEY=your_api_key_here
CLOUDSMITH_ORG=indeed
CLOUDSMITH_REPO=maven-repo
""")
    
    print_step(2, "Tag packages cached from Nexus")
    print("""
Ensure that packages cached from Nexus in Cloudsmith are tagged with 'nexus-upstream'.
This can be done during the migration process or afterward using Cloudsmith's API.

Example API call to tag a package:
""")
    print_code("""
curl -X PUT \\
  "${CLOUDSMITH_BASE_URL}/v1/orgs/${CLOUDSMITH_ORG}/repos/${CLOUDSMITH_REPO}/packages/${PACKAGE_ID}/tags/nexus-upstream/" \\
  -H "X-Api-Key: ${CLOUDSMITH_API_KEY}" \\
  -H "Content-Type: application/json"
""")

    print_step(3, "Integrate the freshness checker into your workflow")
    print("""
Modify your existing freshness check script to use this new solution:

1. During the migration period (before fully migrating to Cloudsmith):
   - Check both Nexus and Cloudsmith for the lastUpdated date
   - Use the later of the two dates as the freshness date

2. After fully migrating to Cloudsmith:
   - Only check Cloudsmith, but exclude packages with the 'nexus-upstream' tag
   - This ensures accurate freshness reporting for packages cached from Nexus
""")
    
    print_step(4, "Run the freshness check")
    print("""
Run the freshness check script with appropriate options:
""")
    print_code("""
# During migration period
./freshness_checker.py --exclude-tag nexus-upstream --output-csv results.csv

# After full migration to Cloudsmith
./freshness_checker.py --cloudsmith-only --exclude-tag nexus-upstream --output-csv results.csv
""")
    
    print_step(5, "Interpret the results")
    print("""
The script outputs a CSV file with the following information for each package:
- groupId: The Maven group ID
- artifactId: The Maven artifact ID
- nexus_date: The lastUpdated date from Nexus
- cloudsmith_date: The uploadedAt date from Cloudsmith (excluding tagged packages)
- freshness_date: The date used for freshness calculation (later of the two)
- source: The source of the freshness date (Nexus or Cloudsmith)

You can use this information to:
1. Report on package freshness
2. Identify packages that haven't been updated in a long time
3. Track the progress of your migration from Nexus to Cloudsmith
""")
    
    print_header("IMPLEMENTATION TIPS")
    print("""
1. Schedule the freshness check to run regularly (e.g., daily)
2. Store the results in a database for historical tracking
3. Set up alerts for packages that haven't been updated in X days
4. Consider expanding the solution to other package formats (npm, Python)
5. After the full migration to Cloudsmith and X days have passed (where X is your
   freshness threshold), you can simplify the solution to only check Cloudsmith
""")
    
    print_header("NEXT STEPS")
    print("""
1. Test the solution in your development environment
2. Verify that the freshness dates are accurate
3. Deploy the solution to your production environment
4. Monitor the results during the migration period
5. Update your existing dashboards and alerts to use the new freshness data
""")


if __name__ == "__main__":
    main()
