# Start

I'm an Engineer in Cloudsmith and I'm testing Indeed's migration to us. They have concerns regarding freshness of the package check during the migration, more data is in the contex.md file.

Ingest the context and generate the proposed solution for Maven packages using Nexus and Cloudsmith API. Code should mock data from Nexus for:
* Returning list of all packages
* Returning lastUpdated date for Nexus Maven GA package

It should be able to call Cloudsmith API, with configurable URL and API_KEY, fetched from the .env file

----

## 2

freshness_checker is not working exactly as I intended, let's make some changes:
1. First phase should fetch all versionless packages from Nexus. It should return mocked data based on our fixtures and passed parameter to the CLI. Mocked data set should have Maven, npm and python folders
2. After we get versionless package, we should get mocked lastUpdatedAt from the mocked Nexus API for the particular package
3. For each versionless package, we should query cloudsmith API. we should query package group API `"/packages/{owner}/{repo}/groups/`, like in cloudsmith_package_group_api.txt. We should use query parameter, by using `NOT tag:upstream`
4. Pick older of the 2 dates. that is package freshness date
5. Code should log result of each on of the steps