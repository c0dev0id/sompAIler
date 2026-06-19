GENERAL
==========

Data in the PLAN/ directory is for reference only and should not be changed.
PLAN/vue3js-app-proposal-for-sdk-claude contains information about the planned implementation (as git submodule)
PLAN/sompyler contains the sompyler repository (as git submodule)
The repository root contains the neusican repository code

This information supercedes code location information referenced inside PLAN/vue3js-app-proposal-for-sdk-claude documents.
Instructions like git pull should be assumed as already performed. The code is current.

Rules for implementations in directory score-editors/
=============

- R. contains only the blueprint code, not the Neusician or the Sompyler core.  root file is expected `__init__.py` containing a flask.Blueprint() call, to be properly imported.
- Blueprint accepts at its root endpoint url the GET parameter `?import=1`
- GETs sompyle/astlog for importing a Neusik score to guarantee that the source is checked renderable by the original Neusician/Sompyler core.
- For exporting generated Neusik code, Blueprints static client code opens /sompyle or `/sompyle/reserved-a-worker-for-tests` and inserts it into the text-area via javascript. CORS issues will not be raised when score-editor project runs on the same domain as the Neusician core instance.
- The score-editor may encapsulate the rendering process by accessing sompyle/status.json. Auto-clicking "update status" button in intervals of 2 seconds or of centiles of the ETA time at >0-20% progress should suffice. (Automatic polling will not be realized upstream. Patience is a virtue.)
