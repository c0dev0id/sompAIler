AGENTS policy
=============

People with or without AI tools are welcome to participate in the Neusician
score editor challenge. Neusician instance providers may clone one or more
repositories that comply with the conditions below into a sub-directory
score-editors/*repo-name* and set the SCORE\_EDITOR\_BLUEPRINT config directive
to their current preference. The value of this variable is the repository
referenced by name in this sub-directory and will be registered as blueprint
with the url-prefix '/sompyle/score-editor'. The registration of a single
blueprint is supported, multiple blueprints support is not planned.

Conditions the author of Neusician relies upon to be fullfilled
---------------------------------------------------------------

 1. Repository is maintained by the owner of AI service account and token budget

 2. Merge requests upstream are denied for score editing stuff. This does not
    cover deterministic pseudo-random generation as there are already examples
    upstream.

 3. If the repository is private/internal, the author of Neusician can be invited
    for reporter role to the repository of the blueprint for evaluation and
    prompting assistance. He would refuse owner or maintainer role.

 4. R. contains only the blueprint code, not the Neusician or the Sompyler core.
    root file is expected `__init__.py` containing a flask.Blueprint() call,
    to be properly imported.

 5. Blueprint accepts at its root endpoint url the GET parameter `?import=1`

 6. GETs sompyle/astlog for importing a Neusik score to guarantee that the
    source is checked renderable by the original Neusician/Sompyler core.

 7. For exporting generated Neusik code, Blueprints static client code opens
    /sompyle or `/sompyle/reserved-a-worker-for-tests` and inserts it into the
    text-area via javascript. CORS issues will not be raised when score-editor
    project runs on the same domain as the Neusician core instance.

 8. The score-editor may encapsulate the rendering process by accessing
    sompyle/status.json. Auto-clicking "update status" button in intervals of
    2 seconds or of centiles of the ETA time at >0-20% progress should
    suffice. (Automatic polling will not be realized upstream. Patience is a
    virtue.)

 9. The blueprint is supposed to run without AI-accelaration hardware.
    Otherwise the upstream author will not support the project as he does not
    have the resources to test it.

 10. Only open-source blueprints are supported by the Neusician core author.
