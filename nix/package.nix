{
  lib,
  python3Packages,
}:

let
  pyproject = builtins.fromTOML (builtins.readFile ../pyproject.toml);
in

python3Packages.buildPythonApplication {
  pname = pyproject.project.name;
  version = pyproject.project.version;
  pyproject = true;

  src = ./..;

  build-system = [ python3Packages.uv-build ];

  dependencies = with python3Packages; [
    httpx
    more-itertools
    (pyroute2.overrideAttrs (oldAttrs: {
      patches = oldAttrs.patches or [ ] ++ [ ./pyroute2-async-fix.patch ];
    }))
    typer
  ];

  meta = {
    description = pyproject.project.description;
    license = lib.licenses.eupl12;
    mainProgram = "nft-prefix-import";
  };
}
