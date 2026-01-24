
> This is part of a group project for the course CECS1011 - Introduction to Engineering & CS

## Overview

A full-stack web application for tracking produce batches' time-to-live (freshness), export routes, suggesting export routes for each produce batches, showing real-time and historic sensor reading and issuing warnings as issues occur.
## Architecture

1. Main server app:
	- Base: FastAPI 
	- why FastAPI? Offers convenient classes (Requests/Responses, BackgroundProcess, Middleware, Dependency Injection) and decorators to speed up the progress of writing API endpoints; does not force a fixed way of structuring the project folder like other frameworks; modular (can omit WebSocket support if not needed, can change native Python JSON handler for other more performant options like ORJSON)
	- Components:
		- `/static`: collection of HTML/JS/CSS files that makes up the front-end
		- `/routes`: a collection of server-side components, each matching with a different group of features ("responsibilities") of the server.
			- **produce**: provides interfaces to query and filter types of post-harvest produce by name, returning either a simple ID-and-produce-type list or a detailed one (consisting of name, shelf life and thresholds). also supports exporting a detailed produce list as either XLSX or CSV.
			- **batch**: there can be many batches of the same produce type. this component helps adding new batches, listing and extracting information of available batches, finding batches assigned to an order, assign order to or unassign order from a batch and managing statuses of each batch (`AVAILABLE`, `MARKED_FOR_EXPORT`, `EXPORTED`, `EXPIRED`, `DISCARDED` etc.)
			- **shipments**: allows creating, managing status (`PENDING_FOR_PAYLOAD`, `PENDING_FOR_DEPARTURE`, `DEPARTED`), lateness and triggering manual departure of shipments.
			- **sensors**: provide interfaces for uploading sensor reading (via WebSocket), receiving real-time sensor reading (via Server-Sent Events) and downloading/exporting historic sensor readings.
			- **suggestion**: run, poll the status off and return results for shipment suggestion tasks.
			- **admin**: a subset of controls for each of the components above that's only available for administrator accounts, including account management and produce type database management.
			- **config**: sets and gets configs related to the warehouse environment (safe thresholds, warehouse capacity)
			- **users**: provide account-related operations for non-admin users
		- `/server.py`: the main component. responsible for initializing modules, opening sessions and issuing session tokens on log-in and restricting users' access to modules based on account level (non-admin / admin).
2. Database: PostgreSQL:
	- **Entity Relation (ER) Diagram:** Table names should be self-explanatory
	- ![er_diagram](mdassets/Pasted%20image%2020260124115402.png)
3. Session Store:
	- Uses the Valkey in-memory database.
	- Stores current configuration for quick access.
	- Stores and expires session tokens.
	- **Why not lump the Session Store with the main Server App?**
		- A separate session store survives server reboots in case an uncaught exception happens
		- If we need to scale the server app to multiple workers (which by defaults, use totally separate instances of the same server app), we can make sure all workers have equal access to the list of session tokens for validation.
4. Batch Import Utility:
	- A simple ttkbootstrap-based desktop app.
	- Objective: Lets operator record new batches, receives the server-issued ID for the batch and prints the corresponding QR code.
	- Connects to any ESC/POS-compatible printer (such as the XPrinter lines) using the `python-escpos` library.

## Execution Flow

**New batch arrives** --> **Batch Import Utility** --> New UI to stick on batch + assign a time-to-live.

**Create new export shipment** 
--> **EITHER** (Run Batch Suggestions  --> Accept Suggestions) **OR** Assign batch manually
--> If shipment is fulfilled, click Export on that shipment record.

**Near expiry batch**: --> Mark batch in Red --> Show warning banner in dashboard.

**Expired Batch**: --> Mark batch as expired --> If any shipments containing
## Hosting operation

- Host on an Azure VM instance.
- Each of the main component is packaged in a Podman container.
- Uses Quadlets (`.container` and `.network` files) to generate systemd units for each container. This way, we can create a chain startup flow that:
	- Automatically runs the server component whenever the VM starts up.
	- Allows the main server app to wait until the database and the session store is fully ready.
	- Allows only rebooting the main server app if an update is needed, cutting maintenance downtime to seconds.
- Protection includes:
	- App-level: grouping all admin-only APIs under the `/admin` path; checking session tokens in requests against the server-side session store.
	- VM-level: run Podman containers in rootless mode, so any breaches in each of the container does not affect the root user of the VM.
	- Infra-level: Allow SSH access only through a VPN and uses Azure DDoS protection.

## Testing Steps

- Testing set-up:
	- Main server app running on localhost
	- Database and Session Store running in local Podman containers
	- API testing software
	- `virtualsensor.py`: a script to simulate a sensor, sending random data in specified range at fixed 1-sec interval through a WebSocket endpoint.
	- browser DevTools: for tracking network requests to and from the client.
- Create placeholder UIs for the front-end
- Creates new API endpoint
- For endpoint with simple DB query - call the API endpoint via an API testing software (in this case, Bruno)
- For endpoint with complex DB queries - run the query beforehand in a separate database management software
- If API endpoint behaves correctly - implement the API call and functions that process the info in the front-end
- For testing uploading sensor data -> server:
	- First, tried implementing a standard REST API (each entry = 1 push). found out it still takes some delay even on localhost
	- Switches to WebSocket (optimized for high-frequency data push).
- For testing broadcasting sensor data -> clients:
	- Open 6 cURL sessions pointed to the Server-Sent Event (SSE) source (i.e. the endpoint to receive realtime sensor data) with at different intervals.
	- Once confirmed to have no hiccups, implement the logic to receive sensor data on the web-based client.

## Libraries used

Backend:
* language: python
* 	valkey-server: in-memory key-value cache to store authenticated sessions
* 	PostgresQL: database
* 	Gemini API: provides ML functionalities

Libs used:
*     fastapi - library for writing webserver
*     websockets - provide websocket support for fastapi
*     pydantic - to validate input data and model responses
*     python-dotenv - to load environment variable file for development purposes
*     valkey-glide - client library to interact with Valkey server.
*     asyncpg - client library to interacting with PostgreSQL database.
*     aiofiles, aiocsv, aioxlsxstream - for handling files in web server applications.
*     argon2-cffi - provides hashing mechanism for passwords.
*     requests - for consuming third-party APIs

Front-end
* 	  language: html/css/js - no frameworks
*     bootstrap - provides fundamental styling
*     popper - dependency for context buttons in bootstrap
*     axios - to call server-side APIs
*     litepicker - supports picking date range in filters
*     sheetjs - in-browser .xlsx file generation
*     chartjs, chartjs-plugin-annotation, chartjs-plugin-streaming - provides realtime line charts for sensor view