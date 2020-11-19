# MAC

## Overview

MAC is intended to provide a simple way to implement API access to various sources and automate regular tasks. 
Modules provide the actual API implementation for accessing the source. Currently MAC provides Modules for
- ESM (get a list of data sources)
- openDXL (receive/send DXL messages)
- file (write to file)

Apps are instances of the Modules, and provide automation capabilities. An App follows this workflow:
- consume event (e.g. ESM: get list of data sources)
- process event (e.g. ATD: filter on certain reputations only)
- produce event (e.g. File: write to file)
In order to setup a workflow, Apps can be connected to each other by defining Targets (target App). Payload produced
by a certain App will in turn be consumed by the target App.

Some Modules require parameters to work properly (e.g. ESM: credentials, IP address), which is configured on a per App basis.
Those required parameters are defined in the __init__ function of a particular module
