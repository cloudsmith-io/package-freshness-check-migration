Example Openapi doc for package group API that needs to be used


```
"/packages/{owner}/{repo}/groups/": {
            "get": {
                "operationId": "packages_groups_list",
                "summary": "Return a list of Package Groups in a repository.",
                "description": "Return a list of Package Groups in a repository.",
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "description": "A page number within the paginated result set.",
                        "required": false,
                        "type": "integer"
                    },
                    {
                        "name": "page_size",
                        "in": "query",
                        "description": "Number of results to return per page.",
                        "required": false,
                        "type": "integer"
                    },
                    {
                        "name": "group_by",
                        "in": "query",
                        "description": "A field to group packages by. Available options: name, backend_kind.",
                        "required": false,
                        "type": "string",
                        "default": "name"
                    },
                    {
                        "name": "query",
                        "in": "query",
                        "description": "A search term for querying names, filenames, versions, distributions, architectures, formats, or statuses of packages.",
                        "required": false,
                        "type": "string",
                        "default": ""
                    },
                    {
                        "name": "sort",
                        "in": "query",
                        "description": "A field for sorting objects in ascending or descending order. Use `-` prefix for descending order (e.g., `-name`). Available options: name, count, num_downloads, size, last_push, backend_kind.",
                        "required": false,
                        "type": "string",
                        "default": "name"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Retrieved the list of package groups.",
                        "schema": {
                            "required": [
                                "results"
                            ],
                            "type": "object",
                            "properties": {
                                "results": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/definitions/PackageGroup"
                                    }
                                }
                            }
                        }
                    },
                    "404": {
                        "description": "Owner namespace or repository not found",
                        "schema": {
                            "$ref": "#/definitions/ErrorDetail"
                        }
                    },
                    "400": {
                        "description": "Request could not be processed (see detail).",
                        "schema": {
                            "$ref": "#/definitions/ErrorDetail"
                        }
                    },
                    "422": {
                        "description": "Missing or invalid parameters (see detail).",
                        "schema": {
                            "$ref": "#/definitions/ErrorDetail"
                        }
                    }
                },
                "tags": [
                    "packages"
                ],
                "x-hidden": false,
                "x-detail": false,
                "x-permissionRequired": "package.view_repo(repo: 'Repository')",
                "x-objectPermissionRequired": false
            },
            "parameters": [
                {
                    "name": "owner",
                    "in": "path",
                    "required": true,
                    "type": "string"
                },
                {
                    "name": "repo",
                    "in": "path",
                    "required": true,
                    "type": "string"
                }
            ]
    }
```