import importlib.util, pathlib
import neusician.sompyler_procman as procman
from neusician.server import create_app
from jinja2 import FileSystemLoader, ChoiceLoader

HERE = pathlib.Path(__file__).parent

# SUBDIR is a CWD-relative constant in procman; fix it to an absolute path
procman.SUBDIR = str(pathlib.Path(procman.__file__).parent)

spec = importlib.util.spec_from_file_location('_config', HERE / 'instance' / 'config.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
config = {k: v for k, v in vars(mod).items() if k.isupper()}

app = create_app(test_config=config)

app.jinja_loader = ChoiceLoader([
    FileSystemLoader(str(HERE / 'templates')),
    app.jinja_loader,
])
