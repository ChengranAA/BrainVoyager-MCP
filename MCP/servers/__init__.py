"""MCP server entry points — one per domain (industry-standard pattern).

Three independent servers, each with its own ``FastMCP`` instance:

    bv_core_server       Document management, DICOM ops, UI, shell
    bv_anatomy_server    VMR creation, preprocessing pipeline, mesh, MP2RAGE
    bv_fmri_server       VTC, MDM, FMR, DMR, project workflows

Configure your MCP client to run only the servers you need:

.. code-block:: json

    {
      "mcpServers": {
        "BV Core": {
          "command": "python",
          "args": ["MCP/servers/bv_core_server.py"]
        },
        "BV Anatomy": {
          "command": "python",
          "args": ["MCP/servers/bv_anatomy_server.py"]
        },
        "BV fMRI": {
          "command": "python",
          "args": ["MCP/servers/bv_fmri_server.py"]
        }
      }
    }
"""
