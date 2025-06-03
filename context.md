# Indeed Package freshness - vibe coding

## Context

Indeed is periodically fetching data for “freshness” of each version-less package (They called it that, it is a Package group in Cloudsmith terminology). If it is older than X amount of days, it raises an event/alarm. They do this for:

- Maven (biggest worry)
- npm (correct me if wrong)
- python (correct me if wrong)

They are worried that during the migration to Cloudsmith, `uploadDate` of the package cached from upstream will be set to the current date, which will override `uploadDate` from the upstream and report that the packages fetched from the upstream are “fresher” than supposed to be. Biggest worry is the migration period, once they fully migrate to Cloudsmith and X amount of days have passed, this problem should not exist

- notes and sources for the context
    
    ```python
    Right now we’re using https://nexus.corp.indeed.com/service/rest/repository/browse/maven-hosted/ in Nexus, it’s basically an HTML index of the maven tree. Though if they have a meaningful API that responds reliably and can give us the basically the data in a maven-metadata.xml file it pretty much covers our need .
    ```
    
    Information [from Carl’s message](https://cloudsmith-io.slack.com/archives/C07MX9RRB36/p1734716167461899?thread_ts=1734113231.348739&cid=C07MX9RRB36):
    
    - “gather all of the libraries and applications we build and publish”
    - date of the latest publish
        - Q: Per package or package group? Group makes more sense
    - the highest published version
    - internal metadata
    
    Need:
    
    - what percentage of team X's libraries are fresh,  published with new dependencies within the last X days
    - "what libraries haven't had their dependencies updated in a long time”
    
    [Per this message](https://cloudsmith-io.slack.com/archives/C07MX9RRB36/p1736179542167839?thread_ts=1734113231.348739&cid=C07MX9RRB36), it seems it is not per package data that they require, but per package group
    
    - What we need is a list of all libraries (i.e. groupId:artifactId .. we generally call it a versionless coordinate ) that are published in the maven repository. From that, everything else is pretty easy and anything that looks like a maven repo works.
    

## Assumption

- Indeed’s Cloudsmith Repository has their Nexus as an upstream (i.e. that artifacts will be sourced/migrated via upstreams)
- Nexus repository has upstreams
- Cloudsmith’s repository DOESN’T have the same (conflicting) upstreams as Nexus
- For simplicity sake, let’s assume there won’t be other upstreams except for Nexus
- Maven is JIT
- Scoping the issue for Maven, with potential expansion to other formats

## Scenarios

Legend:

- CS-repo: local package
    - Cloudsmith Repository - locally pushed packages
    - In the scenarios, indicates latest `uploadedAt` date for a package group (versionless package) of packages that were pushed to Cloudsmith
- Nexus repo
    - In the scenarios, indicates `uploadedAt` date for a package group (versionless package) in Nexus repository that Indeed is using today, they are consuming `maven-metadata.xml` file on GA index, [example file on mavencentral](https://repo1.maven.org/maven2/junit/junit/maven-metadata.xml)
- CS-repo: Cached Nexus upstream package
    - Cloudsmith Repository - Packages cached from the Nexus upstream
    - indicates latest `uploadedAt` date for a package group (versionless package) of packages that cached from the Nexus Upstream. If a package `junit:4.1.2` is proxied and cached, once the package is cached we will create a local package from the upstream. Once the upstream indexing is done (triggered every 2 hrs), we will fetch all versions of `junit` from upstream (but not sync them), which will impact `uploadedAt` date. After that, once a new version of `junit` is released, upstream indexing will reset `uploadedAt` date
- Expected last updated
    - This is our assumption what Indeed will expect as `uploadedAt` date for a package group, to make sure their freshness check is working as expected when consuming ONLY from Cloudsmith API
- Cloudsmith GA maven-metadata.xml returns
    - `lastUpdated`  in GA `maven-metadata.xml` returned from Cloudsmith is set at a time when the metadata was generated, and as it is cached in application cache (that has short TTL), and it is a dynamic file (doesn’t exist, generated on the fly), so this date keeps increasing over time and it will not show the values like Nexus. It will indicate false freshness for Indeed. By specification, we are not doing anything wrong, but it will impact Indeed’s date freshness and if they are going to use it from CS, we will need to adjust it’s value to the expected one for Indeed
    - In the scenarios, it indicates what would our `maven-metadata.xml` return IF the above case is “fixed”

| Scenario | CS-repo: local package [ts] | Nexus repo [ts] | CS-repo: Cached Nexus upstream package [ts] | Expected last updated [ts] | Cloudsmith GA maven-metadata.xml returns [ts] | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| [1] Package in Nexus only | / | 20250326 | / | 20250326 | Error: 404 | 404 Error response as Maven is JIT and we are not aware of the package group  |
| [2] Local Package in Cloudsmith only | 20250326 | / | / | 20250326 | 20250326 | Will return expected response |
| [3] Upstream Package cached in CS | / | 20250326 | 20250401 
 | 20250326 | 20250401 | We would override lastupdatedat date because of upstream sync, but indeed needs upstream date for freshness |
| [4] Local package and Nexus Upstream package. Local newer | 20250401 | 20250326 | / | 20250401 | 20250401 | Later date takes precedence  |
| [5] Local package and Nexus Upstream package. Local older. Indexing not run | 20250326 | 20250401 |  | 20250401 | 20250326 | Later date takes precedence. This can happen ONLY if a upstream was not indexed after the new version is published, it should take up to 2hrs to index and should not be a problem |
| [6]  Local package and Nexus Upstream package. Local older. Upstream Indexing completed | 20250326 | 20250401 |  | 20250401 | 20250401 |  |

## Failure scenarios context:

### [1] Package in Nexus only

As Maven doesn’t support AOT indexing, we have no awareness of upstream packages until they are pulled for the first time. We could fallback to using Nexus API for upstream indexing, but this will require considerable effort. Workaround could be that Indeed fetches all the expected packages using their current script (they are already doing this when traversing HTML), where they would handle 404 from Cloudsmith as that the package is not synced, which means defaulting to the timing got from Nexus freshness check for a package group

### [3] Upstream Package cached in CS

Once the package is pulled from the upstream, `uploadedAt` date for the package would be set to `now` . We don’t have data on the upload date for the upstream source. Reason why we don’t have this is that fetching this data requires a lot of engineering effort, even if we scope this to Maven format only, most of the maven upstreams have a different way of presenting this date, or not supporting API (MavenCentral), or not exposing this data at all (Oracle Maven).

As a workaround, as we don’t have exact date when the upload package is uploaded, but we can filter out this package from the `uploadedAt` of “versionless package” calculation (e.g. implement parameter that will filter out packages with `nexus-upstream` tag), but it will require Indeed to fetch `uploadedAt` date from Nexus for the same “versionless package”, and pick the larger of two for the “freshness date”

### [5] Local package and Nexus Upstream package. Local older. Indexing not run

This inconsistency will be caused because of latency of Upstream indexing. As it will yield latency of up to 2hr, and Indeed cares about freshness in days, we can omit this failure scenario

## Learnings

- Maven is JIT, which means we won’t have information about packages if they are not cached in the Cloudsmith from the upstream
- Update date from the upstream package is not available in the DB and will take some effort to fetch
- `uploadedAt` in GA `maven-metadata.xml` in Cloudsmith will return unexpected values for Indeed

## Potential Solutions:

### Solution 1: Indeed blends information from the Nexus and Cloudsmith to determine freshness of a package

During the migration period, all up to X days from fully migrating to Cloudsmith (X being their freshness check limit), Indeed will get equivalent “versionless package” information from both Indeed and Cloudsmith. Script algorithm should work:

- Fetch all packages in Indeed maven repository
- For each package group:
    - Get `lastUpdated`  in GA `maven-metadata.xml` (they are already doing that)
    - Get `lastUpdated` from Cloudsmith for all packages EXCEPT packages synced from Nexus upstream. Script will need to provide property like “exclude_packages_with_tags=nexus-maven”, and API should apply the filter. This can be implemented using
        - `lastUpdated`  in Cloudsmith GA `maven-metadata.xml` . Would require changing how we generate `lastUpdated` . Low effort, Maven specific
        - in Cloudsmith PackageGroup API. Low effort, format agnostic, so it can be reused for npm and python
    - Pick higher of those 2 `lastUpdated` dates, which will be the date used for freshness check

Pros:

- Low effort from our side
- Solves Maven being JIT

Cons:

- Indeed’s script during transition period will need to add logic to compare Cloudsmith and Nexus `lastUpdated` time

## Proposed solution

Solution 1 adds little complexity in the customer’s script, but it won’t require us to add temporary customer specific code in our codebase, that will be hacky. If we implement Solution 1 with using Package Group, we can extend implementation on other formats. It wouldn’t require too much engineering time from the Cloudsmith

### Diagram of the proposed solution

https://link.excalidraw.com/l/7aJ5mIbtXrP/8qSC4ceSRjE

## 2025/04/18 Meeting Notes

- Investigate PackageGroup behaviour for Maven and npm. How it handles same artifactId but different groupID
- CS to CS; first set to proxy, second upstream’s to first one. Maven arbitrary files would need to support it

2025/04/2 Meeting notes

Scenario:

- Migrated package X; latest version 2.1.1 with a date; Expected date from versionless check 20250401
- They build and push package X with a version 1.0.0 today (on 20250402 )
    - Expected date from versionless check 20250401 , but we would return 20250402