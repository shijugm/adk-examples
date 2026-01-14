We will be using the MCP Toolbox for Databases to interact with Neo4j.

Install and Configure Toolbox 

First step is to install and run the Toolbox server. 
Download the binary from https://github.com/googleapis/genai-toolbox/releases

Run the toolbox server 
./toolbox --tools-file neo4j_mcp_integration/tools.yaml

MCP Toolbox server runs by default on localhost (or 127.0.0.1) and uses port 5000.

To change the port use  
./toolbox --tools-file neo4j_mcp_integration/tools.yaml  --port 5001 

To view the hosted tools
http://127.0.0.1:5001/api/toolset